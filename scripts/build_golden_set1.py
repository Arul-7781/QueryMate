import json
import re
import sqlite3
import time
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path

SOURCE_GOLDEN = Path("tests/golden_set.json")
TARGET_GOLDEN = Path("tests/golden_set1.json")
DB_PATH = Path("data/company_expanded.db")
FALLBACK_DB_PATH = Path("data/company.db")
TARGET_TOTAL = 1000
TIMEOUT_MS = 1500


def norm_text(s: str) -> str:
    return " ".join(s.lower().strip().split())


def canonical_sql(sql: str) -> str:
    text = norm_text(sql)
    text = re.sub(r"\s+", " ", text)
    return text


def structure_fingerprint(sql: str) -> str:
    s = canonical_sql(sql)
    s = re.sub(r"'[^']*'", "'?'", s)
    s = re.sub(r'\b\d+\b', '?', s)
    return s


def quote_sql(value: str) -> str:
    return value.replace("'", "''")


def token_set(text: str):
    return set(re.findall(r"[a-z0-9_]+", norm_text(text)))


def jaccard(a, b) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def execute_with_timeout(conn: sqlite3.Connection, sql: str, timeout_ms: int = TIMEOUT_MS):
    cur = conn.cursor()
    start = time.perf_counter()

    def progress_handler():
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return 1 if elapsed_ms > timeout_ms else 0

    conn.set_progress_handler(progress_handler, 1000)
    try:
        cur.execute(sql)
        rows = cur.fetchall()
    finally:
        conn.set_progress_handler(None, 0)
    return rows


def normalise_value(v):
    if isinstance(v, float):
        return round(v, 6)
    return v


def normalise_rows(rows):
    return Counter(tuple(normalise_value(v) for v in row) for row in rows)


def is_safe_sql(sql: str) -> bool:
    s = canonical_sql(sql)
    if not (s.startswith("select") or s.startswith("with")):
        return False
    forbidden = [
        " insert ", " update ", " delete ", " drop ", " alter ", " create ",
        " replace ", " attach ", " detach ", " pragma ", " vacuum ", " reindex ",
    ]
    wrapped = f" {s} "
    return not any(tok in wrapped for tok in forbidden)


def infer_topic_tags(sql: str):
    s = canonical_sql(sql)
    tags = set()
    if " join " in s:
        tags.add("joins")
    if " left join " in s:
        tags.add("left_join")
    if " cross join " in s:
        tags.add("cross_join")
    if " group by " in s:
        tags.add("group_by")
    if " having " in s:
        tags.add("having")
    if " with " in f" {s} ":
        tags.add("cte")
    if " recursive " in f" {s} ":
        tags.add("recursive_cte")
    if " over (" in s:
        tags.add("window")
    if " union " in s or " intersect " in s or " except " in s:
        tags.add("set_ops")
    if " case " in f" {s} ":
        tags.add("case")
    if " exists (" in s or " in (select " in s:
        tags.add("subquery")
    if "strftime(" in s or "julianday(" in s or "date(" in s:
        tags.add("date_time")
    if "upper(" in s or "lower(" in s or "substr(" in s or "length(" in s or " like " in s:
        tags.add("string_ops")
    if " limit " in s or " offset " in s:
        tags.add("pagination")
    if "row_number()" in s or "rank()" in s or "dense_rank()" in s:
        tags.add("ranking")
    if "proposed" in s or "preview" in s:
        tags.add("dml_safe")
    return sorted(tags) if tags else ["single_table"]


def profile_coverage(cases):
    topic_counts = Counter()
    difficulty_topic_counts = Counter()
    for c in cases:
        difficulty = c.get("difficulty", "medium")
        sql = c.get("sql", "")
        tags = c.get("topic_tags") or infer_topic_tags(sql)
        for t in tags:
            topic_counts[t] += 1
            difficulty_topic_counts[(t, difficulty)] += 1
    return topic_counts, difficulty_topic_counts


def fetch_list(cur, sql):
    cur.execute(sql)
    return [r[0] for r in cur.fetchall()]


