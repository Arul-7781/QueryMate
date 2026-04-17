import random
import shutil
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SRC_DB = Path("data/company.db")
DST_DB = Path("data/company_expanded.db")
SEED = 42


def choose(rng, seq):
    return seq[rng.randrange(len(seq))]


def date_str(d: date) -> str:
    return d.isoformat()


def bounded_date(rng, start: date, end: date) -> str:
    span = (end - start).days
    return date_str(start + timedelta(days=rng.randint(0, span)))


def get_max_id(cur, table: str, col: str) -> int:
    cur.execute(f"SELECT COALESCE(MAX({col}), 0) FROM {table}")
    return int(cur.fetchone()[0])


def fetch_rows(cur, sql: str):
    cur.execute(sql)
    return cur.fetchall()


def main():
    if not SRC_DB.exists():
        raise FileNotFoundError(f"Missing source DB: {SRC_DB}")

    DST_DB.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC_DB, DST_DB)

    rng = random.Random(SEED)

    conn = sqlite3.connect(DST_DB)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    # Existing base references
    existing_depts = fetch_rows(cur, "SELECT DeptID, DeptName FROM Departments ORDER BY DeptID")
    existing_dept_ids = [d[0] for d in existing_depts]

    # 1) Add new locations
    next_location_id = get_max_id(cur, "Locations", "LocationID") + 1
    new_locations = [
        (next_location_id + 0, "Hyderabad", "India", "Regional"),
        (next_location_id + 1, "Pune", "India", "Regional"),
        (next_location_id + 2, "Kolkata", "India", "Regional"),
        (next_location_id + 3, "Ahmedabad", "India", "Remote Hub"),
        (next_location_id + 4, "Coimbatore", "India", "Remote Hub"),
        (next_location_id + 5, "Jaipur", "India", "Remote Hub"),
    ]
    cur.executemany("INSERT INTO Locations (LocationID, City, Country, OfficeType) VALUES (?,?,?,?)", new_locations)

    # 2) Add new departments
    next_dept_id = get_max_id(cur, "Departments", "DeptID") + 1
    extra_dept_specs = [
        ("Legal", "Neeraj Bhatia", new_locations[0][0], 520000),
        ("Marketing", "Ira Sen", new_locations[1][0], 740000),
        ("Procurement", "Harsh Vora", new_locations[2][0], 610000),
        ("Security", "Avni Narang", new_locations[3][0], 690000),
        ("R&D", "Farhan Ali", new_locations[4][0], 950000),
    ]
    new_departments = []
    for i, spec in enumerate(extra_dept_specs):
        new_departments.append((next_dept_id + i, spec[0], spec[1], spec[2], spec[3]))
    cur.executemany(
        "INSERT INTO Departments (DeptID, DeptName, ManagerName, LocationID, Budget) VALUES (?,?,?,?,?)",
        new_departments,
    )

    all_dept_rows = fetch_rows(cur, "SELECT DeptID, DeptName FROM Departments ORDER BY DeptID")
    all_dept_ids = [r[0] for r in all_dept_rows]

    # 3) Add skills
    next_skill_id = get_max_id(cur, "Skills", "SkillID") + 1
    new_skills = [
        (next_skill_id + 0, "Kubernetes", "Technical"),
        (next_skill_id + 1, "Tableau", "Technical"),
        (next_skill_id + 2, "Power BI", "Technical"),
        (next_skill_id + 3, "Cybersecurity", "Technical"),
        (next_skill_id + 4, "Negotiation", "Soft"),
        (next_skill_id + 5, "Risk Management", "Domain"),
        (next_skill_id + 6, "Contract Law", "Domain"),
        (next_skill_id + 7, "Inventory Planning", "Domain"),
        (next_skill_id + 8, "NLP", "Technical"),
        (next_skill_id + 9, "A/B Testing", "Technical"),
        (next_skill_id + 10, "Public Speaking", "Soft"),
        (next_skill_id + 11, "Stakeholder Management", "Soft"),
    ]
    cur.executemany("INSERT INTO Skills (SkillID, SkillName, Category) VALUES (?,?,?)", new_skills)

    skill_ids = [r[0] for r in fetch_rows(cur, "SELECT SkillID FROM Skills ORDER BY SkillID")]

    # 4) Add many employees with deterministic naming and manager hierarchy per department
    first_names = [
        "Aarav", "Aisha", "Vihaan", "Anaya", "Ishaan", "Sara", "Aditya", "Myra",
        "Kabir", "Riya", "Reyansh", "Diya", "Arnav", "Kiara", "Krish", "Tara",
        "Yash", "Navya", "Nakul", "Meher", "Dev", "Pari", "Atharv", "Sia",
        "Rudra", "Isha", "Samar", "Naina", "Ayaan", "Mira", "Kian", "Anika",
    ]
    last_names = [
        "Khanna", "Bose", "Kapoor", "Rastogi", "Kulkarni", "Panda", "Chawla", "Saxena",
        "Banerjee", "Agarwal", "Bhardwaj", "Dutta", "Naidu", "Bhandari", "Rana", "Sethi",
        "Ghosh", "Jain", "Bhalla", "Sood", "Mishra", "Puri", "Talwar", "Pathak",
    ]

    role_map = {
        "IT": ["Data Engineer", "Backend Developer", "DevOps Engineer", "ML Engineer", "QA Engineer"],
        "Sales": ["Sales Executive", "Sales Rep", "Account Manager", "Growth Associate"],
        "HR": ["HR Manager", "Recruiter", "L&D Specialist", "HR Analyst"],
        "Finance": ["Finance Analyst", "Accountant", "Tax Specialist", "FP&A Analyst"],
        "Operations": ["Ops Manager", "Logistics Lead", "Process Analyst", "Supply Planner"],
        "Legal": ["Legal Counsel", "Compliance Analyst", "Contract Specialist"],
        "Marketing": ["Marketing Manager", "Performance Marketer", "Content Strategist", "SEO Analyst"],
        "Procurement": ["Procurement Manager", "Vendor Analyst", "Sourcing Specialist"],
        "Security": ["Security Analyst", "SOC Engineer", "Risk Analyst"],
        "R&D": ["Research Scientist", "Applied ML Engineer", "Data Scientist", "Prototype Engineer"],
    }

    status_choices = ["Active", "Active", "Active", "On Leave", "Resigned"]

    existing_names = {r[0] for r in fetch_rows(cur, "SELECT Name FROM Employees")}
    next_emp_id = get_max_id(cur, "Employees", "EmpID") + 1
    employees_to_add = []
    manager_by_dept = {}

    # Add one manager-like employee per dept first (for new + existing departments)
    dept_name_by_id = {d[0]: d[1] for d in fetch_rows(cur, "SELECT DeptID, DeptName FROM Departments")}
    for dept_id in all_dept_ids:
        dept_name = dept_name_by_id[dept_id]
        manager_name = f"{dept_name} Manager {dept_id}"
        salary = rng.randint(95000, 145000)
        join_date = bounded_date(rng, date(2019, 1, 1), date(2023, 6, 30))
        employees_to_add.append((next_emp_id, manager_name, "Department Manager", salary, join_date, dept_id, None, "Active"))
        manager_by_dept[dept_id] = next_emp_id
        existing_names.add(manager_name)
        next_emp_id += 1

    target_new_employees = 320
    while len(employees_to_add) < (len(all_dept_ids) + target_new_employees):
        dept_id = choose(rng, all_dept_ids)
        dept_name = dept_name_by_id[dept_id]
        role_choices = role_map.get(dept_name, ["Specialist", "Analyst", "Associate"])
        role = choose(rng, role_choices)

        first = choose(rng, first_names)
        last = choose(rng, last_names)
        suffix = rng.randint(1, 999)
        name = f"{first} {last} {suffix}"
        if name in existing_names:
            continue

        base_low, base_high = (45000, 95000)
        if "Manager" in role or "Lead" in role or "Scientist" in role:
            base_low, base_high = (70000, 130000)

        salary = rng.randint(base_low, base_high)
        join_date = bounded_date(rng, date(2020, 1, 1), date(2026, 2, 1))
        manager_id = manager_by_dept[dept_id]
        status = choose(rng, status_choices)

        employees_to_add.append((next_emp_id, name, role, salary, join_date, dept_id, manager_id, status))
        existing_names.add(name)
        next_emp_id += 1

    cur.executemany(
        "INSERT INTO Employees (EmpID, Name, Role, Salary, JoinDate, DeptID, ManagerID, Status) VALUES (?,?,?,?,?,?,?,?)",
        employees_to_add,
    )

    # 5) Add projects
    next_project_id = get_max_id(cur, "Projects", "ProjectID") + 1
    project_statuses = ["Pending", "In Progress", "Completed", "On Hold"]
    project_prefixes = [
        "Automation", "Platform", "Optimization", "Revamp", "Initiative", "Program",
        "Migration", "Expansion", "Analytics", "Governance", "Modernization",
    ]

    projects_to_add = []
    for i in range(180):
        dept_id = choose(rng, all_dept_ids)
        dept_name = dept_name_by_id[dept_id]
        status = choose(rng, project_statuses)
        start = bounded_date(rng, date(2023, 1, 1), date(2026, 3, 1))

        end_date = None
        if status == "Completed":
            s = date.fromisoformat(start)
            end_date = date_str(s + timedelta(days=rng.randint(45, 300)))

        name = f"{choose(rng, project_prefixes)} {dept_name} {i + 1}"
        budget = rng.randint(40000, 900000)

        projects_to_add.append((next_project_id + i, name, budget, status, start, end_date, dept_id))

    cur.executemany(
        "INSERT INTO Projects (ProjectID, ProjectName, Budget, Status, StartDate, EndDate, DeptID) VALUES (?,?,?,?,?,?,?)",
        projects_to_add,
    )

    # 6) Add employee-project assignments
    all_projects = fetch_rows(cur, "SELECT ProjectID, DeptID FROM Projects")
    dept_emp_map = {}
    for dept_id in all_dept_ids:
        dept_emp_map[dept_id] = [r[0] for r in fetch_rows(cur, f"SELECT EmpID FROM Employees WHERE DeptID = {dept_id}")]

    existing_ep_pairs = set(fetch_rows(cur, "SELECT EmpID, ProjectID FROM EmployeeProjects"))
    ep_rows = []

    for project_id, dept_id in all_projects:
        pool = dept_emp_map.get(dept_id, [])
        if len(pool) < 3:
            pool = [r[0] for r in fetch_rows(cur, "SELECT EmpID FROM Employees")]

        rng.shuffle(pool)
        team_size = min(max(3, rng.randint(3, 7)), len(pool))
        team = pool[:team_size]
        lead = team[0]

        for idx, emp_id in enumerate(team):
            pair = (emp_id, project_id)
            if pair in existing_ep_pairs:
                continue
            role = "Lead" if idx == 0 else "Member"
            hours = rng.randint(20, 280)
            ep_rows.append((emp_id, project_id, role, hours))
            existing_ep_pairs.add(pair)

    cur.executemany(
        "INSERT INTO EmployeeProjects (EmpID, ProjectID, Role, HoursLogged) VALUES (?,?,?,?)",
        ep_rows,
    )

    # 7) Add employee-skill assignments
    existing_es_pairs = set(fetch_rows(cur, "SELECT EmpID, SkillID FROM EmployeeSkills"))
    es_rows = []
    profs = ["Beginner", "Intermediate", "Expert"]
    all_emp_ids = [r[0] for r in fetch_rows(cur, "SELECT EmpID FROM Employees")]

    for emp_id in all_emp_ids:
        k = rng.randint(3, 6)
        chosen_skills = rng.sample(skill_ids, k=min(k, len(skill_ids)))
        for skill_id in chosen_skills:
            pair = (emp_id, skill_id)
            if pair in existing_es_pairs:
                continue
            proficiency = choose(rng, profs)
            es_rows.append((emp_id, skill_id, proficiency))
            existing_es_pairs.add(pair)

    cur.executemany(
        "INSERT INTO EmployeeSkills (EmpID, SkillID, Proficiency) VALUES (?,?,?)",
        es_rows,
    )

    conn.commit()

    summary = {
        "Locations": fetch_rows(cur, "SELECT COUNT(*) FROM Locations")[0][0],
        "Departments": fetch_rows(cur, "SELECT COUNT(*) FROM Departments")[0][0],
        "Employees": fetch_rows(cur, "SELECT COUNT(*) FROM Employees")[0][0],
        "Projects": fetch_rows(cur, "SELECT COUNT(*) FROM Projects")[0][0],
        "EmployeeProjects": fetch_rows(cur, "SELECT COUNT(*) FROM EmployeeProjects")[0][0],
        "Skills": fetch_rows(cur, "SELECT COUNT(*) FROM Skills")[0][0],
        "EmployeeSkills": fetch_rows(cur, "SELECT COUNT(*) FROM EmployeeSkills")[0][0],
    }

    conn.close()

    print(f"Created expanded DB: {DST_DB}")
    for k, v in summary.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
