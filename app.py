import sys
import os
import json
import csv
import io
import time
import streamlit as st
import pandas as pd
from src.agents import run_query_agentic

# Ensure tests/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))
from evaluator import run_evaluation_ui

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="QueryMate", layout="wide")
st.title("🤖 QueryMate: Agentic SQL Assistant")

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("💡 Try these questions:")
    st.code("Who is the manager of the IT department?")
    st.code("Show me employees earning more than 80000")
    st.code("List all active projects with their budgets")
    st.code("Which employees know both Python and SQL?")
    st.code("Who reports to Amit Verma?")
    st.markdown("---")
    st.caption("QueryMate · Llama 3.3 70B via Groq")

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab_query, tab_eval = st.tabs(["💬 Ask a Question", "📊 Run Evaluation"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Query Interface (original)
# ══════════════════════════════════════════════════════════════════════════════
with tab_query:
    st.markdown("Ask questions about **Employees**, **Departments**, **Projects**, **Skills**, and more.")

    question = st.text_input(
        "Enter your question:",
        placeholder="e.g., How many employees are in each department?",
        key="query_input",
    )

    if st.button("Run Analysis", key="run_query"):
        if question:
            with st.spinner("Agents are collaborating..."):
                result = run_query_agentic(question)

            with st.expander("🔍 Agent Thought Process", expanded=False):
                for log in result["logs"]:
                    st.markdown(log)

            if result["status"] == "success":
                st.success("Query executed successfully!")
                st.code(result["sql"], language="sql")
                if result["data"]:
                    df = pd.DataFrame(result["data"], columns=result["headers"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.warning("Query ran successfully but returned no rows.")
            else:
                st.error(f"Analysis failed: {result.get('data', 'Unknown error')}")
        else:
            st.warning("Please enter a question first.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Evaluation Runner
# ══════════════════════════════════════════════════════════════════════════════
with tab_eval:
    GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "tests", "golden_set.json")

    st.markdown(
        "Run QueryMate against a **curated Golden Set** of 50 questions and measure "
        "**Execution Accuracy** (fraction of queries whose result set exactly matches "
        "the reference SQL output)."
    )

    # Load golden set
    with open(GOLDEN_SET_PATH) as f:
        all_cases = json.load(f)

    # ── Filter Controls ────────────────────────────────────────────────────────
    st.markdown("### Configure Run")
    col_diff, col_limit = st.columns([2, 2])

    with col_diff:
        difficulty_filter = st.selectbox(
            "Filter by difficulty",
            options=["All", "easy", "medium", "hard"],
            key="eval_difficulty",
        )

    with col_limit:
        max_queries = st.slider(
            "Max queries to run",
            min_value=1,
            max_value=len(all_cases),
            value=len(all_cases),
            key="eval_limit",
        )

    # Apply filters
    filtered = all_cases
    if difficulty_filter != "All":
        filtered = [c for c in filtered if c["difficulty"] == difficulty_filter]
    filtered = filtered[:max_queries]

    st.caption(
        f"**{len(filtered)} queries** selected "
        f"({'all difficulties' if difficulty_filter == 'All' else difficulty_filter}). "
        f"Estimated time: ~{len(filtered) * 3 // 60}–{len(filtered) * 5 // 60} min "
        f"(includes API rate-limit delays)."
    )

    st.markdown("---")

    # ── Run Button ─────────────────────────────────────────────────────────────
    if st.button("▶  Run Evaluation", type="primary", key="run_eval"):
        st.markdown("### Live Progress")

        progress_bar     = st.progress(0.0, text="Starting…")
        status_text      = st.empty()
        live_table_ph    = st.empty()

        accumulated: list[dict] = []

        def on_progress(i, total, detail):
            pct     = i / total
            outcome = detail["outcome"]
            icon    = "✅" if outcome == "PASS" else ("⚠️" if "ERROR" in outcome else "❌")
            status_text.markdown(
                f"{icon} `Q{detail['id']:02d}` ({detail['difficulty']}) — "
                f"**{outcome}** — _{detail['question'][:70]}_"
            )
            progress_bar.progress(pct, text=f"Query {i}/{total}")

            # Build a display-friendly row
            accumulated.append({
                "Q"          : detail["id"],
                "Difficulty" : detail["difficulty"],
                "Category"   : detail["category"],
                "Question"   : detail["question"][:60] + ("…" if len(detail["question"]) > 60 else ""),
                "Result"     : outcome,
                "Exp. Rows"  : detail["expected_rows"] if detail["expected_rows"] is not None else "—",
                "Act. Rows"  : detail["actual_rows"]   if detail["actual_rows"]   is not None else "—",
                "Time (s)"   : detail["elapsed_s"]     if detail["elapsed_s"]     is not None else "—",
            })

            df_live = pd.DataFrame(accumulated)
            live_table_ph.dataframe(df_live, use_container_width=True, hide_index=True)

        # ── Actually run ────────────────────────────────────────────────────────
        eval_start = time.time()
        report = run_evaluation_ui(filtered, on_progress=on_progress)
        total_elapsed = time.time() - eval_start

        progress_bar.progress(1.0, text="Complete!")
        status_text.empty()

        # ══ Results ════════════════════════════════════════════════════════════
        st.markdown("---")
        st.markdown("### Results")

        # Top-level metrics
        total_q    = report["total"]
        passed     = report["passed"]
        failed     = report["failed"]
        errors     = report["errors"]
        accuracy   = report["execution_accuracy"]
        evaluated  = total_q - errors

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Execution Accuracy", f"{accuracy:.1%}")
        m2.metric("Passed ✅",           passed)
        m3.metric("Failed ❌",           failed)
        m4.metric("Errors ⚠️",          errors)
        m5.metric("Total Time",          f"{total_elapsed/60:.1f} min")

        # ── Breakdown by difficulty ─────────────────────────────────────────────
        st.markdown("#### Accuracy by Difficulty")
        details = report["details"]

        def breakdown(key, order=None):
            from collections import defaultdict
            groups = defaultdict(lambda: {"pass": 0, "total": 0})
            for d in details:
                if d["outcome"] in ("PASS", "FAIL"):
                    groups[d[key]]["total"] += 1
                    if d["outcome"] == "PASS":
                        groups[d[key]]["pass"] += 1
            keys = order if order else sorted(groups.keys())
            rows = []
            for k in keys:
                if k not in groups:
                    continue
                p = groups[k]["pass"]
                t = groups[k]["total"]
                rows.append({key.capitalize(): k, "Passed": p, "Total": t,
                              "Accuracy": round(p / t, 4) if t else 0})
            return pd.DataFrame(rows)

        diff_df = breakdown("difficulty", ["easy", "medium", "hard"])
        cat_df  = breakdown("category")

        col_d, col_c = st.columns(2)
        with col_d:
            if not diff_df.empty:
                st.dataframe(
                    diff_df.style.format({"Accuracy": "{:.1%}"}),
                    use_container_width=True, hide_index=True,
                )
                st.bar_chart(diff_df.set_index("Difficulty")["Accuracy"])

        with col_c:
            st.markdown("#### Accuracy by Category")
            if not cat_df.empty:
                st.dataframe(
                    cat_df.sort_values("Accuracy", ascending=False)
                          .style.format({"Accuracy": "{:.1%}"}),
                    use_container_width=True, hide_index=True,
                )

        # ── Full Results Table ──────────────────────────────────────────────────
        st.markdown("#### All Query Results")

        outcome_filter = st.selectbox(
            "Filter by outcome",
            options=["All", "PASS", "FAIL", "AGENT_ERROR", "SQL_ERROR", "GOLD_ERROR"],
            key="outcome_filter",
        )

        full_rows = []
        for d in details:
            full_rows.append({
                "Q"            : d["id"],
                "Difficulty"   : d["difficulty"],
                "Category"     : d["category"],
                "Question"     : d["question"],
                "Outcome"      : d["outcome"],
                "Exp. Rows"    : d["expected_rows"] if d["expected_rows"] is not None else "—",
                "Act. Rows"    : d["actual_rows"]   if d["actual_rows"]   is not None else "—",
                "Time (s)"     : d["elapsed_s"]     if d["elapsed_s"]     is not None else "—",
                "Generated SQL": d["generated_sql"],
                "Error"        : d["error"],
            })

        full_df = pd.DataFrame(full_rows)
        if outcome_filter != "All":
            full_df = full_df[full_df["Outcome"] == outcome_filter]

        st.dataframe(full_df, use_container_width=True, hide_index=True)

        # ── Download ────────────────────────────────────────────────────────────
        csv_buf = io.StringIO()
        full_df.to_csv(csv_buf, index=False)
        st.download_button(
            label="⬇   Download Results CSV",
            data=csv_buf.getvalue(),
            file_name=f"eval_{report['timestamp']}.csv",
            mime="text/csv",
        )

        st.caption(
            f"Results also saved to `tests/results/eval_{report['timestamp']}.[json|csv]`"
        )
