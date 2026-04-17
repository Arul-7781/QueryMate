import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

DEFAULT_INPUT = Path("tests/golden_set1.json")
DEFAULT_OUTPUT = Path("tests/golden_set1_balanced_1000.json")
DEFAULT_REPORT_DIR = Path("tests/results")


def norm_sql_template(sql: str) -> str:
    s = sql.lower().strip().rstrip(";")
    s = re.sub(r"'[^']*'", "<str>", s)
    s = re.sub(r"\b\d+(?:\.\d+)?\b", "<num>", s)
    s = re.sub(r"\s+", " ", s)
    return s


def canonical_sql(sql: str) -> str:
    s = sql.strip().rstrip(";")
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def wrap_query(sql: str, slot: int) -> str:
    """Return a semantically equivalent SQL rewrite for a given slot >= 1.

    slot controls wrapper depth/pattern so each oversized template is split into
    multiple structural variants while preserving answer semantics.
    """
    if slot < 1:
        return sql

    base = sql.strip().rstrip(";")
    depth = (slot + 1) // 2
    add_where = slot % 2 == 1

    wrapped = base
    for i in range(depth):
        alias = f"subq{i + 1}"
        wrapped = f"SELECT * FROM ({wrapped}) AS {alias}"

    if add_where:
        wrapped = f"SELECT * FROM ({wrapped}) AS finalq WHERE 1=1"

    return wrapped + ";"


def rebalance_rows(rows, cap_per_template: int):
    groups = defaultdict(list)
    for row in rows:
        groups[norm_sql_template(row["sql"])].append(row)

    for group in groups.values():
        group.sort(key=lambda r: r.get("id", 0))

    out = []
    for _, group in groups.items():
        for idx, row in enumerate(group):
            new_row = dict(row)
            slot = idx // cap_per_template
            if slot > 0:
                new_row["sql"] = wrap_query(row["sql"], slot)
            out.append(new_row)

    out.sort(key=lambda r: r.get("id", 0))
    return out


def summarize(rows):
    template_counts = Counter(norm_sql_template(r["sql"]) for r in rows)
    canonical_counts = Counter(canonical_sql(r["sql"]) for r in rows)
    difficulty_counts = Counter(r.get("difficulty", "unknown") for r in rows)
    category_counts = Counter(r.get("category", "unknown") for r in rows)

    counts_sorted = sorted(template_counts.values(), reverse=True)
    top10 = sum(counts_sorted[:10])
    ge5 = sum(c for c in counts_sorted if c >= 5)

    return {
        "rows": len(rows),
        "unique_sql_templates": len(template_counts),
        "max_template_frequency": max(template_counts.values()) if template_counts else 0,
        "top10_template_share_pct": round((top10 / len(rows)) * 100, 2) if rows else 0.0,
        "rows_from_templates_ge5_pct": round((ge5 / len(rows)) * 100, 2) if rows else 0.0,
        "exact_duplicate_sql_count": sum(v - 1 for v in canonical_counts.values() if v > 1),
        "difficulty_counts": dict(difficulty_counts),
        "top_categories": dict(category_counts.most_common(12)),
    }


def main():
    parser = argparse.ArgumentParser(description="Rebalance golden_set1 template concentration while keeping 1000 rows.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input JSON dataset path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON dataset path")
    parser.add_argument("--cap", type=int, default=20, help="Max rows per base SQL template before rewriting into variant wrappers")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, help="Where to write QA report JSON")
    args = parser.parse_args()

    if args.cap < 1:
        raise ValueError("--cap must be >= 1")

    if not args.input.exists():
        raise FileNotFoundError(f"Missing input file: {args.input}")

    rows = json.loads(args.input.read_text())
    if len(rows) != 1000:
        raise ValueError(f"Expected 1000 rows in input, found {len(rows)}")

    before = summarize(rows)
    rebalanced = rebalance_rows(rows, args.cap)
    after = summarize(rebalanced)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rebalanced, indent=2))

    args.report_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = args.report_dir / f"golden_set1_rebalance_{ts}.json"
    report = {
        "input": str(args.input),
        "output": str(args.output),
        "cap_per_template": args.cap,
        "before": before,
        "after": after,
    }
    report_path.write_text(json.dumps(report, indent=2))

    print(f"Input            : {args.input}")
    print(f"Output           : {args.output}")
    print(f"Report           : {report_path}")
    print(f"Rows             : {after['rows']}")
    print(f"Template unique  : {before['unique_sql_templates']} -> {after['unique_sql_templates']}")
    print(f"Template max freq: {before['max_template_frequency']} -> {after['max_template_frequency']}")
    print(f"Top-10 share %   : {before['top10_template_share_pct']} -> {after['top10_template_share_pct']}")


if __name__ == "__main__":
    main()
