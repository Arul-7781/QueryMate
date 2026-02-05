# 💾 Understanding SQLite in QueryMate

## What is SQLite?

SQLite is a **self-contained, serverless, file-based database**. Let me break that down:

### Traditional Databases (MySQL, PostgreSQL):
```
┌─────────────┐         ┌──────────────┐
│ Your App    │ ────────▶│ Database     │
│             │   TCP/IP │ Server       │
│             │◀────────│              │
└─────────────┘         └──────────────┘
                        Runs separately,
                        needs configuration,
                        port 3306/5432
```

**Requirements:**
- Separate server process running 24/7
- Network connection (even if localhost)
- User authentication
- Configuration files
- Memory/CPU overhead

---

### SQLite (What You're Using):
```
┌─────────────────────────────┐
│ Your App                    │
│  ├── Code (Python)          │
│  └── Database (file.db) ◀───┼─ Just a file!
└─────────────────────────────┘
```

**No server needed!**
- Database = Single file (`company.db`)
- No separate process
- No network overhead
- No authentication needed
- Zero configuration

---

## Where is Your Database?

### File Location:
```
/Users/arul/ws/projects/QueryMate/
└── data/
    └── company.db  ← YOUR DATABASE IS HERE!
```

**Absolute Path:**
```
/Users/arul/ws/projects/QueryMate/data/company.db
```

**Size:** ~16 KB (tiny! fits on a floppy disk)

---

## What's Inside company.db?

Your database file contains **everything**:
- Table structures (schemas)
- All data (rows)
- Indexes
- Metadata

### Current Structure:

```
company.db
├── Departments (3 rows)
│   ├── DeptID (Primary Key)
│   ├── DeptName
│   └── ManagerName
│
├── Employees (5 rows)
│   ├── EmpID (Primary Key)
│   ├── Name
│   ├── Role
│   ├── Salary
│   ├── JoinDate
│   └── DeptID (Foreign Key → Departments)
│
└── Projects (3 rows)
    ├── ProjectID (Primary Key)
    ├── ProjectName
    ├── Budget
    ├── Status
    └── DeptID (Foreign Key → Departments)
```

---

## How Your Code Uses SQLite

### Step 1: Connect (src/db_setup.py)
```python
import sqlite3

# This creates/opens the file data/company.db
conn = sqlite3.connect("data/company.db")
cursor = conn.cursor()
```

**What happens:**
- If file doesn't exist → SQLite creates it
- If file exists → SQLite opens it
- Returns a "connection" object to interact with it

### Step 2: Execute SQL Commands
```python
# Create a table
cursor.execute('''
    CREATE TABLE Employees (
        EmpID INTEGER PRIMARY KEY,
        Name TEXT NOT NULL,
        ...
    )
''')

# Insert data
cursor.execute("INSERT INTO Employees VALUES (101, 'Arjun', ...)")

# Query data
cursor.execute("SELECT * FROM Employees")
results = cursor.fetchall()  # Returns: [(101, 'Arjun', ...), ...]
```

### Step 3: Save Changes
```python
conn.commit()  # Writes changes to disk
conn.close()   # Closes the file
```

---

## Real-World Analogy

Think of SQLite like:

### Traditional Database = Restaurant Kitchen
- Separate building (server)
- Staff running 24/7 (processes)
- You order through waiters (network)
- Complex organization (configuration)

### SQLite = Meal Prep Container
- Self-contained box (file)
- Open when needed, close when done
- No staff required
- Take it anywhere
- Perfect for personal use

---

## How to Inspect Your Database

### Method 1: Command Line (SQLite CLI)

```bash
# Open the database
sqlite3 data/company.db

# Common commands:
.tables                    # List all tables
.schema Employees          # Show table structure
SELECT * FROM Employees;   # Query data
.exit                      # Quit
```

### Method 2: GUI Tools

**DB Browser for SQLite** (Free):
- Download: https://sqlitebrowser.org/
- Open `data/company.db`
- Visual interface to browse/edit