def candidate_pool(cur):
    departments = fetch_list(cur, "SELECT DeptName FROM Departments ORDER BY DeptName")
    dept_ids = fetch_list(cur, "SELECT DeptID FROM Departments ORDER BY DeptID")
    employee_status = fetch_list(cur, "SELECT DISTINCT Status FROM Employees ORDER BY Status")
    project_status = fetch_list(cur, "SELECT DISTINCT Status FROM Projects ORDER BY Status")
    skills = fetch_list(cur, "SELECT SkillName FROM Skills ORDER BY SkillName")
    cities = fetch_list(cur, "SELECT DISTINCT City FROM Locations ORDER BY City")
    roles = fetch_list(cur, "SELECT DISTINCT Role FROM Employees WHERE Role IS NOT NULL ORDER BY Role")
    employees = fetch_list(cur, "SELECT Name FROM Employees ORDER BY Name LIMIT 160")

    salary_thresholds = [45000, 55000, 65000, 75000, 90000, 105000, 120000]
    budget_thresholds = [50000, 100000, 200000, 300000, 450000, 600000, 800000]
    date_thresholds = ["2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01"]

    # single-table filters, date/time, string ops, CASE, pagination
    for st in employee_status:
        yield {
            "question": f"List employee names with status {st} sorted alphabetically.",
            "sql": f"SELECT Name FROM Employees WHERE Status = '{quote_sql(st)}' ORDER BY Name;",
            "difficulty": "easy",
            "category": "single_table_filter",
            "tables_used": ["Employees"],
            "topic_tags": ["single_table"],
        }

    for thr in salary_thresholds:
        yield {
            "question": f"How many employees have salary at least {thr}?",
            "sql": f"SELECT COUNT(*) AS EmployeeCount FROM Employees WHERE Salary >= {thr};",
            "difficulty": "easy",
            "category": "single_table_filter",
            "tables_used": ["Employees"],
            "topic_tags": ["single_table"],
        }

    for dt in date_thresholds:
        yield {
            "question": f"How many employees joined on or after {dt}?",
            "sql": f"SELECT COUNT(*) AS EmployeeCount FROM Employees WHERE JoinDate >= '{dt}';",
            "difficulty": "easy",
            "category": "date_filter",
            "tables_used": ["Employees"],
            "topic_tags": ["date_time", "single_table"],
        }
        yield {
            "question": f"Show year-wise employee joining counts from {dt} onwards.",
            "sql": (
                "SELECT strftime('%Y', JoinDate) AS JoinYear, COUNT(*) AS EmployeeCount "
                "FROM Employees "
                f"WHERE JoinDate >= '{dt}' "
                "GROUP BY strftime('%Y', JoinDate) "
                "ORDER BY JoinYear;"
            ),
            "difficulty": "medium",
            "category": "date_grouping",
            "tables_used": ["Employees"],
            "topic_tags": ["date_time", "group_by"],
        }

    for prefix in ["A", "K", "R", "S", "M"]:
        yield {
            "question": f"List employees whose names start with {prefix}.",
            "sql": f"SELECT Name FROM Employees WHERE Name LIKE '{prefix}%' ORDER BY Name;",
            "difficulty": "easy",
            "category": "string_like",
            "tables_used": ["Employees"],
            "topic_tags": ["string_ops", "single_table"],
        }

    for n in [10, 20, 30]:
        yield {
            "question": f"Show employees from row {n+1} to {n+10} by salary descending (pagination).",
            "sql": (
                "SELECT Name, Salary FROM Employees "
                "ORDER BY Salary DESC, EmpID "
                f"LIMIT 10 OFFSET {n};"
            ),
            "difficulty": "medium",
            "category": "pagination",
            "tables_used": ["Employees"],
            "topic_tags": ["pagination", "single_table"],
        }

    # joins + group by/having
    for dept in departments:
        for st in employee_status:
            yield {
                "question": f"In {dept}, how many employees are in status {st}?",
                "sql": (
                    "SELECT COUNT(*) AS EmployeeCount FROM Employees e "
                    "JOIN Departments d ON e.DeptID = d.DeptID "
                    f"WHERE d.DeptName = '{quote_sql(dept)}' AND e.Status = '{quote_sql(st)}';"
                ),
                "difficulty": "easy",
                "category": "join_filter_count",
                "tables_used": ["Employees", "Departments"],
                "topic_tags": ["joins"],
            }

        yield {
            "question": f"List top 5 earners in {dept} with department name.",
            "sql": (
                "SELECT e.Name, e.Salary, d.DeptName FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{quote_sql(dept)}' "
                "ORDER BY e.Salary DESC, e.Name LIMIT 5;"
            ),
            "difficulty": "medium",
            "category": "join_sort_limit",
            "tables_used": ["Employees", "Departments"],
            "topic_tags": ["joins", "pagination"],
        }

        for pstat in project_status:
            yield {
                "question": f"What is the project count for status {pstat} in {dept}?",
                "sql": (
                    "SELECT COUNT(*) AS ProjectCount FROM Projects p "
                    "JOIN Departments d ON p.DeptID = d.DeptID "
                    f"WHERE d.DeptName = '{quote_sql(dept)}' AND p.Status = '{quote_sql(pstat)}';"
                ),
                "difficulty": "easy",
                "category": "join_project_status",
                "tables_used": ["Projects", "Departments"],
                "topic_tags": ["joins"],
            }

        for thr in salary_thresholds:
            yield {
                "question": f"In {dept}, how many employees earn above {thr}?",
                "sql": (
                    "SELECT COUNT(*) AS EmployeeCount FROM Employees e "
                    "JOIN Departments d ON e.DeptID = d.DeptID "
                    f"WHERE d.DeptName = '{quote_sql(dept)}' AND e.Salary > {thr};"
                ),
                "difficulty": "medium",
                "category": "join_threshold",
                "tables_used": ["Employees", "Departments"],
                "topic_tags": ["joins"],
            }

    for city in cities:
        yield {
            "question": f"How many employees are mapped to city {city}?",
            "sql": (
                "SELECT COUNT(*) AS EmployeeCount FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                "JOIN Locations l ON d.LocationID = l.LocationID "
                f"WHERE l.City = '{quote_sql(city)}';"
            ),
            "difficulty": "medium",
            "category": "city_join_count",
            "tables_used": ["Employees", "Departments", "Locations"],
            "topic_tags": ["joins"],
        }
        for pstat in project_status:
            yield {
                "question": f"How many {pstat} projects are tied to city {city}?",
                "sql": (
                    "SELECT COUNT(*) AS ProjectCount FROM Projects p "
                    "JOIN Departments d ON p.DeptID = d.DeptID "
                    "JOIN Locations l ON d.LocationID = l.LocationID "
                    f"WHERE l.City = '{quote_sql(city)}' AND p.Status = '{quote_sql(pstat)}';"
                ),
                "difficulty": "medium",
                "category": "city_project_status",
                "tables_used": ["Projects", "Departments", "Locations"],
                "topic_tags": ["joins"],
            }

    yield {
        "question": "List employees who are not assigned to any project.",
        "sql": (
            "SELECT e.Name FROM Employees e "
            "LEFT JOIN EmployeeProjects ep ON e.EmpID = ep.EmpID "
            "WHERE ep.ProjectID IS NULL ORDER BY e.Name;"
        ),
        "difficulty": "hard",
        "category": "anti_join",
        "tables_used": ["Employees", "EmployeeProjects"],
        "topic_tags": ["joins", "left_join"],
    }

    yield {
        "question": "List projects that currently have no assigned employees.",
        "sql": (
            "SELECT p.ProjectName FROM Projects p "
            "LEFT JOIN EmployeeProjects ep ON p.ProjectID = ep.ProjectID "
            "WHERE ep.EmpID IS NULL ORDER BY p.ProjectName;"
        ),
        "difficulty": "hard",
        "category": "anti_join",
        "tables_used": ["Projects", "EmployeeProjects"],
        "topic_tags": ["joins", "left_join"],
    }

    # group by / having
    yield {
        "question": "Show employee count and average salary for each department.",
        "sql": (
            "SELECT d.DeptName, COUNT(e.EmpID) AS EmployeeCount, AVG(e.Salary) AS AvgSalary "
            "FROM Departments d LEFT JOIN Employees e ON d.DeptID = e.DeptID "
            "GROUP BY d.DeptID, d.DeptName ORDER BY EmployeeCount DESC, d.DeptName;"
        ),
        "difficulty": "medium",
        "category": "group_by_department",
        "tables_used": ["Departments", "Employees"],
        "topic_tags": ["group_by", "joins"],
    }

    for n in [3, 5, 8]:
        yield {
            "question": f"Which skills are held by at least {n} employees?",
            "sql": (
                "SELECT s.SkillName, COUNT(DISTINCT es.EmpID) AS EmployeeCount "
                "FROM Skills s JOIN EmployeeSkills es ON s.SkillID = es.SkillID "
                "GROUP BY s.SkillID, s.SkillName "
                f"HAVING COUNT(DISTINCT es.EmpID) >= {n} "
                "ORDER BY EmployeeCount DESC, s.SkillName;"
            ),
            "difficulty": "medium",
            "category": "having_skill_count",
            "tables_used": ["Skills", "EmployeeSkills"],
            "topic_tags": ["group_by", "having", "joins"],
        }

    # nested subqueries / correlated / exists
    for dept in departments:
        yield {
            "question": f"List employees in {dept} earning above their department average.",
            "sql": (
                "SELECT e.Name, e.Salary FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{quote_sql(dept)}' "
                "AND e.Salary > (SELECT AVG(e2.Salary) FROM Employees e2 WHERE e2.DeptID = e.DeptID) "
                "ORDER BY e.Salary DESC, e.Name;"
            ),
            "difficulty": "hard",
            "category": "correlated_subquery",
            "tables_used": ["Employees", "Departments"],
            "topic_tags": ["subquery", "joins"],
        }

    for st in employee_status:
        yield {
            "question": f"Which departments have at least one employee with status {st}?",
            "sql": (
                "SELECT d.DeptName FROM Departments d "
                "WHERE EXISTS ("
                "SELECT 1 FROM Employees e WHERE e.DeptID = d.DeptID "
                f"AND e.Status = '{quote_sql(st)}'"
                ") ORDER BY d.DeptName;"
            ),
            "difficulty": "hard",
            "category": "exists_subquery",
            "tables_used": ["Departments", "Employees"],
            "topic_tags": ["subquery"],
        }

    # CTE + recursive CTE
    yield {
        "question": "Using a CTE, show total employees and average salary per status.",
        "sql": (
            "WITH emp_base AS (SELECT Status, Salary FROM Employees) "
            "SELECT Status, COUNT(*) AS EmployeeCount, AVG(Salary) AS AvgSalary "
            "FROM emp_base GROUP BY Status ORDER BY EmployeeCount DESC;"
        ),
        "difficulty": "hard",
        "category": "cte_summary",
        "tables_used": ["Employees"],
        "topic_tags": ["cte", "group_by"],
    }

    yield {
        "question": "Build manager-reporting chains up to depth 3 using recursive CTE.",
        "sql": (
            "WITH RECURSIVE org_chain(EmpID, Name, ManagerID, Level) AS ("
            "SELECT EmpID, Name, ManagerID, 0 FROM Employees WHERE ManagerID IS NULL "
            "UNION ALL "
            "SELECT e.EmpID, e.Name, e.ManagerID, oc.Level + 1 "
            "FROM Employees e JOIN org_chain oc ON e.ManagerID = oc.EmpID "
            "WHERE oc.Level < 3"
            ") "
            "SELECT EmpID, Name, ManagerID, Level FROM org_chain ORDER BY Level, Name;"
        ),
        "difficulty": "hard",
        "category": "recursive_cte",
        "tables_used": ["Employees"],
        "topic_tags": ["cte", "recursive_cte"],
    }

    # window functions / ranking
    for dept in departments:
        yield {
            "question": f"Rank employees by salary within {dept}.",
            "sql": (
                "SELECT e.Name, e.Salary, DENSE_RANK() OVER (ORDER BY e.Salary DESC) AS SalaryRank "
                "FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{quote_sql(dept)}' "
                "ORDER BY SalaryRank, e.Name;"
            ),
            "difficulty": "hard",
            "category": "window_rank",
            "tables_used": ["Employees", "Departments"],
            "topic_tags": ["window", "ranking", "joins"],
        }

    yield {
        "question": "Show running total of project budgets ordered by start date.",
        "sql": (
            "SELECT ProjectName, StartDate, Budget, "
            "SUM(Budget) OVER (ORDER BY StartDate, ProjectID) AS RunningBudget "
            "FROM Projects ORDER BY StartDate, ProjectID;"
        ),
        "difficulty": "hard",
        "category": "window_running_total",
        "tables_used": ["Projects"],
        "topic_tags": ["window", "date_time"],
    }

    # set operations
    for dept in departments:
        yield {
            "question": f"Using UNION, list Active or On Leave employees in {dept}.",
            "sql": (
                "SELECT e.Name FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{quote_sql(dept)}' AND e.Status = 'Active' "
                "UNION "
                "SELECT e.Name FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{quote_sql(dept)}' AND e.Status = 'On Leave' "
                "ORDER BY Name;"
            ),
            "difficulty": "hard",
            "category": "set_union",
            "tables_used": ["Employees", "Departments"],
            "topic_tags": ["set_ops", "joins"],
        }

    for s1, s2 in combinations(skills[:14], 2):
        yield {
            "question": f"Using INTERSECT, list employees who have both {s1} and {s2}.",
            "sql": (
                "SELECT e.Name FROM Employees e JOIN EmployeeSkills es ON e.EmpID = es.EmpID "
                "JOIN Skills s ON es.SkillID = s.SkillID "
                f"WHERE s.SkillName = '{quote_sql(s1)}' "
                "INTERSECT "
                "SELECT e.Name FROM Employees e JOIN EmployeeSkills es ON e.EmpID = es.EmpID "
                "JOIN Skills s ON es.SkillID = s.SkillID "
                f"WHERE s.SkillName = '{quote_sql(s2)}' "
                "ORDER BY Name;"
            ),
            "difficulty": "hard",
            "category": "set_intersect",
            "tables_used": ["Employees", "EmployeeSkills", "Skills"],
            "topic_tags": ["set_ops", "joins"],
        }
        yield {
            "question": f"Using EXCEPT, list employees who have {s1} but not {s2}.",
            "sql": (
                "SELECT e.Name FROM Employees e JOIN EmployeeSkills es ON e.EmpID = es.EmpID "
                "JOIN Skills s ON es.SkillID = s.SkillID "
                f"WHERE s.SkillName = '{quote_sql(s1)}' "
                "EXCEPT "
                "SELECT e.Name FROM Employees e JOIN EmployeeSkills es ON e.EmpID = es.EmpID "
                "JOIN Skills s ON es.SkillID = s.SkillID "
                f"WHERE s.SkillName = '{quote_sql(s2)}' "
                "ORDER BY Name;"
            ),
            "difficulty": "hard",
            "category": "set_except",
            "tables_used": ["Employees", "EmployeeSkills", "Skills"],
            "topic_tags": ["set_ops", "joins"],
        }

    # CASE expressions and DML-safe prompts
    for dept in departments:
        yield {
            "question": f"In {dept}, classify employees into salary bands using CASE.",
            "sql": (
                "SELECT e.Name, e.Salary, "
                "CASE "
                "WHEN e.Salary >= 100000 THEN 'High' "
                "WHEN e.Salary >= 70000 THEN 'Mid' "
                "ELSE 'Low' END AS SalaryBand "
                "FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{quote_sql(dept)}' "
                "ORDER BY e.Salary DESC, e.Name;"
            ),
            "difficulty": "medium",
            "category": "case_expression",
            "tables_used": ["Employees", "Departments"],
            "topic_tags": ["case", "joins"],
        }

    for pct in [3, 5, 8]:
        yield {
            "question": f"Before a {pct}% raise, preview current and proposed salaries for active employees.",
            "sql": (
                "SELECT EmpID, Name, Salary AS CurrentSalary, "
                f"ROUND(Salary * (1 + {pct}/100.0), 2) AS ProposedSalary "
                "FROM Employees WHERE Status = 'Active' "
                "ORDER BY ProposedSalary DESC, EmpID;"
            ),
            "difficulty": "medium",
            "category": "dml_safe_preview",
            "tables_used": ["Employees"],
            "topic_tags": ["dml_safe", "transaction_aware"],
        }

    # transaction-aware read-only prompts
    for b in budget_thresholds:
        yield {
            "question": f"Before budget adjustment, show projects with budget >= {b} and their department.",
            "sql": (
                "SELECT p.ProjectName, p.Budget, d.DeptName "
                "FROM Projects p JOIN Departments d ON p.DeptID = d.DeptID "
                f"WHERE p.Budget >= {b} "
                "ORDER BY p.Budget DESC, p.ProjectName;"
            ),
            "difficulty": "medium",
            "category": "transaction_readiness_preview",
            "tables_used": ["Projects", "Departments"],
            "topic_tags": ["transaction_aware", "joins"],
        }

    # employee-specific deep questions
    for emp in employees:
        eq = quote_sql(emp)
        yield {
            "question": f"Show manager and department for employee {emp}.",
            "sql": (
                "SELECT m.Name AS ManagerName, d.DeptName FROM Employees e "
                "LEFT JOIN Employees m ON e.ManagerID = m.EmpID "
                "LEFT JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE e.Name = '{eq}';"
            ),
            "difficulty": "medium",
            "category": "self_join_manager_lookup",
            "tables_used": ["Employees", "Departments"],
            "topic_tags": ["joins", "subquery"],
        }
        yield {
            "question": f"How many projects and total logged hours does {emp} have?",
            "sql": (
                "SELECT COUNT(ep.ProjectID) AS ProjectCount, COALESCE(SUM(ep.HoursLogged), 0) AS TotalHours "
                "FROM Employees e LEFT JOIN EmployeeProjects ep ON e.EmpID = ep.EmpID "
                f"WHERE e.Name = '{eq}';"
            ),
            "difficulty": "easy",
            "category": "employee_rollup",
            "tables_used": ["Employees", "EmployeeProjects"],
            "topic_tags": ["joins", "group_by"],
        }

    # cross join matrix example
    for dept in departments:
        yield {
            "question": f"Build a status matrix for {dept} using CROSS JOIN and counts.",
            "sql": (
                "WITH statuses AS ("
                "SELECT 'Active' AS Status UNION ALL SELECT 'On Leave' UNION ALL SELECT 'Resigned'"
                "), depts AS ("
                f"SELECT DeptID, DeptName FROM Departments WHERE DeptName = '{quote_sql(dept)}'"
                ") "
                "SELECT d.DeptName, s.Status, "
                "COALESCE(("
                "SELECT COUNT(*) FROM Employees e WHERE e.DeptID = d.DeptID AND e.Status = s.Status"
                "), 0) AS EmployeeCount "
                "FROM depts d CROSS JOIN statuses s "
                "ORDER BY s.Status;"
            ),
            "difficulty": "hard",
            "category": "cross_join_matrix",
            "tables_used": ["Departments", "Employees"],
            "topic_tags": ["cross_join", "joins", "cte"],
        }

    # extra advanced templates to push coverage and total volume
    yield {
        "question": "For each department, compute project-budget to department-budget ratio.",
        "sql": (
            "SELECT d.DeptName, d.Budget AS DeptBudget, COALESCE(SUM(p.Budget), 0) AS ProjectBudget, "
            "ROUND(COALESCE(SUM(p.Budget), 0) * 1.0 / NULLIF(d.Budget, 0), 4) AS BudgetRatio "
            "FROM Departments d LEFT JOIN Projects p ON d.DeptID = p.DeptID "
            "GROUP BY d.DeptID, d.DeptName, d.Budget "
            "ORDER BY BudgetRatio DESC, d.DeptName;"
        ),
        "difficulty": "hard",
        "category": "dept_budget_ratio",
        "tables_used": ["Departments", "Projects"],
        "topic_tags": ["joins", "group_by", "case"],
    }

    yield {
        "question": "Show project durations in days using julianday for completed projects.",
        "sql": (
            "SELECT ProjectName, StartDate, EndDate, "
            "CAST(julianday(EndDate) - julianday(StartDate) AS INTEGER) AS DurationDays "
            "FROM Projects WHERE EndDate IS NOT NULL "
            "ORDER BY DurationDays DESC, ProjectName;"
        ),
        "difficulty": "medium",
        "category": "project_duration_days",
        "tables_used": ["Projects"],
        "topic_tags": ["date_time", "single_table"],
    }

    yield {
        "question": "List active employees who are not assigned to any project using EXCEPT.",
        "sql": (
            "SELECT Name FROM Employees WHERE Status = 'Active' "
            "EXCEPT "
            "SELECT e.Name FROM Employees e JOIN EmployeeProjects ep ON e.EmpID = ep.EmpID "
            "ORDER BY Name;"
        ),
        "difficulty": "hard",
        "category": "set_except_active_without_projects",
        "tables_used": ["Employees", "EmployeeProjects"],
        "topic_tags": ["set_ops", "joins"],
    }

    yield {
        "question": "Find employees who have at least one Expert skill but are not project leads.",
        "sql": (
            "SELECT DISTINCT e.Name FROM Employees e "
            "WHERE EXISTS ("
            "SELECT 1 FROM EmployeeSkills es WHERE es.EmpID = e.EmpID AND es.Proficiency = 'Expert'"
            ") "
            "AND e.EmpID NOT IN ("
            "SELECT ep.EmpID FROM EmployeeProjects ep WHERE ep.Role = 'Lead'"
            ") "
            "ORDER BY e.Name;"
        ),
        "difficulty": "hard",
        "category": "expert_not_lead",
        "tables_used": ["Employees", "EmployeeSkills", "EmployeeProjects"],
        "topic_tags": ["subquery", "joins"],
    }

    yield {
        "question": "For each skill, return the most common proficiency level using window functions.",
        "sql": (
            "WITH prof_counts AS ("
            "SELECT s.SkillName, es.Proficiency, COUNT(*) AS Cnt "
            "FROM Skills s JOIN EmployeeSkills es ON s.SkillID = es.SkillID "
            "GROUP BY s.SkillID, s.SkillName, es.Proficiency"
            "), ranked AS ("
            "SELECT SkillName, Proficiency, Cnt, "
            "ROW_NUMBER() OVER (PARTITION BY SkillName ORDER BY Cnt DESC, Proficiency) AS rn "
            "FROM prof_counts"
            ") "
            "SELECT SkillName, Proficiency, Cnt FROM ranked WHERE rn = 1 ORDER BY SkillName;"
        ),
        "difficulty": "hard",
        "category": "window_mode_proficiency",
        "tables_used": ["Skills", "EmployeeSkills"],
        "topic_tags": ["window", "cte", "group_by", "ranking"],
    }

    yield {
        "question": "Show department-wise lead-to-member assignment ratio.",
        "sql": (
            "SELECT d.DeptName, "
            "SUM(CASE WHEN ep.Role = 'Lead' THEN 1 ELSE 0 END) AS LeadAssignments, "
            "SUM(CASE WHEN ep.Role = 'Member' THEN 1 ELSE 0 END) AS MemberAssignments, "
            "ROUND(SUM(CASE WHEN ep.Role = 'Lead' THEN 1 ELSE 0 END) * 1.0 / "
            "NULLIF(SUM(CASE WHEN ep.Role = 'Member' THEN 1 ELSE 0 END), 0), 4) AS LeadMemberRatio "
            "FROM Departments d "
            "JOIN Employees e ON d.DeptID = e.DeptID "
            "JOIN EmployeeProjects ep ON e.EmpID = ep.EmpID "
            "GROUP BY d.DeptID, d.DeptName "
            "ORDER BY LeadMemberRatio DESC, d.DeptName;"
        ),
        "difficulty": "hard",
        "category": "lead_member_ratio",
        "tables_used": ["Departments", "Employees", "EmployeeProjects"],
        "topic_tags": ["joins", "group_by", "case"],
    }

    yield {
        "question": "List cities where average employee salary exceeds global average salary.",
        "sql": (
            "SELECT l.City, AVG(e.Salary) AS CityAvgSalary "
            "FROM Employees e "
            "JOIN Departments d ON e.DeptID = d.DeptID "
            "JOIN Locations l ON d.LocationID = l.LocationID "
            "GROUP BY l.City "
            "HAVING AVG(e.Salary) > (SELECT AVG(Salary) FROM Employees) "
            "ORDER BY CityAvgSalary DESC, l.City;"
        ),
        "difficulty": "hard",
        "category": "city_vs_global_avg",
        "tables_used": ["Employees", "Departments", "Locations"],
        "topic_tags": ["joins", "group_by", "having", "subquery"],
    }

    yield {
        "question": "Before any department budget cut, preview departments above company median budget proxy.",
        "sql": (
            "WITH ordered AS ("
            "SELECT DeptName, Budget, ROW_NUMBER() OVER (ORDER BY Budget) AS rn, "
            "COUNT(*) OVER () AS total_rows FROM Departments"
            ") "
            "SELECT DeptName, Budget AS ProposedReviewBudget FROM ordered "
            "WHERE rn >= (total_rows + 1) / 2 "
            "ORDER BY Budget DESC, DeptName;"
        ),
        "difficulty": "hard",
        "category": "transaction_budget_preview",
        "tables_used": ["Departments"],
        "topic_tags": ["transaction_aware", "window", "dml_safe"],
    }


