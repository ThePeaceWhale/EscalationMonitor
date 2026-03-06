#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Explain escalation probability from a prob.csv row: contributions and reasons in English.

Usage:
  python analyze.py prob.csv prob_explained.csv
  python analyze.py prob.csv prob_explained.csv --limit 10
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List

# Feature names (must match main2 / engine)
FEATURE_NAMES = [
    "news_negativity",
    "news_intensity",
    "escalation_keywords",
    "contiguity",
    "distance_closeness",
    "common_language",
    "both_in_nato",
    "mil_exp_mean",
    "ucdp_recent_interstate",
]

# Human-readable labels and short explanations (English)
FEATURE_INFO = {
    "news_negativity": (
        "News negativity",
        "Negative tone of recent news (GDELT) for this dyad; higher value increases escalation risk.",
    ),
    "news_intensity": (
        "News intensity",
        "Volume of conflict-weighted events in the news; more negative coverage increases risk.",
    ),
    "escalation_keywords": (
        "Escalation / conflict events",
        "Share of conflict-type events (assault, fight, violence); higher share increases risk.",
    ),
    "contiguity": (
        "Shared border",
        "Whether the two countries share a border; contiguity tends to increase risk.",
    ),
    "distance_closeness": (
        "Geographic closeness",
        "Closeness in km (exponential decay); closer countries have slightly higher baseline risk.",
    ),
    "common_language": (
        "Common official language",
        "Shared language; model uses a small negative weight (reduces friction in practice).",
    ),
    "both_in_nato": (
        "Both in NATO",
        "Both countries are NATO members; strong negative contribution (allies, lowers risk).",
    ),
    "mil_exp_mean": (
        "Military expenditure (mean)",
        "Average military spending (% GDP) of the two countries; higher spending increases risk.",
    ),
    "ucdp_recent_interstate": (
        "Recent interstate conflict",
        "Recent interstate conflict history (UCDP); past conflict increases risk.",
    ),
}


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def explain_row(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    From a prob.csv row, compute per-feature contributions and build explanation entries.
    Returns a list of dicts, one per feature, sorted by absolute contribution (most influential first).
    Each dict has: feature, label, value, weight, contribution, effect, explanation.
    """
    contributions: List[Dict[str, Any]] = []
    for k in FEATURE_NAMES:
        x = _safe_float(row.get(k))
        w = _safe_float(row.get(f"w_{k}"))
        c = w * x
        label, desc = FEATURE_INFO.get(k, (k, ""))
        if c > 0:
            effect = "increases"
        elif c < 0:
            effect = "decreases"
        else:
            effect = "neutral"
        explanation = f"{label} = {x:.3f} (weight {w:+.2f}) → contribution {c:+.3f} ({effect} risk). {desc}"
        contributions.append({
            "feature": k,
            "label": label,
            "value": x,
            "weight": w,
            "contribution": c,
            "effect": effect,
            "explanation": explanation,
        })
    contributions.sort(key=lambda d: abs(d["contribution"]), reverse=True)
    return contributions


def explain_row_to_text(row: Dict[str, Any]) -> str:
    """
    Build a single English explanation text for the row (probability and main reasons).
    """
    prob = _safe_float(row.get("probability"), float("nan"))
    bias = _safe_float(row.get("bias"))
    items = explain_row(row)
    z = bias + sum(d["contribution"] for d in items)
    lines = [
        f"Probability = {prob:.4f} (logit z = {z:.3f}, bias = {bias:.2f}).",
        "",
        "Contributions (most influential first):",
    ]
    for d in items:
        lines.append(f"  • {d['explanation']}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Explain prob.csv rows → prob_explained.csv")
    ap.add_argument("input_csv", type=str, default="prob.csv", nargs="?", help="Input prob.csv path")
    ap.add_argument("output_csv", type=str, default="prob_explained.csv", nargs="?", help="Output prob_explained.csv path")
    ap.add_argument("--limit", type=int, default=None, help="Process only first N rows (excluding header)")
    args = ap.parse_args()

    inp = Path(args.input_csv)
    out = Path(args.output_csv)
    if not inp.exists():
        print(f"Error: {inp} not found", file=sys.stderr)
        sys.exit(1)

    rows_read = 0
    with inp.open("r", encoding="utf-8", newline="") as fin:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            print("Error: empty or invalid CSV", file=sys.stderr)
            sys.exit(1)
        out_columns = ["country_a", "country_b", "probability", "explanation"]
        with out.open("w", encoding="utf-8", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=out_columns, extrasaction="ignore")
            writer.writeheader()
            for row in reader:
                if args.limit is not None and rows_read >= args.limit:
                    break
                explanation = explain_row_to_text(row)
                out_row = {
                    "country_a": row.get("country_a", ""),
                    "country_b": row.get("country_b", ""),
                    "probability": row.get("probability", ""),
                    "explanation": explanation,
                }
                writer.writerow(out_row)
                rows_read += 1
                if rows_read % 500 == 0:
                    print(f"Processed {rows_read} rows...", file=sys.stderr)

    print(f"Wrote {out} ({rows_read} rows)", file=sys.stderr)


if __name__ == "__main__":
    main()