**DataGrip** (Paid, but powerful):
- JetBrains tool
- Professional database IDE

### Method 3: Python Script
```python
import sqlite3

conn = sqlite3.connect('data/company.db')
cursor = conn.cursor()

# Show all employees
cursor.execute("SELECT * FROM Employees")
for row in cursor.fetchall():
    print(row)

conn.close()
```

### Method 4: Your QueryMate App!
Just ask: "Show all employees" 😊

---

## Quick Tests You Can Run

### 1. Count Records
```bash
sqlite3 data/company.db "SELECT COUNT(*) FROM Employees;"
# Output: 5
```

### 2. See All Departments
```bash
sqlite3 data/company.db "SELECT * FROM Departments;"
# Output:
# 1|IT|Rohan Gupta
# 2|Sales|Anita Desai
# 3|HR|Suresh Kumar
```

### 3. Join Tables
```bash
sqlite3 data/company.db "
SELECT e.Name, e.Role, d.DeptName 
FROM Employees e 
JOIN Departments d ON e.DeptID = d.DeptID 
LIMIT 3;
"
# Output:
# Arjun Singh|Data Engineer|IT
# Priya Sharma|Sales Rep|Sales
# Amit Verma|DevOps Lead|IT
```

---

## SQLite vs Other Databases

| Feature | SQLite | MySQL | PostgreSQL |
|---------|--------|-------|------------|
| **Setup** | None! | Install server | Install server |
| **Storage** | Single file | Many files | Many files |
| **Server** | No | Yes | Yes |
| **Network** | No | TCP/IP | TCP/IP |
| **Users** | No auth | Multi-user | Multi-user |
| **Size Limit** | 281 TB | Unlimited | Unlimited |
| **Concurrent Writes** | 1 at a time | Many | Many |
| **Speed (Reads)** | Very fast | Fast | Fast |
| **Use Case** | Apps, testing | Web apps | Enterprise |

**Your project = Perfect for SQLite!**

---

## Why SQLite for QueryMate?

### ✅ Advantages for Your Project:

1. **Zero Setup**
   - No installation
   - No configuration
   - Works immediately

2. **Portable**
   - Copy `company.db` to another computer
   - Works instantly
   - No migration needed

3. **Fast for Small Data**
   - Your 11 rows? Lightning fast!
   - No network latency
   - Direct file access

4. **Perfect for Learning**
   - Simple to understand
   - Easy to inspect
   - No complexity overhead

5. **Industry Standard**
   - Used in: Android, iOS, browsers, IoT
   - Most deployed database in the world!
   - 1+ trillion active instances

### ⚠️ Limitations (When NOT to Use SQLite):

1. **High concurrent writes**
   - Only 1 write at a time
   - Multiple reads OK
   - Not for 1000s of simultaneous users

2. **Network access**
   - File-based = local only
   - Can't connect from remote servers
   - (There are workarounds, but not ideal)

3. **User management**
   - No built-in authentication
   - File permissions only

**For your project? SQLite is PERFECT!**

---

## Your Database Creation Flow

Here's what happened when you ran `python src/db_setup.py`:

```
Step 1: Create 'data' directory
   os.makedirs("data", exist_ok=True)
   ✅ Created: /Users/arul/ws/projects/QueryMate/data/

Step 2: Connect (creates file if missing)
   conn = sqlite3.connect("data/company.db")
   ✅ Created: company.db (0 KB)

Step 3: Create tables
   cursor.execute('CREATE TABLE Departments ...')
   cursor.execute('CREATE TABLE Employees ...')
   cursor.execute('CREATE TABLE Projects ...')
   ✅ Database now has structure (still ~4 KB)

Step 4: Insert data
   cursor.executemany('INSERT INTO Departments VALUES ...')
   cursor.executemany('INSERT INTO Employees VALUES ...')
   cursor.executemany('INSERT INTO Projects VALUES ...')
   ✅ Database now has data

Step 5: Commit changes
   conn.commit()
   ✅ Changes written to disk (final size: 16 KB)

Step 6: Close connection
   conn.close()
   ✅ File closed, ready to use!
```

