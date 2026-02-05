# 🎨 Visual Guide: How QueryMate Works

## 1. The Complete Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  USER INTERFACE (Streamlit)                                      │
│  "Show me employees in IT department"                            │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR: run_query_agentic()                               │
│  Coordinates all 4 agents and manages workflow                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
        ▼                                         ▼
┌──────────────────┐                    ┌────────────────────────┐
│  VECTOR DB       │                    │  SQLITE DB             │
│  (ChromaDB)      │                    │  company.db            │
│                  │                    │  • Employees           │
│  Table Schemas:  │                    │  • Departments         │
│  [0.23, -0.45,..]│                    │  • Projects            │
│  [0.15,  0.67,..]│                    └────────────────────────┘
│  [0.89, -0.12,..]│                              ▲
└─────────┬────────┘                              │
          │                                       │
          │                          ┌────────────┴────────────┐
          │                          │                         │
    ┌─────▼──────┐              ┌────▼─────┐          ┌───────▼──────┐
    │  AGENT 1   │              │ AGENT 1.5│          │   AGENT 3    │
    │  Schema    │─────────────▶│ Planner  │─────────▶│   Validator  │
    │  Expert    │  schemas     │          │   plan   │              │
    │            │              │          │          │  Executes on │
    │  Uses RAG  │              │ Reasons  │          │  SQLite DB   │
    └────────────┘              └────┬─────┘          └──────┬───────┘
                                     │                       │
                                     ▼                       │
                               ┌────────────┐               │
                               │  AGENT 2   │               │
                               │  SQL Coder │               │
                               │            │               │
                               │ Few-Shot   │◀──────────────┘
                               │ Learning   │   (if error, loop back)
                               └─────┬──────┘
                                     │
                                     ▼
                            ┌────────────────┐
                            │ Generated SQL  │
                            │ SELECT * FROM..|
                            └────────┬───────┘
                                     │
                                     ▼
                            (Back to Validator)
```

---

## 2. Agent Interaction Timeline

```
TIME →
═════════════════════════════════════════════════════════════════

User asks: "Show employees in IT"

t=0s    │ ┌─────────────────────────────────────┐
        │ │ ORCHESTRATOR receives question       │
        │ └─────────────────────────────────────┘
        │
t=0.5s  │ ┌─────────────────────────────────────┐
        │ │ AGENT 1: Schema Expert               │
        │ │ • Embeds question → [0.23, -0.45...] │
        │ │ • Queries ChromaDB                   │
        │ │ • Finds: Employees, Departments      │
        │ │ • Returns schema strings             │
        │ └─────────────────────────────────────┘
        │
t=1.2s  │ ┌─────────────────────────────────────┐
        │ │ AGENT 1.5: Planner                   │
        │ │ • Receives: question + schemas       │
        │ │ • LLM generates reasoning:           │
        │ │   "1. Find IT's DeptID               │
        │ │    2. Filter Employees by DeptID"    │
        │ └─────────────────────────────────────┘
        │
t=2.1s  │ ┌─────────────────────────────────────┐
        │ │ AGENT 2: SQL Coder                   │
        │ │ • Receives: question + schema + plan │
        │ │ • Sees few-shot examples             │
        │ │ • LLM generates SQL:                 │
        │ │   SELECT * FROM Employees            │
        │ │   WHERE DeptID = (...)               │
        │ └─────────────────────────────────────┘
        │
t=2.2s  │ ┌─────────────────────────────────────┐
        │ │ AGENT 3: Validator                   │
        │ │ • Executes SQL on company.db         │
        │ │ • Success! ✅                        │
        │ │ • Returns: [                         │
        │ │     (101, 'Arjun', 'Engineer'...),   │
        │ │     (103, 'Amit', 'DevOps'...)       │
        │ │   ]                                  │
        │ └─────────────────────────────────────┘
        │
t=2.3s  │ ┌─────────────────────────────────────┐
        │ │ ORCHESTRATOR returns to UI           │
        │ │ • Data                               │
        │ │ • SQL                                │
        │ │ • Logs                               │
        │ │ • Plan                               │
        │ └─────────────────────────────────────┘
        │
t=2.4s  │ ┌─────────────────────────────────────┐
        │ │ UI displays results                  │
        │ └─────────────────────────────────────┘
