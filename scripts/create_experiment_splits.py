import argparse
import json
import math
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_REBALANCED = Path("tests/golden_set1_balanced_1000.json")
DEFAULT_GOLD = Path("tests/golden_set.json")
DEFAULT_OUT_DIR = Path("tests/splits")


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def norm_sql(sql: str) -> str:
    cleaned = sql.strip().rstrip(";")
    return re.sub(r"\s+", " ", cleaned.lower())


def pair_key(row: dict) -> tuple[str, str]:
    return norm_text(row.get("question", "")), norm_sql(row.get("sql", ""))


def stratified_sample(rows: list[dict], n: int, key: str, seed: int) -> list[dict]:
    if n > len(rows):
        raise ValueError(f"Requested {n} rows from a pool of only {len(rows)}")

    grouped = defaultdict(list)
    for row in rows:
        grouped[row.get(key, "unknown")].append(row)

    for bucket in grouped.values():
        bucket.sort(key=lambda x: x.get("id", 0))

    total = len(rows)
    quotas = {}
    remainders = []

    for label, bucket in grouped.items():
        exact = n * len(bucket) / total
        base = math.floor(exact)
        quotas[label] = base
        remainders.append((exact - base, len(bucket), label))

    assigned = sum(quotas.values())
    extra = n - assigned

    remainders.sort(reverse=True)
    idx = 0
    while extra > 0:
        _, _, label = remainders[idx % len(remainders)]
        if quotas[label] < len(grouped[label]):
            quotas[label] += 1
            extra -= 1
        idx += 1

    rng = random.Random(seed)
    sampled = []
    for label, bucket in grouped.items():
        take = quotas[label]
        sampled.extend(rng.sample(bucket, take))

    sampled.sort(key=lambda x: x.get("id", 0))
    return sampled


def check_overlap(a_rows: list[dict], b_rows: list[dict]) -> dict:
    a_pairs = {pair_key(r) for r in a_rows}
    b_pairs = {pair_key(r) for r in b_rows}

    a_q = {norm_text(r.get("question", "")) for r in a_rows}
    b_q = {norm_text(r.get("question", "")) for r in b_rows}

    a_s = {norm_sql(r.get("sql", "")) for r in a_rows}
    b_s = {norm_sql(r.get("sql", "")) for r in b_rows}

    return {
        "pair_overlap": len(a_pairs & b_pairs),
        "question_overlap": len(a_q & b_q),
        "sql_overlap": len(a_s & b_s),
    }


def main():
    parser = argparse.ArgumentParser(description="Create leak-free train/eval splits for QueryMate.")
    parser.add_argument("--rebalanced", type=Path, default=DEFAULT_REBALANCED)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=20260406)
    parser.add_argument("--train-size", type=int, default=850)
    parser.add_argument("--eval-size", type=int, default=50)
    parser.add_argument("--stratify-key", type=str, default="difficulty")
    args = parser.parse_args()

    if not args.rebalanced.exists():
        raise FileNotFoundError(f"Missing rebalanced set: {args.rebalanced}")
    if not args.gold.exists():
        raise FileNotFoundError(f"Missing golden set: {args.gold}")

    rebalanced_rows = json.loads(args.rebalanced.read_text())
    gold_rows = json.loads(args.gold.read_text())

    eval_rows = stratified_sample(gold_rows, args.eval_size, args.stratify_key, args.seed)
    eval_pairs = {pair_key(r) for r in eval_rows}

    candidate_train_pool = [r for r in rebalanced_rows if pair_key(r) not in eval_pairs]
    if len(candidate_train_pool) < args.train_size:
        raise ValueError(
            f"Train pool too small after removing eval overlap: {len(candidate_train_pool)} < {args.train_size}"
        )

    train_rows = stratified_sample(candidate_train_pool, args.train_size, args.stratify_key, args.seed + 1)
    train_ids = {id(r) for r in train_rows}
    holdout_rows = [r for r in candidate_train_pool if id(r) not in train_ids]
    holdout_rows.sort(key=lambda x: x.get("id", 0))

    args.out_dir.mkdir(parents=True, exist_ok=True)

    eval_path = args.out_dir / "eval_50_from_golden_set_stratified.json"
    train_path = args.out_dir / "train_850_from_rebalanced_noeval.json"
    holdout_path = args.out_dir / "holdout_from_rebalanced_noeval.json"
    manifest_path = args.out_dir / "split_manifest_seed_20260406.json"

    eval_path.write_text(json.dumps(eval_rows, indent=2))
    train_path.write_text(json.dumps(train_rows, indent=2))
    holdout_path.write_text(json.dumps(holdout_rows, indent=2))

    overlap = check_overlap(train_rows, eval_rows)
    manifest = {
        "seed": args.seed,
        "stratify_key": args.stratify_key,
        "source_files": {
            "rebalanced": str(args.rebalanced),
            "gold": str(args.gold),
        },
        "sizes": {
            "train": len(train_rows),
            "eval": len(eval_rows),
            "holdout": len(holdout_rows),
        },
        "difficulty_distribution": {
            "train": dict(Counter(r.get("difficulty", "unknown") for r in train_rows)),
            "eval": dict(Counter(r.get("difficulty", "unknown") for r in eval_rows)),
            "holdout": dict(Counter(r.get("difficulty", "unknown") for r in holdout_rows)),
        },
        "overlap_checks": overlap,
    }

    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"Train split : {train_path} ({len(train_rows)})")
    print(f"Eval split  : {eval_path} ({len(eval_rows)})")
    print(f"Holdout     : {holdout_path} ({len(holdout_rows)})")
    print(f"Manifest    : {manifest_path}")
    print(f"Overlap     : {overlap}")


if __name__ == "__main__":
    main()