---

## How Your Agents Query It

When you ask "Show employees in IT":

```python
# In src/agents.py (run_query_agentic function)

# 1. Connect to the database
conn = sqlite3.connect("data/company.db")
cursor = conn.cursor()

# 2. Execute the generated SQL
sql_query = "SELECT * FROM Employees WHERE DeptID = 1"
cursor.execute(sql_query)

# 3. Fetch results
results = cursor.fetchall()
# Returns: [(101, 'Arjun Singh', ...), (103, 'Amit Verma', ...)]

# 4. Get column names
headers = [desc[0] for desc in cursor.description]
# Returns: ['EmpID', 'Name', 'Role', 'Salary', 'JoinDate', 'DeptID']

# 5. Close connection
conn.close()

# 6. Return to UI
return {"data": results, "headers": headers, ...}
```

---

## Fun Facts About SQLite

1. **Most Deployed Database**
   - Billions of copies in active use
   - Every Android phone has ~50 SQLite databases
   - Every iPhone/iPad too
   - Your web browser uses it!

2. **Rock Solid**
   - Powers airplane systems
   - Used in military applications
   - Tested more than any other database

3. **Public Domain**
   - Completely free
   - No license needed
   - Can use anywhere

4. **Small Footprint**
   - Entire library: ~600 KB
   - Your database: 16 KB
   - Can run on a smartwatch!

---

## Practical Exercises

### Exercise 1: Add More Data
```bash
sqlite3 data/company.db

INSERT INTO Employees VALUES (106, 'Your Name', 'AI Engineer', 120000, '2026-02-05', 1);

SELECT * FROM Employees WHERE EmpID = 106;
.exit
```

Now ask QueryMate: "Show the AI Engineer"

### Exercise 2: Explore Relationships
```bash
sqlite3 data/company.db

-- See which department has most employees
SELECT d.DeptName, COUNT(e.EmpID) as EmployeeCount
FROM Departments d
LEFT JOIN Employees e ON d.DeptID = e.DeptID
GROUP BY d.DeptName;
.exit
```

### Exercise 3: Backup Your Database
```bash
# Copy the file
cp data/company.db data/company_backup.db

# Now you have a complete backup!
# Restore anytime by copying back
```

---

## Common SQLite Commands Reference

```sql
-- Show all tables
.tables

-- Show table structure
.schema TableName

-- Show all data
SELECT * FROM TableName;

-- Count rows
SELECT COUNT(*) FROM TableName;

-- Export to CSV
.mode csv
.output employees.csv
SELECT * FROM Employees;
.output stdout

-- See query execution plan
EXPLAIN QUERY PLAN SELECT * FROM Employees WHERE Salary > 80000;

-- Database info
.dbinfo

-- Quit
.exit
```

---

## Key Takeaways

1. **SQLite = Single file database**
   - Located at: `data/company.db`
   - No server needed
   - Perfect for your project

2. **Access methods:**
   - Python code (your agents)
   - SQLite CLI (`sqlite3` command)
   - GUI tools (DB Browser)
   - Your QueryMate app!

3. **Why it's great:**
   - Zero setup
   - Fast for small data
   - Portable
   - Industry standard

4. **When to upgrade:**
   - Need 1000s of concurrent users → PostgreSQL
   - Need remote access → MySQL/PostgreSQL
   - Need advanced features → PostgreSQL

**For learning Text-to-SQL? SQLite is PERFECT! 🎯**

---

## Next Steps

1. **Explore your database:**
   ```bash
   sqlite3 data/company.db
   .schema
   ```

2. **Install DB Browser** (optional):
   - Visual way to see your data
   - Download from sqlitebrowser.org

3. **Experiment:**
   - Add more employees
   - Create new tables
   - Test complex queries

4. **Learn SQL:**
   - Your QueryMate is now a SQL learning tool!
   - Ask questions, see the generated SQL
   - Run them manually to understand

**Your database is just a file - you can't break it! Experiment freely! 🚀**
