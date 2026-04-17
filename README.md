# QueryMate

Submission-ready repository for the PES University AI project on resource-constrained text-to-SQL.

## College Submission Note

- Repository URL / Drive URL: https://github.com/Arul-7781/QueryMate.git
- If this repository is private, add reviewer access for GitHub user: gsrinivasa-pes
- Main branch status: this README is prepared for final submission after merging validated work into main

## Important Evaluation Note

The primary reproduction path for this submission is the notebook workflow in [notebooks/](notebooks/).

Project evolution summary:
1. Initial phase used the Streamlit app with API-based inference.
2. We then pivoted to Colab notebook runs to execute models locally on GPU runtimes and perform adapter fine-tuning.
3. The final reported experimental workflow and results are notebook-driven.

## Project Overview

QueryMate is a multi-agent text-to-SQL system that converts natural language questions into executable SQL.

Core pipeline:
1. Schema Expert (RAG-based schema retrieval)
2. Planner (reasoning steps)
3. SQL Coder (few-shot SQL generation)
4. Validator (execution + automatic correction loop)

## Repository Organization (Data + Code)

Top-level layout:

```
QueryMate/
├── app.py
├── requirements.txt
├── data/
├── src/
├── tests/
├── scripts/
├── notebooks/
├── spider_data/
├── figures/
└── docs/
```

What each folder contains:

- src/: Core implementation
  - [src/agents.py](src/agents.py): multi-agent orchestration, planning, SQL generation, validation
  - [src/schema_rag.py](src/schema_rag.py): schema retrieval with ChromaDB + sentence-transformers
  - [src/llm_engine.py](src/llm_engine.py): Groq client config, model priority and failover
  - [src/db_setup.py](src/db_setup.py): local sample database setup
- data/: runtime database files (for demo/evaluation), including company SQLite database
- tests/: evaluation assets and outputs
  - [tests/evaluator.py](tests/evaluator.py): execution-accuracy evaluator
  - [tests/golden_set.json](tests/golden_set.json): golden query set
  - [tests/results/](tests/results/): generated JSON/CSV reports
  - [tests/splits/](tests/splits/): generated experiment splits
- scripts/: dataset and figure utilities
  - [scripts/create_experiment_splits.py](scripts/create_experiment_splits.py)
  - [scripts/generate_paper_figures.py](scripts/generate_paper_figures.py)
- notebooks/: Colab notebooks for baseline and adapter experiments
- spider_data/: Spider benchmark files and SQLite databases used in experiments
- figures/: generated experiment plots
- docs/: setup, model details, visual guide, and technical explanation

## Environment Setup

Prerequisites:
- Python 3.10+
- Groq API key

Steps:

1. Clone repository

```bash
git clone <your-repository-url>
cd QueryMate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Create .env in project root

```bash
GROQ_API_KEY="your_groq_key"
```

Optional model config in .env:

```bash
GROQ_MODEL="llama-3.3-70b-versatile"
GROQ_MODELS="llama-3.3-70b-versatile,llama-3.1-8b-instant"
```

4. Initialize local company database

```bash
python src/db_setup.py
```

## Reproducing Results

### A) Primary path (required): run the notebooks

Open and run notebooks in [notebooks/](notebooks/) with GPU runtime (T4 on free tier where available):
- company_adapter_colab.ipynb
- qwen25coder3b_colab_baseline_vs_qlora.ipynb
- spider_adapter_colab_best.ipynb
- dual_adapter_company_spider_colab.ipynb

This is the recommended path for reproducing the submitted experiments.

### B) Optional legacy demo path: run the Streamlit app (API-first phase)

```bash
streamlit run app.py
```

Open http://localhost:8501

### C) Reproduce execution-accuracy evaluation (company golden set)

Run full set:

```bash
python tests/evaluator.py
```

Useful options:

```bash
python tests/evaluator.py --difficulty easy
python tests/evaluator.py --limit 10
python tests/evaluator.py --ids 1 5 10
python tests/evaluator.py --golden-set tests/splits/eval_50_from_golden_set_stratified.json
```

Outputs are saved in [tests/results/](tests/results/).

### D) Reproduce experiment split creation

```bash
python scripts/create_experiment_splits.py
```

This generates split artifacts in [tests/splits/](tests/splits/), including:
- eval_50_from_golden_set_stratified.json
- train_850_from_rebalanced_noeval.json
- holdout_from_rebalanced_noeval.json

### E) Generate analysis figures

```bash
python scripts/generate_paper_figures.py
```

Generated files are written to [figures/](figures/).

Note: notebook outputs depend on runtime availability and API limits; evaluation and figure scripts above provide repository-side reproducibility for reported outputs.

## Additional Documentation

- [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)
- [docs/TECHNICAL_EXPLANATION.md](docs/TECHNICAL_EXPLANATION.md)
- [docs/MODEL_INFO.md](docs/MODEL_INFO.md)
- [docs/DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md)
- [docs/VISUAL_GUIDE.md](docs/VISUAL_GUIDE.md)

## Quick Troubleshooting

- Missing API key error:
  - Ensure .env exists in repo root with GROQ_API_KEY.
- Missing dependencies:

```bash
pip install -r requirements.txt --upgrade
```

- Database not found:

```bash
python src/db_setup.py
```

## License

Educational / academic submission repository.