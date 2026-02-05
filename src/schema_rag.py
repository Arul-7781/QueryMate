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
            The Employees table contains information about company staff members.
            It includes employee ID, full name, job role/title, salary information,
            joining date, and department assignment. Use this table for queries about
            employee details, salaries, roles, hiring dates, and staff information.
            """,
            "schema": """
            Employees (
                EmpID INTEGER PRIMARY KEY,
                Name TEXT,
                Role TEXT,
                Salary INTEGER,
                JoinDate TEXT (format: YYYY-MM-DD),
                DeptID INTEGER FOREIGN KEY
            )
            """,
            "example_queries": "employee salary, staff members, who works in, job roles"
        },
        {
            "id": "departments",
            "description": """
            The Departments table stores organizational department information.
            It contains department ID, department name (like IT, Sales, HR),
            and the manager's name for each department. Use this for queries about
            departments, managers, organizational structure, and team information.
            """,
            "schema": """
            Departments (
                DeptID INTEGER PRIMARY KEY,
                DeptName TEXT,
                ManagerName TEXT
            )
            """,
            "example_queries": "department, manager, organizational unit, which team"
        },
        {
            "id": "projects",
            "description": """
            The Projects table tracks project-related information across the organization.
            It includes project ID, project name, allocated budget, current status
            (Pending, In Progress, Completed), and the department responsible.
            Use this for queries about projects, budgets, project status, and initiatives.
            """,
            "schema": """
            Projects (
                ProjectID INTEGER PRIMARY KEY,
                ProjectName TEXT,
                Budget INTEGER,
                Status TEXT (values: 'Pending', 'In Progress', 'Completed'),
                DeptID INTEGER FOREIGN KEY
            )
            """,
            "example_queries": "project status, budget, initiatives, project information"
        }
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

def retrieve_relevant_schemas(question, top_k=2):
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
