import sqlite3
import os

DB_PATH = os.path.join("data", "company.db")

def setup_database():
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON")

    # ── Drop in reverse dependency order ──────────────────────────────────────
    cursor.execute("DROP TABLE IF EXISTS EmployeeSkills")
    cursor.execute("DROP TABLE IF EXISTS Skills")
    cursor.execute("DROP TABLE IF EXISTS EmployeeProjects")
    cursor.execute("DROP TABLE IF EXISTS Projects")
    cursor.execute("DROP TABLE IF EXISTS Employees")
    cursor.execute("DROP TABLE IF EXISTS Departments")
    cursor.execute("DROP TABLE IF EXISTS Locations")

    # ── 1. Locations ──────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE Locations (
        LocationID   INTEGER PRIMARY KEY,
        City         TEXT NOT NULL,
        Country      TEXT NOT NULL,
        OfficeType   TEXT NOT NULL   -- 'HQ', 'Regional', 'Remote Hub'
    )
    ''')

    # ── 2. Departments ────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE Departments (
        DeptID       INTEGER PRIMARY KEY,
        DeptName     TEXT NOT NULL,
        ManagerName  TEXT,
        LocationID   INTEGER,
        Budget       INTEGER,
        FOREIGN KEY (LocationID) REFERENCES Locations(LocationID)
    )
    ''')

    # ── 3. Employees ──────────────────────────────────────────────────────────
    # ManagerID is a self-reference (who this employee reports to)
    cursor.execute('''
    CREATE TABLE Employees (
        EmpID        INTEGER PRIMARY KEY,
        Name         TEXT NOT NULL,
        Role         TEXT,
        Salary       INTEGER,
        JoinDate     TEXT,           -- YYYY-MM-DD
        DeptID       INTEGER,
        ManagerID    INTEGER,        -- References another EmpID (self-join)
        Status       TEXT,           -- 'Active', 'On Leave', 'Resigned'
        FOREIGN KEY (DeptID)    REFERENCES Departments(DeptID),
        FOREIGN KEY (ManagerID) REFERENCES Employees(EmpID)
    )
    ''')

    # ── 4. Projects ───────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE Projects (
        ProjectID    INTEGER PRIMARY KEY,
        ProjectName  TEXT NOT NULL,
        Budget       INTEGER,
        Status       TEXT,           -- 'Pending', 'In Progress', 'Completed', 'On Hold'
        StartDate    TEXT,           -- YYYY-MM-DD
        EndDate      TEXT,           -- YYYY-MM-DD  (NULL if not finished)
        DeptID       INTEGER,
        FOREIGN KEY (DeptID) REFERENCES Departments(DeptID)
    )
    ''')

    # ── 5. EmployeeProjects (junction) ────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE EmployeeProjects (
        EmpID        INTEGER,
        ProjectID    INTEGER,
        Role         TEXT,           -- role on THIS project e.g. 'Lead', 'Member'
        HoursLogged  INTEGER,
        PRIMARY KEY (EmpID, ProjectID),
        FOREIGN KEY (EmpID)      REFERENCES Employees(EmpID),
        FOREIGN KEY (ProjectID)  REFERENCES Projects(ProjectID)
    )
    ''')

    # ── 6. Skills ─────────────────────────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE Skills (
        SkillID      INTEGER PRIMARY KEY,
        SkillName    TEXT NOT NULL,
        Category     TEXT            -- 'Technical', 'Soft', 'Domain'
    )
    ''')

    # ── 7. EmployeeSkills (junction) ──────────────────────────────────────────
    cursor.execute('''
    CREATE TABLE EmployeeSkills (
        EmpID        INTEGER,
        SkillID      INTEGER,
        Proficiency  TEXT,           -- 'Beginner', 'Intermediate', 'Expert'
        PRIMARY KEY (EmpID, SkillID),
        FOREIGN KEY (EmpID)    REFERENCES Employees(EmpID),
        FOREIGN KEY (SkillID)  REFERENCES Skills(SkillID)
    )
    ''')

    # ── INSERT DATA ───────────────────────────────────────────────────────────

    # Locations (4 offices)
    cursor.executemany("INSERT INTO Locations VALUES (?,?,?,?)", [
        (1, 'Bangalore',  'India',  'HQ'),
        (2, 'Mumbai',     'India',  'Regional'),
        (3, 'Delhi',      'India',  'Regional'),
        (4, 'Chennai',    'India',  'Remote Hub'),
    ])

    # Departments (5 departments, spread across offices)
    cursor.executemany("INSERT INTO Departments VALUES (?,?,?,?,?)", [
        (1, 'IT',         'Rohan Gupta',   1, 2000000),
        (2, 'Sales',      'Anita Desai',   2, 800000),
        (3, 'HR',         'Suresh Kumar',  3, 400000),
        (4, 'Finance',    'Meena Iyer',    2, 600000),
        (5, 'Operations', 'Raj Pillai',    4, 500000),
    ])

    # Employees (20 employees, varied salaries, departments, statuses)
    # Format: EmpID, Name, Role, Salary, JoinDate, DeptID, ManagerID, Status
    cursor.executemany("INSERT INTO Employees VALUES (?,?,?,?,?,?,?,?)", [
        # IT Department (DeptID=1) — Manager is Rohan Gupta (EmpID 101)
        (101, 'Arjun Singh',      'Data Engineer',      85000, '2023-01-15', 1, None,  'Active'),
        (102, 'Priya Sharma',     'Backend Developer',  92000, '2022-06-20', 1, 101,   'Active'),
        (103, 'Amit Verma',       'DevOps Lead',        105000,'2021-03-10', 1, 101,   'Active'),
        (104, 'Vikram Malhotra',  'Frontend Developer', 78000, '2023-08-01', 1, 101,   'Active'),
        (105, 'Nisha Kapoor',     'QA Engineer',        65000, '2024-02-14', 1, 103,   'Active'),
        (106, 'Rahul Mehta',      'ML Engineer',        110000,'2022-11-05', 1, 101,   'On Leave'),

        # Sales Department (DeptID=2) — Manager is Anita Desai (EmpID 107)
        (107, 'Kavya Nair',       'Sales Executive',    55000, '2023-05-22', 2, None,  'Active'),
        (108, 'Deepak Joshi',     'Sales Rep',          48000, '2024-03-01', 2, 107,   'Active'),
        (109, 'Sunita Rao',       'Account Manager',    72000, '2022-09-12', 2, 107,   'Active'),
        (110, 'Manish Tiwari',    'Sales Rep',          45000, '2023-11-15', 2, 107,   'Resigned'),

        # HR Department (DeptID=3) — Manager is Suresh Kumar (EmpID 111)
        (111, 'Sneha Patel',      'HR Manager',         68000, '2021-07-01', 3, None,  'Active'),
        (112, 'Pooja Menon',      'Recruiter',          42000, '2024-01-10', 3, 111,   'Active'),
        (113, 'Arun Pillai',      'L&D Specialist',     50000, '2023-06-18', 3, 111,   'Active'),

        # Finance Department (DeptID=4) — Manager is Meena Iyer (EmpID 114)
        (114, 'Rohit Sinha',      'Finance Analyst',    82000, '2022-04-05', 4, None,  'Active'),
        (115, 'Lalita Sharma',    'Accountant',         58000, '2023-02-28', 4, 114,   'Active'),
        (116, 'Vishal Gupta',     'Tax Specialist',     75000, '2021-12-20', 4, 114,   'Active'),

        # Operations Department (DeptID=5) — Manager is Raj Pillai (EmpID 117)
        (117, 'Divya Krishnan',   'Ops Manager',        88000, '2020-09-15', 5, None,  'Active'),
        (118, 'Karthik Reddy',    'Logistics Lead',     67000, '2022-03-01', 5, 117,   'Active'),
        (119, 'Bhavna Desai',     'Process Analyst',    54000, '2023-10-05', 5, 117,   'Active'),
        (120, 'Sanjay Iyer',      'Ops Analyst',        61000, '2024-04-20', 5, 117,   'Active'),
    ])

    # Projects (10 projects across departments)
    # Format: ProjectID, ProjectName, Budget, Status, StartDate, EndDate, DeptID
    cursor.executemany("INSERT INTO Projects VALUES (?,?,?,?,?,?,?)", [
        (1,  'Cloud Migration',        500000, 'In Progress', '2025-01-01', None,         1),
        (2,  'ML Pipeline Setup',      300000, 'In Progress', '2025-03-01', None,         1),
        (3,  'API Gateway Redesign',   150000, 'Completed',   '2024-06-01', '2024-11-30', 1),
        (4,  'CRM Upgrade',            200000, 'Pending',     '2025-07-01', None,         2),
        (5,  'Q1 Sales Campaign',       50000, 'Completed',   '2025-01-01', '2025-03-31', 2),
        (6,  'Annual Hiring Drive',     80000, 'In Progress', '2025-02-01', None,         3),
        (7,  'Employee Wellness Plan',  30000, 'Completed',   '2024-10-01', '2024-12-31', 3),
        (8,  'Budget Forecasting Tool', 90000, 'On Hold',     '2025-04-01', None,         4),
        (9,  'ERP Integration',        450000, 'In Progress', '2025-02-15', None,         5),
        (10, 'Warehouse Automation',   700000, 'Pending',     '2025-09-01', None,         5),
    ])

    # EmployeeProjects (who works on which project, their role, hours logged)
    cursor.executemany("INSERT INTO EmployeeProjects VALUES (?,?,?,?)", [
        (101, 1,  'Member', 120),
        (102, 1,  'Lead',   200),
        (103, 1,  'Member', 180),
        (101, 2,  'Lead',   160),
        (106, 2,  'Member', 140),
        (104, 3,  'Lead',   110),
        (105, 3,  'Member',  90),
        (107, 4,  'Member',  60),
        (109, 4,  'Lead',    80),
        (107, 5,  'Lead',   100),
        (108, 5,  'Member',  70),
        (111, 6,  'Lead',   130),
        (112, 6,  'Member',  90),
        (113, 7,  'Member',  50),
        (111, 7,  'Lead',    60),
        (114, 8,  'Lead',    95),
        (115, 8,  'Member',  55),
        (117, 9,  'Lead',   210),
        (118, 9,  'Member', 175),
        (119, 9,  'Member', 130),
        (117, 10, 'Lead',    40),
        (120, 10, 'Member',  20),
    ])

    # Skills (10 skills)
    cursor.executemany("INSERT INTO Skills VALUES (?,?,?)", [
        (1,  'Python',          'Technical'),
        (2,  'SQL',             'Technical'),
        (3,  'AWS',             'Technical'),
        (4,  'Machine Learning','Technical'),
        (5,  'Leadership',      'Soft'),
        (6,  'Communication',   'Soft'),
        (7,  'Financial Modeling','Domain'),
        (8,  'Recruitment',     'Domain'),
        (9,  'Docker',          'Technical'),
        (10, 'Data Analysis',   'Technical'),
    ])

    # EmployeeSkills (each employee has 2-4 skills)
    cursor.executemany("INSERT INTO EmployeeSkills VALUES (?,?,?)", [
        (101, 1,  'Expert'),
        (101, 2,  'Expert'),
        (101, 10, 'Intermediate'),
        (102, 1,  'Expert'),
        (102, 9,  'Intermediate'),
        (102, 3,  'Intermediate'),
        (103, 3,  'Expert'),
        (103, 9,  'Expert'),
        (103, 5,  'Intermediate'),
        (104, 1,  'Intermediate'),
        (104, 2,  'Beginner'),
        (105, 2,  'Intermediate'),
        (105, 10, 'Beginner'),
        (106, 1,  'Expert'),
        (106, 4,  'Expert'),
        (106, 10, 'Expert'),
        (107, 5,  'Expert'),
        (107, 6,  'Expert'),
        (108, 6,  'Intermediate'),
        (109, 5,  'Intermediate'),
        (109, 6,  'Expert'),
        (111, 5,  'Expert'),
        (111, 8,  'Expert'),
        (112, 8,  'Intermediate'),
        (113, 6,  'Intermediate'),
        (114, 7,  'Expert'),
        (114, 2,  'Intermediate'),
        (115, 7,  'Intermediate'),
        (116, 7,  'Expert'),
        (117, 5,  'Expert'),
        (117, 6,  'Intermediate'),
        (118, 10, 'Intermediate'),
        (119, 10, 'Expert'),
        (120, 2,  'Beginner'),
    ])

    conn.commit()
    conn.close()
    print(f"✅ Enhanced database created at {DB_PATH}")
    print("   Tables: Locations, Departments, Employees, Projects, EmployeeProjects, Skills, EmployeeSkills")
    print("   Rows  : 4 locations | 5 departments | 20 employees | 10 projects | 22 assignments | 10 skills | 34 skill records")

if __name__ == "__main__":
    setup_database()