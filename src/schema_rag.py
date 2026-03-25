"""
RAG Module for Schema Retrieval
================================
This module implements Retrieval-Augmented Generation for intelligent schema retrieval.

CONCEPT: Instead of sending ALL table schemas to the LLM (wasteful and noisy),
we use semantic search to retrieve ONLY the relevant tables based on the user's question.

HOW IT WORKS:
1. We create embeddings (vector representations) of each table's description
2. When a user asks a question, we embed the question
3. We find the most similar table descriptions using cosine similarity
4. We return only those relevant schemas to the LLM

BENEFITS:
- Reduces token usage (cost savings)
- Improves accuracy (less noise/confusion for the LLM)
- Scales better (works with 100+ tables)
"""

import chromadb
from chromadb.utils import embedding_functions

# Initialize ChromaDB (in-memory for simplicity)
# In production, you'd persist this to disk
chroma_client = chromadb.Client()

# Use sentence-transformers for embedding
# This converts text into 384-dimensional vectors
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"  # Fast, lightweight model
)

def initialize_schema_vectorstore():
    """
    Creates a vector database with our table schemas.
    
    Each "document" contains:
    - A description of what the table stores
    - Metadata about the table structure
    
    This runs once at startup.
    """
    
    # Delete existing collection if it exists (fresh start)
    try:
        chroma_client.delete_collection("table_schemas")
    except:
        pass
    
    # Create new collection
    collection = chroma_client.create_collection(
        name="table_schemas",
        embedding_function=embedding_function
    )
    
    # Define our table descriptions (rich context for better matching)
    schema_documents = [
        {
            "id": "employees",
            "description": """
            The Employees table stores all company staff records.
            Columns: EmpID (primary key), Name, Role (job title), Salary (integer),
            JoinDate (YYYY-MM-DD), DeptID (foreign key to Departments),
            ManagerID (self-referencing foreign key to another EmpID — the person they report to),
            Status ('Active', 'On Leave', 'Resigned').
            Use for queries about employees, salaries, roles, join dates, reporting structure,
            active/resigned staff, and who reports to whom.
            """,
            "schema": """
            Employees (
                EmpID      INTEGER PRIMARY KEY,
                Name       TEXT,
                Role       TEXT,
                Salary     INTEGER,
                JoinDate   TEXT,
                DeptID     INTEGER FOREIGN KEY → Departments.DeptID,
                ManagerID  INTEGER FOREIGN KEY → Employees.EmpID (self-join),
                Status     TEXT  ('Active', 'On Leave', 'Resigned')
            )
            """,
            "example_queries": "employee salary roles join date manager reports to active resigned"
        },
        {
            "id": "departments",
            "description": """
            The Departments table stores organizational unit information.
            Columns: DeptID (primary key), DeptName (IT/Sales/HR/Finance/Operations),
            ManagerName, LocationID (foreign key to Locations), Budget (department annual budget).
            Use for queries about departments, department budgets, department managers,
            which department an employee belongs to, and office locations of departments.
            """,
            "schema": """
            Departments (
                DeptID      INTEGER PRIMARY KEY,
                DeptName    TEXT,
                ManagerName TEXT,
                LocationID  INTEGER FOREIGN KEY → Locations.LocationID,
                Budget      INTEGER
            )
            """,
            "example_queries": "department manager budget team organizational unit which department"
        },
        {
            "id": "locations",
            "description": """
            The Locations table stores office location details.
            Columns: LocationID (primary key), City, Country, OfficeType ('HQ', 'Regional', 'Remote Hub').
            Use for queries about office locations, cities, countries, headquarters,
            which city a department is in, and office types.
            """,
            "schema": """
            Locations (
                LocationID  INTEGER PRIMARY KEY,
                City        TEXT,
                Country     TEXT,
                OfficeType  TEXT  ('HQ', 'Regional', 'Remote Hub')
            )
            """,
            "example_queries": "office location city country headquarters regional hub where is"
        },
        {
            "id": "projects",
            "description": """
            The Projects table tracks all company projects.
            Columns: ProjectID (primary key), ProjectName, Budget, Status ('Pending', 'In Progress',
            'Completed', 'On Hold'), StartDate (YYYY-MM-DD), EndDate (YYYY-MM-DD, NULL if ongoing),
            DeptID (foreign key to Departments).
            Use for queries about projects, project budgets, project status, project timelines,
            which department owns a project, ongoing vs completed projects.
            """,
            "schema": """
            Projects (
                ProjectID   INTEGER PRIMARY KEY,
                ProjectName TEXT,
                Budget      INTEGER,
                Status      TEXT  ('Pending', 'In Progress', 'Completed', 'On Hold'),
                StartDate   TEXT,
                EndDate     TEXT  (NULL if ongoing),
                DeptID      INTEGER FOREIGN KEY → Departments.DeptID
            )
            """,
            "example_queries": "project status budget timeline pending completed on hold start end date"
        },
        {
            "id": "employeeprojects",
            "description": """
            The EmployeeProjects table is a junction table linking employees to projects (many-to-many).
            Columns: EmpID (foreign key to Employees), ProjectID (foreign key to Projects),
            Role (the employee's role on that project: 'Lead' or 'Member'), HoursLogged (integer).
            Use for queries about which employees are assigned to which projects, project leads,
            hours worked on projects, and employee project involvement.
            """,
            "schema": """
            EmployeeProjects (
                EmpID       INTEGER FOREIGN KEY → Employees.EmpID,
                ProjectID   INTEGER FOREIGN KEY → Projects.ProjectID,
                Role        TEXT  ('Lead', 'Member'),
                HoursLogged INTEGER,
                PRIMARY KEY (EmpID, ProjectID)
            )
            """,
            "example_queries": "assigned to project working on project lead member hours logged involvement"
        },
        {
            "id": "skills",
            "description": """
            The Skills table is a catalog of all skills tracked in the company.
            Columns: SkillID (primary key), SkillName (e.g. Python, SQL, AWS, Leadership),
            Category ('Technical', 'Soft', 'Domain').
            Use for queries about available skills, skill categories, technical vs soft skills.
            """,
            "schema": """
            Skills (
                SkillID   INTEGER PRIMARY KEY,
                SkillName TEXT,
                Category  TEXT  ('Technical', 'Soft', 'Domain')
            )
            """,
            "example_queries": "skills technical soft domain Python SQL AWS leadership available"
        },
        {
            "id": "employeeskills",
            "description": """
            The EmployeeSkills table links employees to their skills (many-to-many junction table).
            Columns: EmpID (foreign key to Employees), SkillID (foreign key to Skills),
            Proficiency ('Beginner', 'Intermediate', 'Expert').
            Use for queries about employee skill levels, who knows Python/SQL/AWS,
            expert employees in a skill, and skill proficiency across the team.
            """,
            "schema": """
            EmployeeSkills (
                EmpID       INTEGER FOREIGN KEY → Employees.EmpID,
                SkillID     INTEGER FOREIGN KEY → Skills.SkillID,
                Proficiency TEXT  ('Beginner', 'Intermediate', 'Expert'),
                PRIMARY KEY (EmpID, SkillID)
            )
            """,
            "example_queries": "employee skills proficiency expert beginner intermediate knows Python SQL AWS"
        },
    ]
    
    # Add to vector database
    for doc in schema_documents:
        collection.add(
            documents=[doc["description"]],  # This gets embedded
            metadatas=[{
                "schema": doc["schema"],
                "examples": doc["example_queries"]
            }],
            ids=[doc["id"]]
        )
    
    return collection

def retrieve_relevant_schemas(question, top_k=3):
    """
    Performs semantic search to find relevant table schemas.
    
    Args:
        question: User's natural language query
        top_k: Number of most relevant tables to return (default: 2)
    
    Returns:
        A formatted string containing only relevant schemas
    
    EXAMPLE:
        Question: "Show me all employees in IT"
        → Retrieves: Employees + Departments schemas (not Projects)
    """
    
    collection = chroma_client.get_collection(
        name="table_schemas",
        embedding_function=embedding_function
    )
    
    # Perform similarity search
    results = collection.query(
        query_texts=[question],
        n_results=top_k
    )
    
    # Format the results
    schema_context = "Relevant Tables:\n"
    
    for i, metadata in enumerate(results['metadatas'][0]):
        schema_context += f"\n{metadata['schema']}\n"
    
    # Add relationship information
    schema_context += """
    Relationships:
    - Employees.DeptID links to Departments.DeptID
    - Projects.DeptID links to Departments.DeptID
    """
    
    return schema_context
