#!/usr/bin/env python3
"""Aggregate Qwen-vs-rater disagreement without exporting item or rater rows.

Input: public AI-Taste reproducibility package (management_deep_probe).
Output: one aggregate CSV, grouped by benchmark tier and human panel.

This is an exploratory descriptive diagnostic. It does not test causal claims,
and it does not establish latent idea quality: the tier label is a journal-tier
proxy. No titles, article IDs, or pseudonymous rater identifiers are written.
"""
from __future__ import annotations

import argparse
import hashlib
import csv
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

CANONICAL = ("exceptional", "strong", "fair", "limited")
HUMAN_MAP = {
    "Top": "exceptional", "top": "exceptional",
    "Top-": "strong", "top-": "strong",
    "Good": "fair", "good": "fair",
    "Fair": "limited", "fair": "limited",
}
MODEL_KEY = "qwen3-4b-ob"  # Management's best single SFT in the manuscript.


def read_jsonl(path: Path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def entropy_share(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total == 0:
        return float("nan")
    h = -sum((n / total) * math.log(n / total) for n in counts.values() if n)
    return h / math.log(4)


def mode_and_tie(counts: Counter[str]):
    if not counts:
        return None, False
    top = max(counts.values())
    winners = [label for label, count in counts.items() if count == top]
    return (winners[0] if len(winners) == 1 else None), len(winners) > 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", type=Path, required=True,
                    help="Path to cloned public FutureTech-OB/ai-taste repository")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    base = args.package / "data/management_deep_probe"
    benchmark = read_jsonl(base / "benchmark/management_benchmark_120.jsonl")
    preds = read_jsonl(base / "predictions/sft_predictions.jsonl")
    panels = {
        "experts": read_jsonl(base / "human_ratings/expert_ratings_deidentified.jsonl"),
        "juniors": read_jsonl(base / "human_ratings/student_ratings_deidentified.jsonl"),
    }
    # Join on title in memory only. No row-level key is written to the output.
    benchmark_titles = [r["title"] for r in benchmark]
    prediction_titles = [r["title"] for r in preds]
    if len(set(benchmark_titles)) != len(benchmark_titles):
        raise ValueError("Duplicate benchmark titles")
    if len(set(prediction_titles)) != len(prediction_titles):
        raise ValueError("Duplicate prediction titles")
    pred_by_title = {r["title"]: r for r in preds}
    for panel, rows in panels.items():
        titles = [r["title"] for r in rows]
        if len(set(titles)) != len(titles):
            raise ValueError(f"Duplicate {panel} article titles")
        valid_rating_count = sum(
            1 for row in rows for rating in row.get("ratings", [])
            if rating.get("q2_rating") in HUMAN_MAP
        )
        expected = 384 if panel == "experts" else 2530
        if valid_rating_count != expected:
            raise ValueError(f"Expected {expected} valid {panel} ratings; found {valid_rating_count}")
    panel_by_title = {
        name: {r["title"]: r for r in rows} for name, rows in panels.items()
    }
    if len(benchmark) != 120 or set(pred_by_title) != {r["title"] for r in benchmark}:
        raise ValueError("Unexpected benchmark/prediction coverage; inspect package version")
    if any(set(panel_by_title[p]) != {r["title"] for r in benchmark} for p in panels):
        raise ValueError("Unexpected panel/benchmark coverage; inspect package version")
    tier_counts = Counter(HUMAN_MAP.get(r.get("level", r.get("rank")), r.get("level", r.get("rank"))) for r in benchmark)
    if tier_counts != Counter({label: 30 for label in CANONICAL}):
        raise ValueError(f"Expected 30 benchmark items per tier; found {dict(tier_counts)}")

    items = []
    for b in benchmark:
        title = b["title"]
        raw_gold = b.get("level", b.get("rank"))
        gold = HUMAN_MAP.get(raw_gold, raw_gold)
        outcome = pred_by_title[title]["val_outcome"]["rq_with_context"][MODEL_KEY]
        logp = outcome["logp"]
        if not isinstance(logp, dict) or not logp:
            raise ValueError("Missing Qwen log-probability scores")
        valid_scores = [v for v in logp.values() if isinstance(v, (int, float)) and math.isfinite(v)]
        if not valid_scores:
            raise ValueError("Qwen scores contain no finite values")
        # The released Qwen scores are over the restricted output vocabulary;
        # absent labels are treated as unavailable/-infinity for argmax.
        qwen = max(CANONICAL, key=lambda label: logp.get(label, -math.inf))
        panel_counts = {}
        for panel, records in panel_by_title.items():
            counts: Counter[str] = Counter()
            # Deliberately read only ratings; rater_id and all other attributes
            # are ignored and are never serialized.
            for rating in records[title].get("ratings", []):
                label = HUMAN_MAP.get(rating.get("q2_rating"))
                if label:
                    counts[label] += 1
            modal, tied = mode_and_tie(counts)
            panel_counts[panel] = (counts, modal, tied)
        items.append((gold, qwen, panel_counts))

    out_rows = []
    for gold in CANONICAL:
        tier_items = [(g, q, ps) for g, q, ps in items if g == gold]
        for panel in ("experts", "juniors"):
            n_ratings = 0
            model_rating_agreement, human_modal_agreement = [], []
            human_gold_share, human_entropy = [], []
            modal_coverage = 0
            model_accuracy = 0
            for _, qwen, panels_for_item in tier_items:
                counts, modal, tied = panels_for_item[panel]
                total = sum(counts.values())
                if not total:
                    continue
                n_ratings += total
                model_rating_agreement.append(counts[qwen] / total)
                human_gold_share.append(counts[gold] / total)
                human_entropy.append(entropy_share(counts))
                model_accuracy += (qwen == gold)
                if not tied:
                    modal_coverage += 1
                    human_modal_agreement.append(qwen == modal)
            n = len(tier_items)
            out_rows.append({
                "benchmark_tier": gold,
                "human_panel": panel,
                "n_items": n,
                "n_ratings_aggregated": n_ratings,
                "qwen_accuracy_vs_journal_tier_pct": round(100 * model_accuracy / n, 1) if n else "",
                "mean_share_panel_ratings_matching_qwen_pct": round(100 * sum(model_rating_agreement) / len(model_rating_agreement), 1) if model_rating_agreement else "",
                "mean_share_panel_ratings_matching_journal_tier_pct": round(100 * sum(human_gold_share) / len(human_gold_share), 1) if human_gold_share else "",
                "human_modal_items_without_tie": modal_coverage,
                "qwen_matches_human_modal_pct_among_untied_items": round(100 * sum(human_modal_agreement) / len(human_modal_agreement), 1) if human_modal_agreement else "",
                "mean_within_item_human_rating_entropy_0_1": round(sum(human_entropy) / len(human_entropy), 3) if human_entropy else "",
            })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)
    source_files = [
        base / "benchmark/management_benchmark_120.jsonl",
        base / "predictions/sft_predictions.jsonl",
        base / "human_ratings/expert_ratings_deidentified.jsonl",
        base / "human_ratings/student_ratings_deidentified.jsonl",
    ]
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(args.package), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = "unknown"
    manifest = {
        "analysis": "exploratory Qwen3-4B versus human disagreement by benchmark tier",
        "package_commit": commit,
        "model_key": MODEL_KEY,
        "n_benchmark_items": len(benchmark),
        "ratings_aggregated": {
            "experts": sum(len(r.get("ratings", [])) for r in panels["experts"]),
            "juniors": sum(len(r.get("ratings", [])) for r in panels["juniors"]),
        },
        "source_sha256": {
            str(p.relative_to(args.package)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_files
        },
        "output_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
        "privacy": "aggregate-only output; no article keys, titles, or rater identifiers serialized",
        "status": "exploratory, descriptive, not preregistered",
    }
    manifest_path = args.out.with_name("qwen_human_disagreement_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(out_rows)} tier-by-panel aggregate rows to {args.out}")
    print(f"Wrote input/output hashes and release commit to {manifest_path}")


if __name__ == "__main__":
    main()
