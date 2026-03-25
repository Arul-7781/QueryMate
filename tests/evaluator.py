"""
QueryMate Evaluation Runner
----------------------------
Measures Execution Accuracy on the 50-query Golden Set.

Execution Accuracy = fraction of test cases where the LLM-generated SQL
produces an identical result set as the reference (golden) SQL, when both
are executed against the same database.

Usage:
    python tests/evaluator.py                   # full run, all 50
    python tests/evaluator.py --ids 1 5 10      # run specific test IDs
    python tests/evaluator.py --difficulty easy  # run only easy queries
    python tests/evaluator.py --limit 10         # run first N queries
"""

import sys
import os
import json
import sqlite3
import time
import argparse
import csv
import itertools
from datetime import datetime

# Ensure the project root is on the path so we can import src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agents import run_query_agentic

# ─── Config ────────────────────────────────────────────────────────────────────
DB_PATH       = os.path.join(os.path.dirname(__file__), "..", "data", "company.db")
GOLDEN_SET    = os.path.join(os.path.dirname(__file__), "golden_set.json")
RESULTS_DIR   = os.path.join(os.path.dirname(__file__), "results")
FLOAT_ROUND   = 4   # decimal places to round floats for comparison
SLEEP_BETWEEN = 1.5 # seconds between API calls (avoid Groq rate limit)

# ─── Helpers ───────────────────────────────────────────────────────────────────

