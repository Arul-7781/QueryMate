# QueryMate: Technical Deep Dive 🎓

## What Changed and Why

### Overview of Modifications

I've enhanced your baseline QueryMate system with **3 critical improvements** that make it more aligned with industry standards and project guidelines:

1. **RAG (Retrieval-Augmented Generation)** for intelligent schema retrieval
2. **Planner Agent** for transparent reasoning
3. **Few-Shot Learning** for improved accuracy

---

## 🔍 MODIFICATION 1: RAG Implementation

### File: `src/schema_rag.py` (NEW)

**What is RAG?**
RAG = Retrieval-Augmented Generation. Instead of giving the LLM ALL information upfront, we:
1. Convert information into vectors (numbers)
2. Store them in a database
3. Retrieve only RELEVANT pieces based on the query

**Real-World Analogy:**
- **Without RAG**: Giving someone an entire encyclopedia to answer "What's the capital of France?"
- **With RAG**: Looking up just the "France" page and giving them that

### How It Works in Your Code:

```python
# Step 1: Create vector embeddings of table descriptions
schema_documents = [
    {
        "id": "employees",
        "description": "The Employees table contains staff information...",
        "schema": "Employees (EmpID, Name, Role...)"
    },
    # ... more tables
]

# Step 2: Use sentence-transformers to convert text → vectors
embedding_function = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"  # Converts text to 384-dimensional vectors
)

# Step 3: Store in ChromaDB (vector database)
collection.add(documents=[...], embeddings=[...])

# Step 4: At query time, find similar schemas
results = collection.query(query_texts=[question], n_results=2)
```

### The Math Behind It:

When you ask "Show me employee salaries":
1. Your question becomes a vector: `[0.23, -0.45, 0.67, ...]` (384 numbers)
2. Each table description is also a vector
3. ChromaDB calculates **cosine similarity** (how similar vectors are)
4. Returns the 2 most similar tables

**Formula**: 
$$\text{similarity}(A, B) = \frac{A \cdot B}{\|A\| \|B\|} = \cos(\theta)$$

Where values closer to 1 = more similar.

### Benefits:
- ✅ **Reduces tokens**: Only send relevant schemas (saves money)
- ✅ **Improves accuracy**: Less noise confuses the LLM less
- ✅ **Scales**: Works with 100+ tables (your current 3 tables is just a demo)

---

## 🧠 MODIFICATION 2: Planner Agent (Reasoning)

### File: `src/agents.py` - New Function `agent_planner()`

**What is Chain-of-Thought Reasoning?**
Research shows LLMs perform 20-30% better when they "think out loud" before answering.

**Example Without Planner:**
```
Question: "Show employees in IT"
LLM: [generates SQL directly]
```

**Example With Planner:**
```
Question: "Show employees in IT"
Planner: "To solve this:
  1. Find IT department's DeptID from Departments table
  2. Filter Employees where DeptID matches
  3. Use a JOIN or subquery"
SQL Coder: [generates SQL using this plan]
```

### The Code:

```python
def agent_planner(question, schema):
    prompt = f"""
    Explain step-by-step how to answer this question using SQL.
    
    Question: {question}
    Schema: {schema}
    
    Provide a brief plan (2-4 steps)...
    """
    
    response = llm.invoke(prompt)
    return response.content
```

### Why This Matters:
1. **Transparency**: Users see HOW the system thinks
2. **Accuracy**: LLM makes fewer mistakes when it plans first
3. **Debugging**: If SQL is wrong, you can see where the reasoning failed
4. **Guidelines**: Fulfills the "Reasoning" requirement explicitly

---

## 📚 MODIFICATION 3: Few-Shot Learning

### File: `src/agents.py` - Enhanced `agent_sql_coder()`

**What is Few-Shot Learning?**
Teaching by example. Instead of just saying "Generate SQL", we show:
- Example Question 1 → Example SQL 1
- Example Question 2 → Example SQL 2
- Now solve: Your Question → ?

### The Implementation:

```python
few_shot_examples = """
Example 1:
Question: "Who is the manager of the IT department?"
SQL: SELECT ManagerName FROM Departments WHERE DeptName = 'IT';

Example 2:
Question: "Show me employees earning more than 80000"
SQL: SELECT Name, Salary FROM Employees WHERE Salary > 80000;
...
"""

prompt = f"""
{few_shot_examples}

Now answer:
Question: {question}
Schema: {schema}
"""
```

### Why This Works:

**Learning Theory**: Humans learn patterns from examples. LLMs do too.

**Research**: Studies show Few-Shot learning improves accuracy by:
- 20-40% for structured tasks (like SQL)
- Especially effective for domain-specific patterns

**Your Benefit**: 
- LLM learns YOUR database's naming conventions
- Learns YOUR preferred SQL style (joins vs subqueries)
- Reduces hallucination (making up column names)

---

## 🔄 The Complete Workflow (New vs Old)

### OLD Workflow (Baseline):
```
User Question
    ↓
Schema Expert (returns ALL schemas)
    ↓
SQL Coder (generates SQL)
    ↓
Validator (executes)
    ↓
Error? → Loop back to SQL Coder
```

