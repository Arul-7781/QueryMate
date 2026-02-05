import sqlite3
import os

# Define the path to ensure it goes into the 'data' folder
DB_PATH = os.path.join("data", "company.db")

def setup_database():
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Cleanup: Drop tables if they exist (Fresh start)
    cursor.execute('DROP TABLE IF EXISTS Projects')
    cursor.execute('DROP TABLE IF EXISTS Employees')
    cursor.execute('DROP TABLE IF EXISTS Departments')

    # 2. Create Tables
    cursor.execute('''
    CREATE TABLE Departments (
        DeptID INTEGER PRIMARY KEY,
        DeptName TEXT NOT NULL,
        ManagerName TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE Employees (
        EmpID INTEGER PRIMARY KEY,
        Name TEXT NOT NULL,
        Role TEXT,
        Salary INTEGER,
        JoinDate TEXT,
        DeptID INTEGER,
        FOREIGN KEY (DeptID) REFERENCES Departments(DeptID)
    )
    ''')

    cursor.execute('''
    CREATE TABLE Projects (
        ProjectID INTEGER PRIMARY KEY,
        ProjectName TEXT,
        Budget INTEGER,
        Status TEXT,
        DeptID INTEGER,
        FOREIGN KEY (DeptID) REFERENCES Departments(DeptID)
    )
    ''')

    # 3. Insert Dummy Data
    departments = [
        (1, 'IT', 'Rohan Gupta'),
        (2, 'Sales', 'Anita Desai'),
        (3, 'HR', 'Suresh Kumar')
    ]
    cursor.executemany('INSERT INTO Departments VALUES (?, ?, ?)', departments)

    employees = [
        (101, 'Arjun Singh', 'Data Engineer', 85000, '2023-01-15', 1),
        (102, 'Priya Sharma', 'Sales Rep', 45000, '2023-03-10', 2),
        (103, 'Amit Verma', 'DevOps Lead', 95000, '2022-06-20', 1),
        (104, 'Sneha Patel', 'Recruiter', 40000, '2024-01-05', 3),
        (105, 'Vikram Malhotra', 'Frontend Dev', 75000, '2023-08-01', 1)
    ]
    cursor.executemany('INSERT INTO Employees VALUES (?, ?, ?, ?, ?, ?)', employees)

    projects = [
        (1, 'Cloud Migration', 500000, 'In Progress', 1),
        (2, 'Q1 Hiring Drive', 20000, 'Completed', 3),
        (3, 'CRM Upgrade', 150000, 'Pending', 2)
    ]
    cursor.executemany('INSERT INTO Projects VALUES (?, ?, ?, ?, ?)', projects)

    conn.commit()
    conn.close()
    print(f"Database created successfully at {DB_PATH}")

if __name__ == "__main__":
    setup_database()