def build_quota_table(target_new: int):
    topics = [
        "single_table", "joins", "group_by", "having", "subquery", "cte",
        "recursive_cte", "window", "set_ops", "case", "date_time", "string_ops",
        "ranking", "pagination", "dml_safe", "transaction_aware", "left_join", "cross_join",
    ]
    per_topic_min = max(8, target_new // (len(topics) * 3))

    quotas = {}
    for t in topics:
        quotas[(t, "easy")] = per_topic_min
        quotas[(t, "medium")] = per_topic_min
        quotas[(t, "hard")] = per_topic_min

    # Force heavier coverage on advanced topics.
    for t in ["joins", "subquery", "cte", "window", "set_ops", "group_by"]:
        quotas[(t, "medium")] += 8
        quotas[(t, "hard")] += 10

    return quotas


def should_accept_for_quota(tags, difficulty, quota_counts, quotas):
    for t in tags:
        if quota_counts[(t, difficulty)] < quotas.get((t, difficulty), 0):
            return True
    return False


def main():
    if not SOURCE_GOLDEN.exists():
        raise FileNotFoundError(f"Missing source golden set: {SOURCE_GOLDEN}")

    db_path = DB_PATH if DB_PATH.exists() else FALLBACK_DB_PATH
    if not db_path.exists():
        raise FileNotFoundError(
            f"Neither {DB_PATH} nor {FALLBACK_DB_PATH} exists. Run DB setup first."
        )

    with SOURCE_GOLDEN.open("r") as f:
        source_cases = json.load(f)

    # Start target file from source so original remains untouched.
    cases = list(source_cases)

    seen_questions = {norm_text(c["question"]) for c in cases}
    seen_sql = {canonical_sql(c["sql"]) for c in cases}
    seen_fingerprints = {structure_fingerprint(c["sql"]) for c in cases}
    question_tokens = [token_set(c["question"]) for c in cases]

    next_id = (max((c.get("id", 0) for c in cases), default=0) + 1)
    target_new = max(TARGET_TOTAL - len(cases), 0)

    existing_topic_counts, _ = profile_coverage(cases)
    quotas = build_quota_table(target_new)
    quota_counts = Counter()

    conn = sqlite3.connect(db_path)

    accepted = []
    rejected = []

    for cand in candidate_pool(conn.cursor()):
        if len(accepted) >= target_new:
            break

        question = cand["question"].strip()
        sql = cand["sql"].strip()
        difficulty = cand.get("difficulty", "medium")
        tags = cand.get("topic_tags") or infer_topic_tags(sql)

        q_norm = norm_text(question)
        s_norm = canonical_sql(sql)
        fp = structure_fingerprint(sql)

        if q_norm in seen_questions:
            rejected.append((question, "dup_question"))
            continue
        if s_norm in seen_sql:
            rejected.append((question, "dup_sql"))
            continue
        q_tok = token_set(question)
        if any(jaccard(q_tok, prev) > 0.98 for prev in question_tokens[-120:]):
            rejected.append((question, "near_dup_question"))
            continue

        if not is_safe_sql(sql):
            rejected.append((question, "unsafe_sql"))
            continue

        try:
            rows1 = execute_with_timeout(conn, sql, TIMEOUT_MS)
            rows2 = execute_with_timeout(conn, sql, TIMEOUT_MS)
        except Exception as e:
            rejected.append((question, f"exec_error:{type(e).__name__}"))
            continue

        if normalise_rows(rows1) != normalise_rows(rows2):
            rejected.append((question, "unstable_result"))
            continue

        if rows1 is None:
            rejected.append((question, "no_rows"))
            continue

        # Prioritize unmet quotas first; once enough candidates exist, allow fill.
        must_take = should_accept_for_quota(tags, difficulty, quota_counts, quotas)
        have_room = len(accepted) < target_new
        if not (must_take or have_room):
            rejected.append((question, "quota_skip"))
            continue

        item = {
            "id": next_id,
            "difficulty": difficulty,
            "category": cand.get("category", "generated"),
            "tables_used": cand.get("tables_used", []),
            "topic_tags": tags,
            "question": question,
            "sql": sql,
        }

        accepted.append(item)
        cases.append(item)
        next_id += 1

        seen_questions.add(q_norm)
        seen_sql.add(s_norm)
        seen_fingerprints.add(fp)
        question_tokens.append(q_tok)
        for t in tags:
            quota_counts[(t, difficulty)] += 1

    conn.close()

    cases = sorted(cases, key=lambda x: x["id"])

    TARGET_GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = TARGET_GOLDEN.with_suffix(".json.tmp")
    with tmp_path.open("w") as f:
        json.dump(cases, f, indent=2)
    tmp_path.replace(TARGET_GOLDEN)

    # QA report
    report_dir = Path("tests/results")
    report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    qa_path = report_dir / f"golden_set1_generation_{ts}.json"
    with qa_path.open("w") as f:
        json.dump(
            {
                "source_total": len(source_cases),
                "target_total": len(cases),
                "requested_new": target_new,
                "accepted_new": len(accepted),
                "db_path_used": str(db_path),
                "existing_topic_counts": dict(existing_topic_counts),
                "new_topic_difficulty_counts": {f"{k[0]}|{k[1]}": v for k, v in quota_counts.items()},
                "rejected_sample": rejected[:200],
            },
            f,
            indent=2,
        )

    print(f"Source file       : {SOURCE_GOLDEN}")
    print(f"Target file       : {TARGET_GOLDEN}")
    print(f"Database used     : {db_path}")
    print(f"Original total    : {len(source_cases)}")
    print(f"Accepted new      : {len(accepted)}")
    print(f"Final total       : {len(cases)}")
    print(f"QA report         : {qa_path}")

    if len(cases) < TARGET_TOTAL:
        print(
            f"Warning: final total is {len(cases)} (< {TARGET_TOTAL}). "
            "Increase DB size or add more templates."
        )


if __name__ == "__main__":
    main()