### NEW Workflow (Enhanced):
```
User Question
    ↓
1. Schema Expert (RAG: returns RELEVANT schemas only)
    ↓
2. Planner (creates reasoning strategy)
    ↓
3. SQL Coder (uses plan + few-shot examples)
    ↓
4. Validator (executes)
    ↓
Error? → Loop back with error context
```

---

## 📊 Updated Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│                  USER QUESTION                  │
│            "Show employees in IT"               │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  AGENT 1: Schema Expert (RAG-Powered)          │
│  • Embeds question → vector                     │
│  • Searches ChromaDB for similar schemas       │
│  • Returns: Employees + Departments schemas    │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  AGENT 1.5: Planner (NEW!)                     │
│  Output: "1. Find IT's DeptID                   │
│           2. Filter Employees by DeptID"       │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  AGENT 2: SQL Coder (Few-Shot Enhanced)        │
│  Input: Question + Schema + Plan + Examples    │
│  Output: SELECT * FROM Employees WHERE...      │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│  AGENT 3: Validator                             │
│  • Executes SQL on SQLite                       │
│  • Returns data OR error                        │
│  • If error → loops back to Agent 2            │
└─────────────────────────────────────────────────┘
```

---

## 🎯 How This Fulfills Project Guidelines

| Requirement | Implementation | Evidence |
|------------|----------------|----------|
| **LLM Usage** | ✅ Llama 3 70B via Groq | `src/llm_engine.py` |
| **Reasoning** | ✅ Planner Agent shows step-by-step thinking | `agent_planner()` function |
| **Real-World Applicability** | ✅ Text-to-SQL used in Tableau, Metabase, enterprise BI | Industry standard |
| **Prompt Engineering** | ✅ Structured prompts, few-shot, temperature=0 | All agent prompts |
| **RAG** | ✅ ChromaDB vector store for schema retrieval | `src/schema_rag.py` |
| **Agentic Workflow** | ✅ 4 agents with clear orchestration | `run_query_agentic()` |
| **Model Adaptation** | ⚠️ Not required (optional). Few-shot is a lightweight alternative | Could add fine-tuning later |

**Result**: ✅ **All Required Criteria Met**

---

## 🔬 Key Concepts You Should Understand

### 1. **Vector Embeddings**
- Text → Numbers conversion
- Similar meanings → Similar vectors
- Enables semantic search (search by meaning, not keywords)

### 2. **Cosine Similarity**
- Measures angle between vectors
- Range: -1 (opposite) to +1 (identical)
- Used in RAG to find relevant documents

### 3. **Temperature in LLMs**
- Temperature = 0: Deterministic (same input → same output)
- Temperature = 1: Creative/Random
- SQL needs temperature=0 for consistency

### 4. **Few-Shot vs Zero-Shot**
- Zero-Shot: "Generate SQL" (no examples)
- Few-Shot: "Here are 3 examples, now do this" (better)
- One-Shot: Just 1 example
- Your code uses ~4 examples (optimal for most tasks)

### 5. **Self-Correction Loop**
- System catches its own errors
- Feeds error back as input
- Tries to fix itself (up to 3 times)
- Mimics human debugging process

---

## 🧪 Testing Your System

### Test Case 1: Basic Query
```
Input: "Show all employees"
Expected Flow:
  1. Schema Expert: Retrieves Employees schema
  2. Planner: "Select all rows from Employees table"
  3. SQL Coder: "SELECT * FROM Employees"
  4. Validator: Executes successfully
```

### Test Case 2: Self-Correction
```
Input: "Show employees in IT department"
Attempt 1: SELECT * FROM Employees WHERE Department = 'IT'
           ❌ Error: "no such column Department"
Attempt 2: SELECT * FROM Employees WHERE DeptID = (SELECT DeptID FROM Departments WHERE DeptName = 'IT')
           ✅ Success!
```

### Test Case 3: RAG Verification
```
Input: "What's the budget for pending projects?"
Schema Expert: Should retrieve Projects + Departments (NOT Employees)
This proves RAG is working (selective retrieval)
```

---

## 🚀 Next Steps for Learning

1. **Run the system** and observe the logs
2. **Examine the vector database**: See what gets retrieved for different questions
3. **Modify few-shot examples**: Add your own and see accuracy change
4. **Break it intentionally**: Ask impossible questions to test error handling

---

## 💡 Advanced Extensions (Future Work)

1. **Add SQL Explanation Agent**: Explains generated SQL in plain English
2. **User Feedback Loop**: Learn from corrections (online learning)
3. **Multi-Database Support**: PostgreSQL, MySQL, etc.
4. **Fine-Tuning**: Collect 200+ question-SQL pairs, fine-tune Llama 3
5. **Caching**: Store successful queries to avoid re-generation

---

## 📚 Further Reading

- **RAG**: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020)
- **Chain-of-Thought**: "Chain-of-Thought Prompting Elicits Reasoning in LLMs" (Wei et al., 2022)
- **Few-Shot Learning**: "Language Models are Few-Shot Learners" (Brown et al., 2020)
- **Vector Databases**: ChromaDB Documentation
- **LangChain**: Official docs for agent patterns

---

**Remember**: The best way to learn is to break things and fix them. Try modifying prompts, changing parameters, and observing the results!
