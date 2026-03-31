import json
import sqlite3
from pathlib import Path

GOLDEN_SET_PATH = Path("tests/golden_set.json")
DB_PATH = Path("data/company.db")


def add_case(cases, next_id, question, sql, difficulty, category, tables_used):
    cases.append(
        {
            "id": next_id,
            "difficulty": difficulty,
            "category": category,
            "tables_used": tables_used,
            "question": question,
            "sql": sql,
        }
    )
    return next_id + 1


def main():
    with GOLDEN_SET_PATH.open() as f:
        base = json.load(f)

    if len(base) != 50:
        raise RuntimeError(
            f"Expected seed golden set to have 50 entries, found {len(base)}"
        )

    new_cases = []
    next_id = max(item["id"] for item in base) + 1

    # A) Department-focused queries (50)
    departments = ["IT", "Sales", "HR", "Finance", "Operations"]
    for dept in departments:
        next_id = add_case(
            new_cases,
            next_id,
            f"How many active employees are in the {dept} department?",
            (
                "SELECT COUNT(*) AS ActiveEmployeeCount "
                "FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}' AND e.Status = 'Active';"
            ),
            "easy",
            "dept_filter_count",
            ["Employees", "Departments"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"What is the average salary of active employees in {dept}?",
            (
                "SELECT AVG(e.Salary) AS AvgActiveSalary "
                "FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}' AND e.Status = 'Active';"
            ),
            "medium",
            "dept_filter_aggregate",
            ["Employees", "Departments"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"What is the highest salary in the {dept} department?",
            (
                "SELECT MAX(e.Salary) AS MaxSalary "
                "FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}';"
            ),
            "easy",
            "dept_filter_aggregate",
            ["Employees", "Departments"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"List employees in {dept} ordered by salary descending.",
            (
                "SELECT e.Name, e.Role, e.Salary "
                "FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}' "
                "ORDER BY e.Salary DESC;"
            ),
            "medium",
            "dept_filter_sort",
            ["Employees", "Departments"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"How many projects are owned by {dept}?",
            (
                "SELECT COUNT(*) AS ProjectCount "
                "FROM Projects p "
                "JOIN Departments d ON p.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}';"
            ),
            "easy",
            "dept_projects_count",
            ["Projects", "Departments"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"What is the total project budget owned by {dept}?",
            (
                "SELECT SUM(p.Budget) AS TotalProjectBudget "
                "FROM Projects p "
                "JOIN Departments d ON p.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}';"
            ),
            "medium",
            "dept_projects_budget",
            ["Projects", "Departments"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"List projects in {dept} with status and budget.",
            (
                "SELECT p.ProjectName, p.Status, p.Budget "
                "FROM Projects p "
                "JOIN Departments d ON p.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}' "
                "ORDER BY p.Budget DESC;"
            ),
            "medium",
            "dept_projects_list",
            ["Projects", "Departments"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"What is the total hours logged by employees from {dept} across all projects?",
            (
                "SELECT SUM(ep.HoursLogged) AS TotalHours "
                "FROM EmployeeProjects ep "
                "JOIN Employees e ON ep.EmpID = e.EmpID "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}';"
            ),
            "medium",
            "dept_hours_sum",
            ["EmployeeProjects", "Employees", "Departments"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"How many distinct skills are present among employees in {dept}?",
            (
                "SELECT COUNT(DISTINCT es.SkillID) AS DistinctSkillCount "
                "FROM EmployeeSkills es "
                "JOIN Employees e ON es.EmpID = e.EmpID "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}';"
            ),
            "hard",
            "dept_distinct_skills",
            ["EmployeeSkills", "Employees", "Departments"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"For the {dept} department, show managers and their number of direct reports.",
            (
                "SELECT m.Name AS ManagerName, COUNT(e.EmpID) AS DirectReports "
                "FROM Employees e "
                "JOIN Employees m ON e.ManagerID = m.EmpID "
                "JOIN Departments d ON m.DeptID = d.DeptID "
                f"WHERE d.DeptName = '{dept}' "
                "GROUP BY m.EmpID, m.Name "
                "ORDER BY DirectReports DESC;"
            ),
            "hard",
            "dept_manager_reports",
            ["Employees", "Departments"],
        )

    # B) Skill-focused queries (50)
    skills = [
        "Python",
        "SQL",
        "AWS",
        "Machine Learning",
        "Leadership",
        "Communication",
        "Financial Modeling",
        "Recruitment",
        "Docker",
        "Data Analysis",
    ]
    for skill in skills:
        next_id = add_case(
            new_cases,
            next_id,
            f"How many employees have the {skill} skill?",
            (
                "SELECT COUNT(DISTINCT e.EmpID) AS EmployeeCount "
                "FROM Employees e "
                "JOIN EmployeeSkills es ON e.EmpID = es.EmpID "
                "JOIN Skills s ON es.SkillID = s.SkillID "
                f"WHERE s.SkillName = '{skill}';"
            ),
            "easy",
            "skill_count",
            ["Employees", "EmployeeSkills", "Skills"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"List employees with {skill} skill and their proficiency.",
            (
                "SELECT e.Name, es.Proficiency "
                "FROM Employees e "
                "JOIN EmployeeSkills es ON e.EmpID = es.EmpID "
                "JOIN Skills s ON es.SkillID = s.SkillID "
                f"WHERE s.SkillName = '{skill}' "
                "ORDER BY e.Name;"
            ),
            "medium",
            "skill_list_proficiency",
            ["Employees", "EmployeeSkills", "Skills"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"How many employees are expert in {skill}?",
            (
                "SELECT COUNT(DISTINCT e.EmpID) AS ExpertCount "
                "FROM Employees e "
                "JOIN EmployeeSkills es ON e.EmpID = es.EmpID "
                "JOIN Skills s ON es.SkillID = s.SkillID "
                f"WHERE s.SkillName = '{skill}' AND es.Proficiency = 'Expert';"
            ),
            "medium",
            "skill_expert_count",
            ["Employees", "EmployeeSkills", "Skills"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"What is the average salary of employees who have {skill}?",
            (
                "SELECT AVG(e.Salary) AS AvgSalaryWithSkill "
                "FROM Employees e "
                "JOIN EmployeeSkills es ON e.EmpID = es.EmpID "
                "JOIN Skills s ON es.SkillID = s.SkillID "
                f"WHERE s.SkillName = '{skill}';"
            ),
            "medium",
            "skill_salary_avg",
            ["Employees", "EmployeeSkills", "Skills"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"Which departments have employees with {skill}, and how many such employees are there per department?",
            (
                "SELECT d.DeptName, COUNT(DISTINCT e.EmpID) AS EmployeeCount "
                "FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                "JOIN EmployeeSkills es ON e.EmpID = es.EmpID "
                "JOIN Skills s ON es.SkillID = s.SkillID "
                f"WHERE s.SkillName = '{skill}' "
                "GROUP BY d.DeptID, d.DeptName "
                "ORDER BY EmployeeCount DESC;"
            ),
            "hard",
            "skill_department_distribution",
            ["Employees", "Departments", "EmployeeSkills", "Skills"],
        )

    # C) Location-focused queries (20)
    cities = ["Bangalore", "Mumbai", "Delhi", "Chennai"]
    for city in cities:
        next_id = add_case(
            new_cases,
            next_id,
            f"How many employees are based in {city}?",
            (
                "SELECT COUNT(*) AS EmployeeCount "
                "FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                "JOIN Locations l ON d.LocationID = l.LocationID "
                f"WHERE l.City = '{city}';"
            ),
            "medium",
            "location_employee_count",
            ["Employees", "Departments", "Locations"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"What is the average salary of employees in {city}?",
            (
                "SELECT AVG(e.Salary) AS AvgSalary "
                "FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                "JOIN Locations l ON d.LocationID = l.LocationID "
                f"WHERE l.City = '{city}';"
            ),
            "medium",
            "location_salary_avg",
            ["Employees", "Departments", "Locations"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"How many projects are managed from {city}?",
            (
                "SELECT COUNT(*) AS ProjectCount "
                "FROM Projects p "
                "JOIN Departments d ON p.DeptID = d.DeptID "
                "JOIN Locations l ON d.LocationID = l.LocationID "
                f"WHERE l.City = '{city}';"
            ),
            "medium",
            "location_project_count",
            ["Projects", "Departments", "Locations"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"What is the total project budget for projects in {city}?",
            (
                "SELECT SUM(p.Budget) AS TotalBudget "
                "FROM Projects p "
                "JOIN Departments d ON p.DeptID = d.DeptID "
                "JOIN Locations l ON d.LocationID = l.LocationID "
                f"WHERE l.City = '{city}';"
            ),
            "medium",
            "location_project_budget",
            ["Projects", "Departments", "Locations"],
        )
        next_id = add_case(
            new_cases,
            next_id,
            f"How many active employees are in {city}?",
            (
                "SELECT COUNT(*) AS ActiveEmployeeCount "
                "FROM Employees e "
                "JOIN Departments d ON e.DeptID = d.DeptID "
                "JOIN Locations l ON d.LocationID = l.LocationID "
                f"WHERE l.City = '{city}' AND e.Status = 'Active';"
            ),
            "medium",
            "location_active_employee_count",
            ["Employees", "Departments", "Locations"],
        )

    # D) Advanced global queries (30)
    advanced = [
        (
            "Rank employees by salary within each department.",
            "SELECT d.DeptName, e.Name, e.Salary, DENSE_RANK() OVER (PARTITION BY d.DeptID ORDER BY e.Salary DESC) AS SalaryRank FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID ORDER BY d.DeptName, SalaryRank;",
            "hard",
            "window_rank",
            ["Employees", "Departments"],
        ),
        (
            "Show the top earner in each department using window functions.",
            "WITH ranked AS (SELECT d.DeptName, e.Name, e.Salary, ROW_NUMBER() OVER (PARTITION BY d.DeptID ORDER BY e.Salary DESC) AS rn FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID) SELECT DeptName, Name, Salary FROM ranked WHERE rn = 1 ORDER BY Salary DESC;",
            "hard",
            "window_top_per_group",
            ["Employees", "Departments"],
        ),
        (
            "Compute a running total of project budget ordered by start date.",
            "SELECT ProjectName, StartDate, Budget, SUM(Budget) OVER (ORDER BY StartDate, ProjectID) AS RunningBudget FROM Projects ORDER BY StartDate, ProjectID;",
            "hard",
            "window_running_total",
            ["Projects"],
        ),
        (
            "List employees whose salary is above their department average salary.",
            "SELECT e.Name, d.DeptName, e.Salary FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID WHERE e.Salary > (SELECT AVG(e2.Salary) FROM Employees e2 WHERE e2.DeptID = e.DeptID) ORDER BY e.Salary DESC;",
            "hard",
            "correlated_subquery",
            ["Employees", "Departments"],
        ),
        (
            "Which departments have an average salary greater than the company average salary?",
            "SELECT d.DeptName, AVG(e.Salary) AS DeptAvgSalary FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID GROUP BY d.DeptID, d.DeptName HAVING AVG(e.Salary) > (SELECT AVG(Salary) FROM Employees) ORDER BY DeptAvgSalary DESC;",
            "hard",
            "having_subquery",
            ["Employees", "Departments"],
        ),
        (
            "List projects that currently have no assigned employees.",
            "SELECT p.ProjectName FROM Projects p LEFT JOIN EmployeeProjects ep ON p.ProjectID = ep.ProjectID WHERE ep.ProjectID IS NULL;",
            "medium",
            "anti_join",
            ["Projects", "EmployeeProjects"],
        ),
        (
            "List employees who are not assigned to any project.",
            "SELECT e.Name FROM Employees e LEFT JOIN EmployeeProjects ep ON e.EmpID = ep.EmpID WHERE ep.EmpID IS NULL;",
            "medium",
            "anti_join",
            ["Employees", "EmployeeProjects"],
        ),
        (
            "Which skills are held by at least three employees?",
            "SELECT s.SkillName, COUNT(DISTINCT es.EmpID) AS EmployeeCount FROM Skills s JOIN EmployeeSkills es ON s.SkillID = es.SkillID GROUP BY s.SkillID, s.SkillName HAVING COUNT(DISTINCT es.EmpID) >= 3 ORDER BY EmployeeCount DESC;",
            "medium",
            "having",
            ["Skills", "EmployeeSkills"],
        ),
        (
            "List pairs of employees who belong to the same department.",
            "SELECT e1.Name AS Employee1, e2.Name AS Employee2, d.DeptName FROM Employees e1 JOIN Employees e2 ON e1.DeptID = e2.DeptID AND e1.EmpID < e2.EmpID JOIN Departments d ON e1.DeptID = d.DeptID ORDER BY d.DeptName, e1.Name, e2.Name;",
            "hard",
            "self_join_pairs",
            ["Employees", "Departments"],
        ),
        (
            "Which department has the highest average logged hours per assigned employee?",
            "WITH dept_hours AS (SELECT d.DeptID, d.DeptName, SUM(ep.HoursLogged) AS TotalHours, COUNT(DISTINCT ep.EmpID) AS AssignedEmployees FROM Departments d JOIN Employees e ON d.DeptID = e.DeptID JOIN EmployeeProjects ep ON e.EmpID = ep.EmpID GROUP BY d.DeptID, d.DeptName) SELECT DeptName, CAST(TotalHours AS REAL) / AssignedEmployees AS AvgHoursPerAssignedEmployee FROM dept_hours ORDER BY AvgHoursPerAssignedEmployee DESC LIMIT 1;",
            "hard",
            "cte_aggregate_ratio",
            ["Departments", "Employees", "EmployeeProjects"],
        ),
        (
            "Which project has the highest average logged hours per member?",
            "SELECT p.ProjectName, CAST(SUM(ep.HoursLogged) AS REAL) / COUNT(DISTINCT ep.EmpID) AS AvgHoursPerMember FROM Projects p JOIN EmployeeProjects ep ON p.ProjectID = ep.ProjectID GROUP BY p.ProjectID, p.ProjectName ORDER BY AvgHoursPerMember DESC LIMIT 1;",
            "hard",
            "aggregate_ratio",
            ["Projects", "EmployeeProjects"],
        ),
        (
            "List employees who have both Leadership and Communication skills.",
            "SELECT e.Name FROM Employees e WHERE e.EmpID IN (SELECT es.EmpID FROM EmployeeSkills es JOIN Skills s ON es.SkillID = s.SkillID WHERE s.SkillName = 'Leadership') AND e.EmpID IN (SELECT es.EmpID FROM EmployeeSkills es JOIN Skills s ON es.SkillID = s.SkillID WHERE s.SkillName = 'Communication') ORDER BY e.Name;",
            "hard",
            "set_intersection",
            ["Employees", "EmployeeSkills", "Skills"],
        ),
        (
            "List employees who have at least one technical skill and at least one soft skill.",
            "SELECT e.Name FROM Employees e WHERE e.EmpID IN (SELECT es.EmpID FROM EmployeeSkills es JOIN Skills s ON es.SkillID = s.SkillID WHERE s.Category = 'Technical') AND e.EmpID IN (SELECT es.EmpID FROM EmployeeSkills es JOIN Skills s ON es.SkillID = s.SkillID WHERE s.Category = 'Soft') ORDER BY e.Name;",
            "hard",
            "set_intersection",
            ["Employees", "EmployeeSkills", "Skills"],
        ),
        (
            "Which departments have no completed projects?",
            "SELECT d.DeptName FROM Departments d WHERE d.DeptID NOT IN (SELECT DISTINCT p.DeptID FROM Projects p WHERE p.Status = 'Completed') ORDER BY d.DeptName;",
            "hard",
            "not_in_subquery",
            ["Departments", "Projects"],
        ),
        (
            "Find the earliest joined employee in each department.",
            "SELECT d.DeptName, e.Name, e.JoinDate FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID WHERE e.JoinDate = (SELECT MIN(e2.JoinDate) FROM Employees e2 WHERE e2.DeptID = e.DeptID) ORDER BY e.JoinDate;",
            "hard",
            "correlated_subquery",
            ["Employees", "Departments"],
        ),
        (
            "Find the latest joined employee in each department.",
            "SELECT d.DeptName, e.Name, e.JoinDate FROM Employees e JOIN Departments d ON e.DeptID = d.DeptID WHERE e.JoinDate = (SELECT MAX(e2.JoinDate) FROM Employees e2 WHERE e2.DeptID = e.DeptID) ORDER BY e.JoinDate DESC;",
            "hard",
            "correlated_subquery",
            ["Employees", "Departments"],
        ),
        (
            "List projects that started in 2025 and are not completed.",
            "SELECT ProjectName, Status, StartDate FROM Projects WHERE StartDate >= '2025-01-01' AND Status != 'Completed' ORDER BY StartDate;",
            "medium",
            "date_filter",
            ["Projects"],
        ),
        (
            "Show department-wise project count and average project budget.",
            "SELECT d.DeptName, COUNT(p.ProjectID) AS ProjectCount, AVG(p.Budget) AS AvgProjectBudget FROM Departments d LEFT JOIN Projects p ON d.DeptID = p.DeptID GROUP BY d.DeptID, d.DeptName ORDER BY ProjectCount DESC;",
            "medium",
            "join_aggregate",
            ["Departments", "Projects"],
        ),
        (
            "Compute active employee ratio per department.",
            "SELECT d.DeptName, SUM(CASE WHEN e.Status = 'Active' THEN 1 ELSE 0 END) AS ActiveEmployees, COUNT(e.EmpID) AS TotalEmployees, CAST(SUM(CASE WHEN e.Status = 'Active' THEN 1 ELSE 0 END) AS REAL) / COUNT(e.EmpID) AS ActiveRatio FROM Departments d JOIN Employees e ON d.DeptID = e.DeptID GROUP BY d.DeptID, d.DeptName ORDER BY ActiveRatio DESC;",
            "hard",
            "case_ratio",
            ["Departments", "Employees"],
        ),
        (
            "Which managers have at least one resigned direct report?",
            "SELECT DISTINCT m.Name AS ManagerName FROM Employees e JOIN Employees m ON e.ManagerID = m.EmpID WHERE e.Status = 'Resigned' ORDER BY ManagerName;",
            "medium",
            "self_join_filter",
            ["Employees"],
        ),
        (
            "List employees whose manager belongs to a different department.",
            "SELECT e.Name, m.Name AS ManagerName FROM Employees e JOIN Employees m ON e.ManagerID = m.EmpID WHERE e.DeptID != m.DeptID ORDER BY e.Name;",
            "hard",
            "self_join_filter",
            ["Employees"],
        ),
        (
            "Which project leads are from a different department than the owning project department?",
            "SELECT DISTINCT e.Name, p.ProjectName FROM EmployeeProjects ep JOIN Employees e ON ep.EmpID = e.EmpID JOIN Projects p ON ep.ProjectID = p.ProjectID WHERE ep.Role = 'Lead' AND e.DeptID != p.DeptID ORDER BY e.Name;",
            "hard",
            "cross_department_check",
            ["EmployeeProjects", "Employees", "Projects"],
        ),
        (
            "List skills not found among IT department employees.",
            "SELECT s.SkillName FROM Skills s WHERE s.SkillID NOT IN (SELECT DISTINCT es.SkillID FROM EmployeeSkills es JOIN Employees e ON es.EmpID = e.EmpID JOIN Departments d ON e.DeptID = d.DeptID WHERE d.DeptName = 'IT') ORDER BY s.SkillName;",
            "hard",
            "not_in_subquery",
            ["Skills", "EmployeeSkills", "Employees", "Departments"],
        ),
        (
            "Which departments have all employees active?",
            "SELECT d.DeptName FROM Departments d JOIN Employees e ON d.DeptID = e.DeptID GROUP BY d.DeptID, d.DeptName HAVING SUM(CASE WHEN e.Status != 'Active' THEN 1 ELSE 0 END) = 0 ORDER BY d.DeptName;",
            "hard",
            "having_case",
            ["Departments", "Employees"],
        ),
        (
            "Which employee is assigned to the highest number of projects?",
            "SELECT e.Name, COUNT(ep.ProjectID) AS ProjectCount FROM Employees e JOIN EmployeeProjects ep ON e.EmpID = ep.EmpID GROUP BY e.EmpID, e.Name ORDER BY ProjectCount DESC LIMIT 1;",
            "medium",
            "group_by_sort_limit",
            ["Employees", "EmployeeProjects"],
        ),
        (
            "How many employees have zero recorded skills?",
            "SELECT COUNT(*) AS EmployeesWithoutSkills FROM Employees e LEFT JOIN EmployeeSkills es ON e.EmpID = es.EmpID WHERE es.EmpID IS NULL;",
            "medium",
            "left_join_null",
            ["Employees", "EmployeeSkills"],
        ),
        (
            "For each project, how many assigned members have at least one expert-level skill?",
            "SELECT p.ProjectName, COUNT(DISTINCT ep.EmpID) AS ExpertMemberCount FROM Projects p LEFT JOIN EmployeeProjects ep ON p.ProjectID = ep.ProjectID LEFT JOIN EmployeeSkills es ON ep.EmpID = es.EmpID AND es.Proficiency = 'Expert' WHERE es.EmpID IS NOT NULL GROUP BY p.ProjectID, p.ProjectName ORDER BY ExpertMemberCount DESC;",
            "hard",
            "multi_join_aggregate",
            ["Projects", "EmployeeProjects", "EmployeeSkills"],
        ),
        (
            "Compute budget per active employee for each department.",
            "SELECT d.DeptName, d.Budget, SUM(CASE WHEN e.Status = 'Active' THEN 1 ELSE 0 END) AS ActiveEmployees, CAST(d.Budget AS REAL) / NULLIF(SUM(CASE WHEN e.Status = 'Active' THEN 1 ELSE 0 END), 0) AS BudgetPerActiveEmployee FROM Departments d JOIN Employees e ON d.DeptID = e.DeptID GROUP BY d.DeptID, d.DeptName, d.Budget ORDER BY BudgetPerActiveEmployee DESC;",
            "hard",
            "aggregate_ratio",
            ["Departments", "Employees"],
        ),
        (
            "Show each employee with number of skills and number of projects side-by-side.",
            "WITH skill_counts AS (SELECT EmpID, COUNT(*) AS SkillCount FROM EmployeeSkills GROUP BY EmpID), project_counts AS (SELECT EmpID, COUNT(*) AS ProjectCount FROM EmployeeProjects GROUP BY EmpID) SELECT e.Name, COALESCE(sc.SkillCount, 0) AS SkillCount, COALESCE(pc.ProjectCount, 0) AS ProjectCount FROM Employees e LEFT JOIN skill_counts sc ON e.EmpID = sc.EmpID LEFT JOIN project_counts pc ON e.EmpID = pc.EmpID ORDER BY e.Name;",
            "hard",
            "cte_multi_aggregate",
            ["Employees", "EmployeeSkills", "EmployeeProjects"],
        ),
        (
            "List departments sorted by total hours logged by their employees.",
            "SELECT d.DeptName, SUM(ep.HoursLogged) AS TotalHoursLogged FROM Departments d JOIN Employees e ON d.DeptID = e.DeptID JOIN EmployeeProjects ep ON e.EmpID = ep.EmpID GROUP BY d.DeptID, d.DeptName ORDER BY TotalHoursLogged DESC;",
            "medium",
            "join_aggregate",
            ["Departments", "Employees", "EmployeeProjects"],
        ),
        (
            "For each office type, how many departments and employees are there?",
            "SELECT l.OfficeType, COUNT(DISTINCT d.DeptID) AS DepartmentCount, COUNT(e.EmpID) AS EmployeeCount FROM Locations l LEFT JOIN Departments d ON l.LocationID = d.LocationID LEFT JOIN Employees e ON d.DeptID = e.DeptID GROUP BY l.OfficeType ORDER BY EmployeeCount DESC;",
            "medium",
            "multi_join_group_by",
            ["Locations", "Departments", "Employees"],
        ),
        (
            "Find employees who have more skills than projects assigned.",
            "WITH skill_counts AS (SELECT EmpID, COUNT(*) AS SkillCount FROM EmployeeSkills GROUP BY EmpID), project_counts AS (SELECT EmpID, COUNT(*) AS ProjectCount FROM EmployeeProjects GROUP BY EmpID) SELECT e.Name, COALESCE(sc.SkillCount, 0) AS SkillCount, COALESCE(pc.ProjectCount, 0) AS ProjectCount FROM Employees e LEFT JOIN skill_counts sc ON e.EmpID = sc.EmpID LEFT JOIN project_counts pc ON e.EmpID = pc.EmpID WHERE COALESCE(sc.SkillCount, 0) > COALESCE(pc.ProjectCount, 0) ORDER BY e.Name;",
            "hard",
            "cte_comparison",
            ["Employees", "EmployeeSkills", "EmployeeProjects"],
        ),
        (
            "Find projects where every assigned employee has at least one technical skill.",
            "SELECT p.ProjectName FROM Projects p WHERE NOT EXISTS (SELECT 1 FROM EmployeeProjects ep WHERE ep.ProjectID = p.ProjectID AND NOT EXISTS (SELECT 1 FROM EmployeeSkills es JOIN Skills s ON es.SkillID = s.SkillID WHERE es.EmpID = ep.EmpID AND s.Category = 'Technical')) ORDER BY p.ProjectName;",
            "hard",
            "double_not_exists",
            ["Projects", "EmployeeProjects", "EmployeeSkills", "Skills"],
        ),
    ]

    for question, sql, difficulty, category, tables_used in advanced:
        next_id = add_case(
            new_cases,
            next_id,
            question,
            sql,
            difficulty,
            category,
            tables_used,
        )

    if len(new_cases) < 150:
        raise RuntimeError(f"Expected at least 150 new cases, got {len(new_cases)}")
    if len(new_cases) > 150:
        new_cases = new_cases[:150]

    # Re-assign IDs after trimming to guarantee contiguous 51..200
    for i, item in enumerate(new_cases, start=51):
        item["id"] = i

    # Validate SQLs
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    errors = []
    for item in new_cases:
        try:
            cur.execute(item["sql"])
            cur.fetchall()
        except Exception as exc:
            errors.append((item["id"], item["question"], str(exc)))
    conn.close()

    if errors:
        for err in errors[:30]:
            print(err)
        raise RuntimeError(f"Validation failed for {len(errors)} generated cases")

    merged = base + new_cases
    with GOLDEN_SET_PATH.open("w") as f:
        json.dump(merged, f, indent=2)

    print(f"Added {len(new_cases)} new cases")
    print(f"Final count: {len(merged)}")
    print(f"ID range: {min(x['id'] for x in merged)}..{max(x['id'] for x in merged)}")


if __name__ == "__main__":
    main()
