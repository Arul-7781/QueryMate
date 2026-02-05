# QueryMate 🤖

**An AI-powered system that converts your questions into SQL queries - automatically.**

Ask questions in plain English, get instant database results. No SQL knowledge required.

---

## 🎯 What Does It Do?

QueryMate turns this:
```
"Show me employees earning more than 80000"
```

Into this:
```sql
SELECT Name, Salary FROM Employees WHERE Salary > 80000;
```

And shows you the results - all automatically!

---

## ✨ Key Features

- **🗣️ Natural Language Queries** - Ask questions like you're talking to a person
- **🤖 4-Agent System** - AI agents work together to understand, plan, and execute
- **🔄 Self-Correction** - Automatically fixes SQL errors (up to 3 retries)
- **🧠 RAG-Powered** - Smart retrieval finds only relevant tables
- **📊 Interactive UI** - Clean Streamlit interface
- **🔍 Full Transparency** - See exactly how agents think and work

---

## 🏗️ Architecture

QueryMate uses 4 specialized AI agents:

1. **Schema Expert** - Finds relevant database tables using RAG (vector search)
2. **Planner** - Creates a step-by-step reasoning strategy
3. **SQL Coder** - Generates SQL using few-shot learning
4. **Validator** - Executes query and self-corrects errors

```
Your Question → Schema Expert → Planner → SQL Coder → Validator → Results
                     ↓             ↓          ↓           ↓
                  (RAG)      (Reasoning)  (Few-Shot)  (Execute & Fix)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd QueryMate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key**
   
   Create a `.env` file in the project root:
   ```bash
   GROQ_API_KEY="your_api_key_here"
   ```
   
   ⚠️ **Important:** No spaces around the `=` sign!

4. **Create the database**
   ```bash
   python src/db_setup.py
   ```

5. **Run the app**
   ```bash
   streamlit run app.py
   ```

6. **Open your browser**
   
   Go to `http://localhost:8501`

---

## 💡 How to Use

1. **Type your question** in plain English
   ```
   "Who is the manager of the IT department?"
   "Show employees earning more than 70000"
   "List all pending projects"
   ```

2. **Click "Run Analysis"**

3. **View the results:**
   - Agent thought process (expand to see reasoning)
   - Generated SQL query
   - Query results in a table

---

## 📊 Sample Database

The database contains company information:

- **Employees** (5 employees)
  - ID, Name, Role, Salary, Join Date, Department

- **Departments** (3 departments)
  - ID, Name, Manager

- **Projects** (3 projects)
  - ID, Name, Budget, Status, Department

---

## 🎨 Example Queries

Try these questions:

```
✅ "Show all employees in IT"
✅ "Who is the highest paid employee?"
✅ "List projects with status 'In Progress'"
✅ "How many employees in each department?"
✅ "Show employees who joined after 2023"
✅ "What's the total budget for all projects?"
```

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Llama 3.3 70B (via Groq) |
| **Framework** | LangChain |
| **Database** | SQLite |
| **Vector DB** | ChromaDB |
| **Embeddings** | Sentence Transformers |
| **Frontend** | Streamlit |
| **Language** | Python 3.10+ |

---

## 📁 Project Structure

```
QueryMate/
├── app.py                    # Streamlit UI
├── requirements.txt          # Dependencies
├── .env                      # API keys (create this!)
├── data/
│   └── company.db           # SQLite database
├── src/
│   ├── agents.py            # 4-agent system
│   ├── llm_engine.py        # LLM configuration
│   ├── db_setup.py          # Database creation
│   └── schema_rag.py        # RAG implementation
└── docs/                    # Documentation
```

---

## 🔧 Configuration

### Change the LLM Model

Edit `src/llm_engine.py`:
```python
model="llama-3.3-70b-versatile"  # Current (best balance)
# model="llama-3.1-8b-instant"   # Faster, less accurate
# model="openai/gpt-oss-120b"    # Slower, more accurate
```

### Modify Database

Edit `src/db_setup.py` to add your own tables and data.

### Adjust RAG Settings

In `src/agents.py`, change `top_k` to retrieve more/fewer schemas:
```python
retrieve_relevant_schemas(question, top_k=2)  # Retrieve 2 tables
```

---

## 🧪 How It Works (Technical)

### 1. RAG (Retrieval-Augmented Generation)
- Embeds table schemas as vectors
- Finds relevant tables using cosine similarity
- Reduces noise by only sending relevant context to LLM

### 2. Chain-of-Thought Planning
- Agent creates reasoning plan before generating SQL
- Improves accuracy by 20-40% (research-backed)
- Provides transparency into decision-making

### 3. Few-Shot Learning
- Provides example question-SQL pairs to LLM
- Teaches patterns and conventions
- Reduces hallucination

### 4. Self-Correction Loop
- Catches SQL execution errors
- Feeds error back to SQL Coder
- Retries up to 3 times automatically

---

## 📚 Learn More

- **[Technical Explanation](docs/TECHNICAL_EXPLANATION.md)** - Deep dive into RAG, agents, and concepts
- **[Setup Guide](docs/SETUP_GUIDE.md)** - Detailed setup and testing instructions
- **[Database Guide](docs/DATABASE_GUIDE.md)** - Understanding SQLite and your database
- **[Visual Guide](docs/VISUAL_GUIDE.md)** - Architecture diagrams and data flow
- **[Model Info](docs/MODEL_INFO.md)** - LLM model information and alternatives

---

## 🎓 Educational Value

This project demonstrates:
- ✅ **Multi-agent AI systems**
- ✅ **RAG (Retrieval-Augmented Generation)**
- ✅ **Prompt engineering**
- ✅ **Chain-of-thought reasoning**
- ✅ **Few-shot learning**
- ✅ **Self-correction mechanisms**
- ✅ **Vector databases**
- ✅ **LangChain framework**

---

## 🐛 Troubleshooting

### "GROQ_API_KEY not found"
- Check `.env` file exists in project root
- Ensure no spaces: `GROQ_API_KEY="key"` not `GROQ_API_KEY = "key"`

### "No module named 'chromadb'"
```bash
pip install -r requirements.txt --upgrade
```

### "Database not found"
```bash
python src/db_setup.py
```

### App won't start
```bash
# Check if streamlit is installed
pip install streamlit

# Run from project root
cd /path/to/QueryMate
streamlit run app.py
```

---

## 🤝 Contributing

This is an educational project. Feel free to:
- Add more tables to the database
- Improve agent prompts
- Add new agents
- Enhance the UI
- Test with different LLMs

---

## 📝 License

This project is for educational purposes.

---

## 🙏 Acknowledgments

Built using:
- [LangChain](https://langchain.com) - LLM framework
- [Groq](https://groq.com) - Fast LLM inference
- [Streamlit](https://streamlit.io) - Web UI
- [ChromaDB](https://www.trychroma.com) - Vector database

---

## 📞 Support

For questions or issues:
1. Check the documentation in `/docs`
2. Review the troubleshooting section above
3. Examine the agent logs in the UI

---

**Made with ❤️ for learning AI agent systems**