```

---

## 3. Self-Correction Loop (When Error Occurs)

```
┌────────────────────────────────────────────────────────┐
│ First Attempt                                          │
├────────────────────────────────────────────────────────┤
│                                                        │
│  SQL Coder generates:                                  │
│  SELECT * FROM Employees WHERE Department = 'IT'       │
│                                                        │
│         ▼                                              │
│  Validator tries to execute                            │
│         ▼                                              │
│  ❌ ERROR: "no such column: Department"                │
│                                                        │
└────────────────────────┬───────────────────────────────┘
                         │
                         │ SELF-CORRECTION LOOP
                         ▼
┌────────────────────────────────────────────────────────┐
│ Second Attempt                                         │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Validator sends to SQL Coder:                         │
│  {                                                     │
│    "bad_sql": "SELECT * FROM ... Department...",       │
│    "error": "no such column: Department"               │
│  }                                                     │
│                                                        │
│         ▼                                              │
│  SQL Coder (REPAIR MODE):                              │
│  • Sees the error                                      │
│  • Looks at schema again                               │
│  • Realizes: column is DeptID, not Department          │
│  • Generates fixed SQL:                                │
│    SELECT * FROM Employees WHERE DeptID =              │
│    (SELECT DeptID FROM Departments WHERE DeptName='IT')│
│                                                        │
│         ▼                                              │
│  Validator tries again                                 │
│         ▼                                              │
│  ✅ SUCCESS!                                           │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 4. RAG in Action (Vector Similarity Search)

```
Question: "Show employee salaries"
         │
         ▼ (Convert to vector using sentence-transformers)
         
Question Vector: [0.25, -0.43, 0.65, 0.12, ..., -0.89]
                              ▲
                              │ 384 dimensions
                              

                 Vector Database (ChromaDB)
    ┌──────────────────────────────────────────────────┐
    │                                                  │
    │  Employees Schema:                               │
    │  [0.23, -0.45, 0.67, 0.15, ..., -0.91]          │
    │  Similarity Score: 0.89 ← HIGHEST! ✅            │
    │                                                  │
    │  Departments Schema:                             │
    │  [0.15, 0.67, -0.23, 0.45, ..., 0.12]           │
    │  Similarity Score: 0.52                          │
    │                                                  │
    │  Projects Schema:                                │
    │  [0.89, -0.12, 0.34, -0.56, ..., 0.78]          │
    │  Similarity Score: 0.21 ← LOWEST                 │
    │                                                  │
    └──────────────────────────────────────────────────┘
                         │
                         ▼ (Return top_k=2)
                         
    Returns: Employees + Departments schemas
    (Projects schema is not sent to LLM - irrelevant!)
```

**Math Formula**:
$$
\text{similarity}(\vec{q}, \vec{d}) = \frac{\vec{q} \cdot \vec{d}}{|\vec{q}| \cdot |\vec{d}|} = \cos(\theta)
$$

Where:
- $\vec{q}$ = Question vector
- $\vec{d}$ = Document (schema) vector
- Higher score = More relevant

---

## 5. Few-Shot Learning Visualization

```
┌─────────────────────────────────────────────────────────┐
│  ZERO-SHOT (Old Approach)                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Prompt to LLM:                                         │
│  "Generate SQL for: Show employees in IT"               │
│                                                         │
│  LLM Response:                                          │
│  SELECT * FROM Employee WHERE dept = 'IT'               │
│  ❌ Wrong table name! ❌ Wrong column!                  │
│                                                         │
└─────────────────────────────────────────────────────────┘

                        VS

┌─────────────────────────────────────────────────────────┐
│  FEW-SHOT (New Approach)                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Prompt to LLM:                                         │
│                                                         │
│  "Example 1:                                            │
│   Q: Show IT manager                                    │
│   A: SELECT ManagerName FROM Departments                │
│      WHERE DeptName = 'IT'                              │
│                                                         │
│   Example 2:                                            │
│   Q: Employees earning > 80000                          │
│   A: SELECT Name, Salary FROM Employees                 │
│      WHERE Salary > 80000                               │
│                                                         │
│   [2 more examples...]                                  │
│                                                         │
│   Now solve:                                            │
│   Q: Show employees in IT"                              │
│                                                         │
│  LLM Response:                                          │
│  SELECT * FROM Employees WHERE DeptID =                 │
│  (SELECT DeptID FROM Departments WHERE DeptName='IT')   │
│  ✅ Correct! Learned the pattern!                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Logs Output Example

When you run a query, you'll see:

```
┌─────────────────────────────────────────────────────┐
│  Agent Thought Process                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  📋 PLANNER:                                        │
│  To answer "Show employees in IT":                  │
│  1. Query Departments table to find DeptID         │
│     where DeptName = 'IT'                           │
│  2. Use that DeptID to filter Employees table       │
│  3. Return employee records                         │
│                                                     │
│  🔍 SCHEMA EXPERT:                                  │
│  Retrieved relevant schemas using RAG               │
│                                                     │
│  🚀 Attempt 1/3                                     │
│                                                     │
│  💻 SQL CODER Generated:                            │
│  SELECT * FROM Employees                            │
│  WHERE DeptID = (                                   │
│    SELECT DeptID FROM Departments                   │
│    WHERE DeptName = 'IT'                            │
│  )                                                  │
│                                                     │
│  ✅ VALIDATOR:                                      │
│  Query executed successfully!                       │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 7. Technology Stack Visualization

