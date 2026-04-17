import sqlite3
import os
import re
from src.llm_engine import invoke_with_fallback
from src.schema_rag import initialize_schema_vectorstore, retrieve_relevant_schemas

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
    # Use RAG to get only relevant schemas (top_k=3 for 7-table schema)
    return retrieve_relevant_schemas(question, top_k=3)

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
    
    response = invoke_with_fallback(prompt)
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
    -- Only select ManagerName, not SELECT *

    Example 2:
    Question: "Show me employees earning more than 80000"
    SQL: SELECT Name, Salary FROM Employees WHERE Salary > 80000;
    -- Select exactly Name and Salary — NOT EmpID or other columns

    Example 3:
    Question: "List all projects with Pending status"
    SQL: SELECT ProjectName FROM Projects WHERE Status = 'Pending';
    -- Only ProjectName since that is what is asked

    Example 4:
    Question: "How many employees in Sales?"
    SQL: SELECT COUNT(*) AS EmployeeCount FROM Employees WHERE DeptID = (SELECT DeptID FROM Departments WHERE DeptName = 'Sales');

    Example 5:
    Question: "Which employees know Python?"
    SQL: SELECT e.Name FROM Employees e JOIN EmployeeSkills es ON e.EmpID = es.EmpID JOIN Skills s ON es.SkillID = s.SkillID WHERE s.SkillName = 'Python';
    -- Return Name (human-readable), NOT EmpID

    Example 6:
    Question: "Which employees are leading at least one project?"
    SQL: SELECT DISTINCT e.Name FROM Employees e JOIN EmployeeProjects ep ON e.EmpID = ep.EmpID WHERE ep.Role = 'Lead';
    -- Use DISTINCT e.Name only — not SELECT E.*

    Example 7:
    Question: "What is the total hours logged per project?"
    SQL: SELECT p.ProjectName, SUM(ep.HoursLogged) AS TotalHours FROM Projects p JOIN EmployeeProjects ep ON p.ProjectID = ep.ProjectID GROUP BY p.ProjectID, p.ProjectName ORDER BY TotalHours DESC;
    -- Include ProjectName (readable), not ProjectID. Alias must match exactly.

    Example 8:
    Question: "Who are the managers and how many employees report to them?"
    SQL: SELECT m.Name AS Manager, COUNT(e.EmpID) AS DirectReports FROM Employees e JOIN Employees m ON e.ManagerID = m.EmpID GROUP BY m.EmpID, m.Name ORDER BY DirectReports DESC;
    -- Self-join: alias the manager table as m, report table as e

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
        5. Only use column names that exist in the schema above
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
        
        CRITICAL RULES — follow every one:
        1. Return ONLY the raw SQL code — no explanations, no markdown
        2. Prefer explicit column lists. Use SELECT * only when question clearly asks for all fields.
        3. SELECT only the columns that directly answer the question:
           - If asked for names → SELECT Name (not EmpID, not extra columns)
           - If asked for a count → SELECT COUNT(...)
           - If asked for name + salary → SELECT Name, Salary
        4. Use human-readable columns (Name, ProjectName, DeptName) not ID columns
        5. Column aliases must match the question intent (e.g. AS TotalHours not AS TotalHoursLogged)
        6. Only use column names that exist in the schema above — do not invent columns
        7. Do NOT add assumptions or hidden filters not asked in the question
        8. If question asks for both an entity and a metric, return both (e.g., DeptName + TotalSalary)
        """

    response = invoke_with_fallback(prompt)
    
    # Clean up the output (remove markdown if LLM adds it anyway)
    sql = response.content.replace("```sql", "").replace("```", "").strip()
    return sql


def validate_sql_intent(question, sql_query):
    """
    Generic semantic guardrail (non-overfit): catches broad intent mismatches
    before SQL execution and feeds correction hints into retry loop.
    """
    q = question.lower()
    s = sql_query.lower()
    select_clause = s.split("from", 1)[0] if "from" in s else s
    where_clause = s.split("where", 1)[1] if "where" in s else ""

    aggregate_terms = ["how many", "count", "average", "avg", "total", "sum", "maximum", "minimum", "highest", "lowest"]
    asks_aggregate = any(t in q for t in aggregate_terms)
    asks_grouping = ("each" in q) or ("per " in q)
    asks_status = any(t in q for t in ["status", "active", "inactive", "resigned", "pending", "completed", "on hold", "on leave"])

    if asks_aggregate and "select *" in s:
        return "Aggregation question should not use SELECT *. Return aggregate columns only."

    if ("how many" in q or "count" in q) and "count(" not in s:
        return "Count question should use COUNT(...)."

    if ("average" in q or "avg" in q) and "avg(" not in s:
        return "Average question should use AVG(...)."

    if ("total" in q or "sum" in q) and ("sum(" not in s) and ("total number" not in q):
        return "Total question should use SUM(...)."

    if asks_grouping and "group by" not in s:
        return "Per/each question usually needs GROUP BY."

    if "status" in where_clause and not asks_status:
        return "You added status filtering that is not requested by the question."

    asks_entity_names = any(t in q for t in ["name", "names", "who", "which employee", "which department", "which project", "manager"])
    has_name_like = any(t in select_clause for t in ["name", "deptname", "projectname", "skillname", "managername", "role"])
    id_only = any(t in select_clause for t in ["empid", "deptid", "projectid", "skillid"]) and not has_name_like
    if asks_entity_names and id_only:
        return "Return human-readable columns (Name/DeptName/ProjectName) instead of ID-only outputs."

    top_match = re.search(r"top\s+(\d+)", q)
    if top_match and "limit" not in s:
        return "Top-N question should include LIMIT N."

    return None


def validate_result_shape(question, sql_query, rows, headers):
    """
    Post-execution generic validation.
    If SQL executes but likely under-answers/over-answers the question,
    return a correction hint for retry.
    """
    q = question.lower()
    s = sql_query.lower()
    header_text = " ".join([h.lower() for h in headers]) if headers else ""

    if ("how many" in q or "count" in q) and len(rows) != 1 and ("group by" not in s):
        return "Count question should return a single row unless explicitly grouped."

    if ("average" in q or "avg" in q or "maximum" in q or "minimum" in q) and len(rows) != 1 and ("group by" not in s):
        return "Single aggregate question should return one row unless grouped by category."

    if any(t in q for t in ["name", "names", "who", "which employee", "which department", "which project"]):
        if headers and any(h.lower().endswith("id") for h in headers) and not any("name" in h.lower() for h in headers):
            return "Result columns are ID-only; include human-readable name columns."

    top_match = re.search(r"top\s+(\d+)", q)
    if top_match:
        n = int(top_match.group(1))
        if len(rows) > n:
            return f"Top-{n} question returned too many rows; apply LIMIT {n}."

    if " and " in q and headers and len(headers) == 1 and ("count(" not in s):
        return "Question requests multiple aspects; include all requested output fields."

    return None

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

            # SEMANTIC INTENT CHECK (self-correction before execution)
            intent_error = validate_sql_intent(question, sql_query)
            if intent_error:
                logs.append(f"⚠️ INTENT CHECK ERROR: {intent_error}")
                if attempt < MAX_RETRIES - 1:
                    error_context = {"error": intent_error, "bad_sql": sql_query}
                    sql_query = agent_sql_coder(question, schema, error_context=error_context)
                    logs.append("🔄 SQL CODER: Refining query to match question intent...")
                    continue
                logs.append("⚠️ Max retries reached during intent correction; executing best attempt.")
            
            # EXECUTE QUERY
            cursor.execute(sql_query)
            results = cursor.fetchall()
            headers = [desc[0] for desc in cursor.description] if cursor.description else []

            # RESULT-SHAPE CHECK (self-correction after successful execution)
            shape_error = validate_result_shape(question, sql_query, results, headers)
            if shape_error and attempt < MAX_RETRIES - 1:
                logs.append(f"⚠️ RESULT CHECK ERROR: {shape_error}")
                error_context = {"error": shape_error, "bad_sql": sql_query}
                sql_query = agent_sql_coder(question, schema, error_context=error_context)
                logs.append("🔄 SQL CODER: Refining query based on result-shape feedback...")
                continue

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