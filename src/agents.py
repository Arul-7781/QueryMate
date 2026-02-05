import sqlite3
import os
from src.llm_engine import get_llm
from src.schema_rag import initialize_schema_vectorstore, retrieve_relevant_schemas

# Initialize LLM
llm = get_llm()
DB_PATH = os.path.join("data", "company.db")

# Initialize RAG system (runs once at startup)
# This creates embeddings of our table schemas for intelligent retrieval
print("🔧 Initializing RAG Schema Vectorstore...")
initialize_schema_vectorstore()
print("✅ RAG System Ready!")

# ==========================================
# AGENT 1: SCHEMA EXPERT (Context Provider with RAG)
# ==========================================
def agent_schema_expert(question):
    """
    Returns database schema using RAG (Retrieval-Augmented Generation).
    
    IMPROVEMENT FROM BASELINE:
    - OLD: Returned ALL 3 tables regardless of question
    - NEW: Uses semantic search to return only RELEVANT tables
    
    EXAMPLE:
        Question: "Show me employee salaries"
        → Returns: Employees table (not Projects, Departments)
    
    This reduces noise and improves LLM accuracy.
    """
    # Use RAG to get only relevant schemas
    return retrieve_relevant_schemas(question, top_k=2)

# ==========================================
# AGENT 1.5: PLANNER (Reasoning Agent) 🧠
# ==========================================
def agent_planner(question, schema):
    """
    NEW AGENT: Explains the reasoning strategy before generating SQL.
    
    This demonstrates "Chain-of-Thought" reasoning, which:
    - Improves accuracy by making the LLM think step-by-step
    - Provides transparency (users see the thought process)
    - Fulfills "Reasoning" requirement in project guidelines
    
    EXAMPLE OUTPUT:
        "To answer 'Show employees in IT':
         1. Need to find IT department's DeptID from Departments table
         2. Filter Employees where DeptID matches
         3. Use a subquery or JOIN"
    """
    prompt = f"""
    You are a database query planner. Explain step-by-step how to answer this question using SQL.
    
    Question: {question}
    Available Schema: {schema}
    
    Provide a brief plan (2-4 steps) explaining:
    1. Which tables to use
    2. What conditions/filters to apply
    3. Any JOINs or subqueries needed
    
    Keep it concise and technical.
    """
    
    response = llm.invoke(prompt)
    return response.content

# ==========================================
# AGENT 2: SQL CODER (Generator with Few-Shot Learning)
# ==========================================
def agent_sql_coder(question, schema, plan=None, error_context=None):
    """
    Generates SQL using Few-Shot Learning.
    
    IMPROVEMENT FROM BASELINE:
    - Added Few-Shot Examples (teaches LLM by example)
    - Added plan parameter (incorporates reasoning from Planner)
    - Better structured prompts
    
    Few-Shot Learning: Providing example Q&A pairs improves accuracy by 20-40%
    """
    
    # Few-Shot Examples (teach the LLM our patterns)
    few_shot_examples = """
    Example 1:
    Question: "Who is the manager of the IT department?"
    SQL: SELECT ManagerName FROM Departments WHERE DeptName = 'IT';
    
    Example 2:
    Question: "Show me employees earning more than 80000"
    SQL: SELECT Name, Salary FROM Employees WHERE Salary > 80000;
    
    Example 3:
    Question: "List projects with 'Pending' status"
    SQL: SELECT ProjectName, Budget FROM Projects WHERE Status = 'Pending';
    
    Example 4:
    Question: "How many employees in Sales?"
    SQL: SELECT COUNT(*) FROM Employees WHERE DeptID = (SELECT DeptID FROM Departments WHERE DeptName = 'Sales');
    """
    
    if error_context:
        # REPAIR MODE: The 'Validator' sent it back with an error
        prompt = f"""
        You are an expert SQLite Developer fixing a broken query.
        
        Question: {question}
        Schema: {schema}
        
        Previous Query (FAILED): {error_context['bad_sql']}
        Error Message: {error_context['error']}
        
        Learn from these examples:
        {few_shot_examples}
        
        Rules:
        1. Return ONLY the corrected SQL code
        2. Fix the specific error mentioned
        3. Do not use Markdown (```sql)
        4. Do not add explanations
        """
    else:
        # NORMAL MODE: First attempt (includes planning)
        plan_context = f"\nQuery Plan:\n{plan}\n" if plan else ""
        
        prompt = f"""
        You are an expert SQLite Developer. 
        
        Question: {question}
        Schema: {schema}
        {plan_context}
        Learn from these examples:
        {few_shot_examples}
        
        Rules:
        1. Return ONLY the raw SQL code
        2. Do not use Markdown (```sql)
        3. Do not add explanations
        4. Follow the pattern shown in examples
        """

    response = llm.invoke(prompt)
    
    # Clean up the output (remove markdown if LLM adds it anyway)
    sql = response.content.replace("```sql", "").replace("```", "").strip()
    return sql

# ==========================================
# AGENT 3: VALIDATOR (Execution & Self-Correction)
# ==========================================
def run_query_agentic(question):
    """
    Main orchestration function (Enhanced Version).
    
    WORKFLOW (4-Agent Chain):
    1. Schema Expert → Retrieves relevant tables using RAG
    2. Planner → Explains reasoning strategy (NEW!)
    3. SQL Coder → Generates SQL using Few-Shot learning
    4. Validator → Executes and validates
    
    If validation fails, loops back to SQL Coder with error feedback.
    
    IMPROVEMENTS:
    - Added Planner for transparent reasoning
    - Enhanced logging to show all agent interactions
    - Better error messages
    """
    
    # Step 1: Get relevant schema (RAG-powered)
    schema = agent_schema_expert(question)
    
    # Step 2: Create a query plan (NEW - shows reasoning)
    plan = agent_planner(question, schema)
    
    # Step 3: Generate SQL with planning context
    sql_query = agent_sql_coder(question, schema, plan=plan)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    MAX_RETRIES = 3
    logs = []  # Transparency logs shown to user
    
    # Log the planning phase
    logs.append(f"📋 PLANNER: {plan}")
    logs.append(f"🔍 SCHEMA EXPERT: Retrieved relevant schemas using RAG")
    
    for attempt in range(MAX_RETRIES):
        try:
            logs.append(f"\n🚀 Attempt {attempt+1}/{MAX_RETRIES}")
            logs.append(f"💻 SQL CODER Generated:\n{sql_query}")
            
            # EXECUTE QUERY
            cursor.execute(sql_query)
            results = cursor.fetchall()
            headers = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()
            
            logs.append(f"✅ VALIDATOR: Query executed successfully!")
            
            return {
                "status": "success",
                "data": results,
                "headers": headers,
                "sql": sql_query,
                "logs": logs,
                "plan": plan  # Include reasoning in output
            }
            
        except sqlite3.Error as e:
            error_msg = str(e)
            logs.append(f"❌ VALIDATOR ERROR: {error_msg}")
            
            if attempt < MAX_RETRIES - 1:  # Don't retry on last attempt
                # SEND BACK TO AGENT 2 FOR REPAIR (Self-Correction Loop)
                error_context = {"error": error_msg, "bad_sql": sql_query}
                sql_query = agent_sql_coder(question, schema, error_context=error_context)
                logs.append(f"🔄 SQL CODER: Attempting to fix the error...")
            else:
                logs.append(f"⚠️ Max retries reached. Query could not be fixed.")
            
    conn.close()
    return {
        "status": "failed",
        "error": "Could not fix query after 3 attempts.",
        "logs": logs,
        "sql": sql_query  # Return last attempted query
    }