```
┌─────────────────────────────────────────────────────┐
│                  FRONTEND LAYER                     │
│  ┌───────────────────────────────────────────────┐  │
│  │  Streamlit UI (app.py)                        │  │
│  │  • Text input                                 │  │
│  │  • Results display                            │  │
│  │  • Logs viewer                                │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              AGENT ORCHESTRATION LAYER              │
│  ┌───────────────────────────────────────────────┐  │
│  │  src/agents.py                                │  │
│  │  • Agent 1: Schema Expert                     │  │
│  │  • Agent 1.5: Planner                         │  │
│  │  • Agent 2: SQL Coder                         │  │
│  │  • Agent 3: Validator                         │  │
│  │  • Orchestrator: run_query_agentic()          │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌────────────────┐          ┌─────────────────────┐
│  LLM LAYER     │          │   DATA LAYER        │
│ ┌────────────┐ │          │ ┌─────────────────┐ │
│ │ Groq API   │ │          │ │ ChromaDB        │ │
│ │ (Llama 3)  │ │          │ │ (Vectors)       │ │
│ └────────────┘ │          │ └─────────────────┘ │
│                │          │                     │
│ src/           │          │ ┌─────────────────┐ │
│ llm_engine.py  │          │ │ SQLite          │ │
│                │          │ │ (company.db)    │ │
│ • ChatGroq     │          │ └─────────────────┘ │
│ • temp=0       │          │                     │
│ • API key mgmt │          │ src/schema_rag.py   │
│                │          │ src/db_setup.py     │
└────────────────┘          └─────────────────────┘
```

---

## 8. Decision Tree: When Each Agent Activates

```
User submits question
         │
         ▼
    ┌─────────┐
    │ Always  │ → AGENT 1: Schema Expert (RAG)
    └────┬────┘       Retrieves relevant schemas
         │
         ▼
    ┌─────────┐
    │ Always  │ → AGENT 1.5: Planner
    └────┬────┘       Creates reasoning plan
         │
         ▼
    ┌─────────┐
    │ Always  │ → AGENT 2: SQL Coder (First attempt)
    └────┬────┘       Generates SQL
         │
         ▼
    ┌─────────┐
    │ Always  │ → AGENT 3: Validator
    └────┬────┘       Tries to execute
         │
         ├──────────┐
         │          │
    ┌────▼───┐  ┌───▼────┐
    │Success?│  │ Error? │
    └────┬───┘  └───┬────┘
         │          │
         │          ▼
         │     ┌─────────┐
         │     │ Retry   │ → AGENT 2: SQL Coder (Repair mode)
         │     │ < 3?    │       Fixes the SQL
         │     └────┬────┘
         │          │
         │          ▼
         │     Loop back to Validator
         │
         ▼
    Return results to UI
```

---

## Key Takeaways

1. **RAG** = Smart retrieval (only get what you need)
2. **Planner** = Think before acting (improves accuracy)
3. **Few-Shot** = Learn by example (pattern recognition)
4. **Self-Correction** = Learn from mistakes (autonomous debugging)

All working together = **Agentic AI System** 🚀