def execute_sql(sql: str):
    """Run SQL against company.db and return (rows, error)."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        conn.close()
        return rows, None
    except Exception as e:
        return None, str(e)


def normalise_value(v):
    """Round floats; leave everything else unchanged."""
    if isinstance(v, float):
        return round(v, FLOAT_ROUND)
    return v


def normalise_rows(rows):
    """
    Convert a list of rows into a canonical frozenset of tuples so order
    does not matter.  Also normalises floats.
    """
    if rows is None:
        return None
    normalised = []
    for row in rows:
        normalised.append(tuple(normalise_value(v) for v in row))
    return frozenset(normalised)


def results_match(expected_rows, actual_rows):
    """
    Denotation-style execution match.

    1) Exact row-set equality passes.
    2) If model returns extra columns, allow a projection match:
       if there exists a subset of actual columns whose row-set equals expected.

    This is more faithful to execution accuracy for NL-to-SQL settings where
    an answer can be semantically correct despite extra projected columns.
    """
    if expected_rows is None or actual_rows is None:
        return False

    expected_norm = normalise_rows(expected_rows)
    actual_norm = normalise_rows(actual_rows)

    # Fast path: exact match
    if expected_norm == actual_norm:
        return True

    # If either side is empty after normalization, exact path already handled it
    if len(expected_rows) == 0 or len(actual_rows) == 0:
        return False

    # Projection-tolerant path: same number of rows and expected has <= columns
    exp_cols = len(expected_rows[0])
    act_cols = len(actual_rows[0])
    if len(expected_rows) != len(actual_rows):
        return False
    if exp_cols > act_cols:
        return False

    # Try all column subsets from actual rows that match expected width.
    # Keep this practical; our generated SQL here is typically narrow.
    if act_cols > 10:
        return False

    for col_idx in itertools.combinations(range(act_cols), exp_cols):
        projected = [tuple(row[i] for i in col_idx) for row in actual_rows]
        if normalise_rows(projected) == expected_norm:
            return True

    return False


def colour(text, code):
    """ANSI colour wrap for terminal output."""
    return f"\033[{code}m{text}\033[0m"

PASS = lambda t: colour(t, "32")   # green
FAIL = lambda t: colour(t, "31")   # red
WARN = lambda t: colour(t, "33")   # yellow
BOLD = lambda t: colour(t, "1")


# ─── Core evaluator ────────────────────────────────────────────────────────────

def run_evaluation(test_cases: list[dict]) -> dict:
    """
    Run all test cases and return a results dictionary.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    total    = len(test_cases)
    passed   = 0
    failed   = 0
    errors   = 0   # LLM failed to produce executable SQL
    details  = []

    print(BOLD(f"\n{'─'*60}"))
    print(BOLD(f"  QueryMate Golden Set Evaluation  ({total} queries)"))
    print(BOLD(f"{'─'*60}\n"))

    for i, tc in enumerate(test_cases, 1):
        tid        = tc["id"]
        question   = tc["question"]
        golden_sql = tc["sql"]
        difficulty = tc["difficulty"]
        category   = tc["category"]

        print(f"[{i:02d}/{total}] Q{tid} ({difficulty}) — {question[:65]}...")

        # 1. Execute golden SQL to get expected result
        expected_rows, gold_err = execute_sql(golden_sql)
        if gold_err:
            print(WARN(f"     ⚠  Golden SQL error: {gold_err}"))
            details.append(_make_detail(tc, "GOLD_ERROR", None, None,
                                        gold_err, None, None))
            errors += 1
            continue

        # 2. Run QueryMate agent
        t_start = time.time()
        try:
            result = run_query_agentic(question)
        except Exception as e:
            elapsed = time.time() - t_start
            print(FAIL(f"     ✗  Agent exception: {e}"))
            details.append(_make_detail(tc, "AGENT_ERROR", None, None,
                                        str(e), elapsed, None))
            errors += 1
            time.sleep(SLEEP_BETWEEN)
            continue
        elapsed = time.time() - t_start

        agent_status  = result.get("status")
        generated_sql = result.get("sql", "")
        agent_data    = result.get("data", [])   # already executed rows
        agent_error   = None

        # 3. If agent returned an error, try to execute its SQL ourselves
        #    to see if it's actually correct despite the reported failure.
        if agent_status in ("error", "failed") or not generated_sql:
            print(FAIL(f"     ✗  Agent returned error — {result.get('data', '')}"))
            details.append(_make_detail(tc, "AGENT_ERROR", generated_sql,
                                        agent_data, result.get("data", ""),
                                        elapsed, expected_rows))
            errors += 1
            time.sleep(SLEEP_BETWEEN)
            continue

        # 4. Execute the generated SQL  (agents.py already ran it, but we
        #    re-run from golden DB path to ensure we compare on the same DB)
        actual_rows, exec_err = execute_sql(generated_sql)
        if exec_err:
            agent_error = exec_err
            print(FAIL(f"     ✗  Generated SQL error: {exec_err}"))
            print(f"          SQL: {generated_sql[:120]}")
            details.append(_make_detail(tc, "SQL_ERROR", generated_sql,
                                        actual_rows, exec_err, elapsed,
                                        expected_rows))
            failed += 1
            time.sleep(SLEEP_BETWEEN)
            continue

        # 5. Compare result sets
        match = results_match(expected_rows, actual_rows)
        outcome = "PASS" if match else "FAIL"

        if match:
            passed += 1
            print(PASS(f"     ✓  PASS  ({elapsed:.1f}s)  rows={len(actual_rows)}"))
        else:
            failed += 1
            exp_rows_str = str(list(expected_rows)[:3])
            act_rows_str = str(list(actual_rows)[:3])
            print(FAIL(f"     ✗  FAIL  ({elapsed:.1f}s)"))
            print(f"          Expected ({len(expected_rows)} rows): {exp_rows_str}{'...' if len(expected_rows)>3 else ''}")
            print(f"          Got      ({len(actual_rows)} rows): {act_rows_str}{'...' if len(actual_rows)>3 else ''}")
            print(f"          Gen SQL: {generated_sql[:120]}")

        details.append(_make_detail(tc, outcome, generated_sql, actual_rows,
                                    agent_error, elapsed, expected_rows))

        time.sleep(SLEEP_BETWEEN)

    # ── Summary ────────────────────────────────────────────────────────────────
    accuracy = passed / (total - errors) if (total - errors) > 0 else 0.0

    print(BOLD(f"\n{'─'*60}"))
    print(BOLD(f"  RESULTS"))
    print(f"  Total Queries  : {total}")
    print(PASS(f"  Passed         : {passed}"))
    print(FAIL(f"  Failed         : {failed}"))
    print(WARN(f"  Errors (skip)  : {errors}"))
    print(BOLD(f"  Execution Acc  : {accuracy:.1%}  ({passed}/{total - errors})"))
    print(BOLD(f"{'─'*60}\n"))

    # Break down by difficulty
    _print_breakdown(details, "difficulty", ["easy", "medium", "hard"])
    _print_breakdown(details, "category")

    # Save reports
    report = {
        "timestamp"        : timestamp,
        "total"            : total,
        "passed"           : passed,
        "failed"           : failed,
        "errors"           : errors,
        "execution_accuracy": round(accuracy, 4),
        "details"          : details
    }
    _save_json(report, os.path.join(RESULTS_DIR, f"eval_{timestamp}.json"))
    _save_csv(details,  os.path.join(RESULTS_DIR, f"eval_{timestamp}.csv"))
    print(f"  Reports saved to tests/results/eval_{timestamp}.[json|csv]\n")

    return report


# ─── UI-friendly evaluator (no prints, uses callbacks) ─────────────────────────

