# 🚀 Quick Start Guide

## Step 1: Install Dependencies

Run in your terminal:
```bash
pip install -r requirements.txt
```

**What this installs:**
- `langchain` - Framework for LLM applications
- `langchain-groq` - Groq API integration
- `chromadb` - Vector database for RAG
- `sentence-transformers` - Text embedding model
- `streamlit` - Web UI framework
- `python-dotenv` - Environment variable management

---

## Step 2: Setup Database

Create the SQLite database with sample data:
```bash
python src/db_setup.py
```

**What this does:**
- Creates `data/company.db`
- Populates 3 tables: Employees, Departments, Projects
- Inserts sample data (5 employees, 3 departments, 3 projects)

---

## Step 3: Run the Application

```bash
streamlit run app.py
```

**First-time startup will:**
1. Load environment variables from `.env`
2. Initialize Groq LLM connection
3. Create vector embeddings (takes ~5 seconds)
4. Launch web browser at `http://localhost:8501`

---

## 🧪 Testing the System

### Test 1: Basic Query (Happy Path)
```
Question: "Show all employees"
Expected: Lists all 5 employees
Logs: Should show Planner → SQL Coder → Success
```

### Test 2: RAG Verification
```
Question: "What projects are pending?"
Expected: Shows only projects with Status='Pending'
Check Logs: Should retrieve Projects schema (NOT Employees)
```

### Test 3: Self-Correction Loop
```
Question: "Show employees earning more than 70000"
Expected: Returns Arjun, Amit, Vikram
Watch: Logs show planning, SQL generation, execution
```

### Test 4: Complex Query (Tests Planning)
```
Question: "Who manages the IT department?"
Expected: "Rohan Gupta"
Planner Output: "Query Departments table where DeptName='IT', return ManagerName"
```

### Test 5: Intentional Error (Tests Self-Correction)
Modify the database to break something, then watch it auto-fix:
- The system should retry up to 3 times
- Logs will show error detection and correction attempts

---

## 📊 Understanding the UI

### Main Interface
- **Text Input**: Your natural language question
- **Run Analysis Button**: Triggers the agent workflow
- **Sidebar**: Sample questions to try

### Output Sections
1. **Agent Thought Process** (Expandable):
   - Shows all 4 agents' activities
   - Displays planning, SQL generation, errors, retries
   
2. **Generated SQL**:
   - The final SQL query that succeeded
   - Copy this to test manually in SQLite

3. **Results Table**:
   - Data returned from the query
   - Formatted as a pandas DataFrame

---

## 🔍 Debugging Tips

### Problem: "GROQ_API_KEY not found"
**Solution**: Check your `.env` file has no spaces around `=`
```
✅ Correct: GROQ_API_KEY="gsk_..."
❌ Wrong:   GROQ_API_KEY = "gsk_..."
```

### Problem: "ModuleNotFoundError: No module named 'chromadb'"
**Solution**: Reinstall dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Problem: RAG not working (retrieving all schemas)
**Solution**: Delete and recreate vector store
- RAG system initializes on first run
- Check logs for "🔧 Initializing RAG Schema Vectorstore..."

### Problem: SQL always fails
**Solution**: Check database exists
```bash
ls data/company.db  # Should show the file
python src/db_setup.py  # Recreate if needed
```

---

## 📈 Monitoring Agent Behavior

### What to Look For in Logs:

1. **Planning Phase**:
   ```
   📋 PLANNER: To answer this question:
   1. Query the Employees table
   2. Filter by Salary > 70000
   3. Return Name and Salary columns
   ```

2. **Schema Retrieval**:
   ```
   🔍 SCHEMA EXPERT: Retrieved relevant schemas using RAG
   ```
   - If you see all 3 tables every time → RAG isn't working
   - Should be selective (2 tables max for simple queries)

3. **SQL Generation**:
   ```
   💻 SQL CODER Generated:
   SELECT Name, Salary FROM Employees WHERE Salary > 70000;
   ```

4. **Success**:
   ```
   ✅ VALIDATOR: Query executed successfully!
   ```

5. **Error & Retry**:
   ```
   ❌ VALIDATOR ERROR: no such column 'dept'
   🔄 SQL CODER: Attempting to fix the error...
   ```

---

## 🎓 Learning Exercises

### Exercise 1: Modify Few-Shot Examples
1. Open `src/agents.py`
2. Find `few_shot_examples` in `agent_sql_coder()`
3. Add a new example for joins
4. Test if accuracy improves for join queries

### Exercise 2: Change RAG Parameters
1. Open `src/agents.py` 
2. In `run_query_agentic()`, change `top_k=2` to `top_k=1`
3. Observe if it retrieves too little context
4. Try `top_k=3` - does it help or add noise?

### Exercise 3: Adjust LLM Temperature
1. Open `src/llm_engine.py`
2. Change `temperature=0` to `temperature=0.3`
3. Run the same query 3 times
4. Do you get different SQL each time? (You should)
5. Which is better for SQL generation?

### Exercise 4: Add More Data
1. Open `src/db_setup.py`
2. Add 5 more employees with different salaries
3. Test edge cases: "Show the highest paid employee"
4. Does the system handle it correctly?

---

## 🔬 Advanced: Inspecting the Vector Database

Want to see what RAG is actually doing?

```python
# Add this to a test script
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.Client()
embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction()

collection = client.get_collection("table_schemas", embedding_function=embedding_fn)

# Test different questions
questions = [
    "Show me employee salaries",
    "What projects are pending?",
    "Who manages the IT department?"
]

for q in questions:
    results = collection.query(query_texts=[q], n_results=2)
    print(f"\nQuestion: {q}")
    print(f"Retrieved: {results['ids'][0]}")  # Which tables?
```

---

## ✅ Success Criteria

Your system is working correctly if:
1. ✅ RAG initializes without errors
2. ✅ Sample questions return correct data
3. ✅ Logs show all 4 agents working
4. ✅ Planner explains reasoning before SQL generation
5. ✅ Self-correction works (intentionally break something to test)
6. ✅ Schema retrieval is selective (not always all 3 tables)

---

## 🆘 Getting Help

If something doesn't work:
1. Check the terminal output (not just the web UI)
2. Look for error messages in the Streamlit logs
3. Verify `.env` file is correct
4. Ensure all dependencies installed
5. Try recreating the database

---

**Ready to test? Run `streamlit run app.py` and start querying!**