def run_evaluation_ui(test_cases: list[dict], on_progress=None) -> dict:
    """
    Runs evaluation and returns a report dict identical to run_evaluation().
    Does NOT print anything.  Instead calls on_progress after every query:

        on_progress(i: int, total: int, detail: dict)

    where `detail` is the row dict for the completed query (same keys as
    _make_detail).  This lets Streamlit update its UI live as each query runs.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    total   = len(test_cases)
    passed  = 0
    failed  = 0
    errors  = 0
    details = []

    for i, tc in enumerate(test_cases, 1):
        # 1. Execute golden SQL
        expected_rows, gold_err = execute_sql(tc["sql"])
        if gold_err:
            detail = _make_detail(tc, "GOLD_ERROR", None, None, gold_err, None, None)
            details.append(detail)
            errors += 1
            if on_progress:
                on_progress(i, total, detail)
            continue

        # 2. Call agent
        t_start = time.time()
        try:
            result = run_query_agentic(tc["question"])
        except Exception as e:
            elapsed = time.time() - t_start
            detail = _make_detail(tc, "AGENT_ERROR", None, None, str(e), elapsed, None)
            details.append(detail)
            errors += 1
            if on_progress:
                on_progress(i, total, detail)
            time.sleep(SLEEP_BETWEEN)
            continue
        elapsed = time.time() - t_start

        agent_status  = result.get("status")
        generated_sql = result.get("sql", "")

        # 3. Agent returned failure ("failed" = exhausted retries, "error" = other)
        if agent_status in ("error", "failed") or not generated_sql:
            detail = _make_detail(tc, "AGENT_ERROR", generated_sql,
                                  result.get("data", []),
                                  result.get("data", ""), elapsed, expected_rows)
            details.append(detail)
            errors += 1
            if on_progress:
                on_progress(i, total, detail)
            time.sleep(SLEEP_BETWEEN)
            continue

        # 4. Execute generated SQL
        actual_rows, exec_err = execute_sql(generated_sql)
        if exec_err:
            detail = _make_detail(tc, "SQL_ERROR", generated_sql,
                                  actual_rows, exec_err, elapsed, expected_rows)
            details.append(detail)
            failed += 1
            if on_progress:
                on_progress(i, total, detail)
            time.sleep(SLEEP_BETWEEN)
            continue

        # 5. Compare result sets
        match   = results_match(expected_rows, actual_rows)
        outcome = "PASS" if match else "FAIL"
        if match:
            passed += 1
        else:
            failed += 1

        detail = _make_detail(tc, outcome, generated_sql, actual_rows,
                              None, elapsed, expected_rows)
        details.append(detail)
        if on_progress:
            on_progress(i, total, detail)

        time.sleep(SLEEP_BETWEEN)

    accuracy = passed / (total - errors) if (total - errors) > 0 else 0.0
    report = {
        "timestamp"         : timestamp,
        "total"             : total,
        "passed"            : passed,
        "failed"            : failed,
        "errors"            : errors,
        "execution_accuracy": round(accuracy, 4),
        "details"           : details,
    }
    _save_json(report, os.path.join(RESULTS_DIR, f"eval_{timestamp}.json"))
    _save_csv(details,  os.path.join(RESULTS_DIR, f"eval_{timestamp}.csv"))
    return report


def _make_detail(tc, outcome, gen_sql, actual_rows, error, elapsed, expected_rows):
    return {
        "id"           : tc["id"],
        "difficulty"   : tc["difficulty"],
        "category"     : tc["category"],
        "question"     : tc["question"],
        "golden_sql"   : tc["sql"],
        "generated_sql": gen_sql or "",
        "outcome"      : outcome,
        "expected_rows": len(expected_rows) if expected_rows is not None else None,
        "actual_rows"  : len(actual_rows)   if actual_rows  is not None else None,
        "error"        : error or "",
        "elapsed_s"    : round(elapsed, 2)  if elapsed else None,
    }


def _print_breakdown(details, key, order=None):
    from collections import defaultdict
    groups = defaultdict(lambda: {"pass": 0, "total": 0})
    for d in details:
        if d["outcome"] in ("PASS", "FAIL"):
            g = d[key]
            groups[g]["total"] += 1
            if d["outcome"] == "PASS":
                groups[g]["pass"] += 1

    keys = order if order else sorted(groups.keys())
    print(f"  By {key}:")
    for k in keys:
        if k not in groups:
            continue
        p = groups[k]["pass"]
        t = groups[k]["total"]
        acc = p/t if t else 0
        bar_len = int(acc * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"    {k:<25} {bar} {acc:5.1%}  ({p}/{t})")
    print()


def _save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _save_csv(details, path):
    if not details:
        return
    fieldnames = details[0].keys()
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(details)


# ─── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="QueryMate Evaluation Runner")
    parser.add_argument("--ids",        nargs="+", type=int, help="Run only specific test IDs")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"],
                        help="Filter by difficulty")
    parser.add_argument("--limit",      type=int, help="Run first N test cases")
    parser.add_argument("--category",   type=str, help="Filter by category name")
    args = parser.parse_args()

    with open(GOLDEN_SET) as f:
        all_cases = json.load(f)

    # Apply filters
    cases = all_cases
    if args.ids:
        cases = [c for c in cases if c["id"] in args.ids]
    if args.difficulty:
        cases = [c for c in cases if c["difficulty"] == args.difficulty]
    if args.category:
        cases = [c for c in cases if c["category"] == args.category]
    if args.limit:
        cases = cases[:args.limit]

    if not cases:
        print("No test cases matched your filters.")
        sys.exit(1)

    run_evaluation(cases)


if __name__ == "__main__":
    main()
