"""Generate the per-patient petal data consumed by index.html.

Writes ``data/outputs/patient_petals.js`` which assigns ``window.PATIENT_PETALS``.
A plain script tag is used instead of ``fetch`` so the page keeps working over
``file://`` and on GitHub Pages without a build step. The generated file is committed.

Each bucket carries two independent values:

``v``    the share input: the raw bucket score, which already sums to the axis score
         exactly. The plot renders ``100 * (v / nSub) / sum(v / nSub)``, so the shares
         total 100% whatever units ``v`` is in.
``pct``  the bucket's percentile within the baseline cohort, used for the legend
         bullet strip. Never feeds the geometry.

Per-axis ``nSub`` in the schema is the sub-bucket count for each bucket. Absolute bucket
score scales with sub-bucket count (r = 0.987), so dividing by it before taking shares
stops big buckets dominating a quadrant purely because they are big.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_gc_pd1_scores import GROUPS, DISPLAY_TO_COLUMN


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/outputs/patient_petals.js"
SUBBUCKETS = ROOT / "data/outputs/tme_subbucket_mapping.csv"
BASELINE_LABEL = "GC PD-1 harmonised cohort"

AXIS_ORDER = ["angiogenesis", "immunogenicity", "fibrosis", "emt"]
COLUMN_TO_DISPLAY = {column: display for display, column in DISPLAY_TO_COLUMN.items()}


def largest_remainder(values: list[float], total: int = 100) -> list[int]:
    """Round shares so the displayed integers sum to exactly ``total``.

    Independent rounding can print 33/33/33 = 99 or 34/33/34 = 101, which is the
    property the plot is meant to guarantee. Mirrors ``largestRemainder()`` in index.html.
    """
    weight = sum(values)
    if weight <= 0:
        return [0] * len(values)
    exact = [v / weight * total for v in values]
    floors = [int(x) for x in exact]
    remainder = total - sum(floors)
    order = sorted(range(len(exact)), key=lambda i: exact[i] - floors[i], reverse=True)
    for i in order[:remainder]:
        floors[i] += 1
    return floors


def sub_bucket_counts() -> dict[str, int]:
    """Sub-buckets per bucket, keyed by the bucket's display name."""
    mapping = pd.read_csv(SUBBUCKETS)
    counts = mapping.groupby("bucket")["sub_bucket_id"].nunique().to_dict()
    missing = [name for name in DISPLAY_TO_COLUMN if name not in counts]
    assert not missing, f"no sub-buckets found for: {missing}"
    assert all(counts[name] > 0 for name in DISPLAY_TO_COLUMN), "zero sub-bucket count"
    return counts


def main() -> None:
    df = pd.read_csv(ROOT / "data/gc_pd1_harmonised.csv")
    n_sub = sub_bucket_counts()
    score_columns = list(GROUPS) + [c for buckets in GROUPS.values() for c in buckets]

    assert not df["sample_id"].duplicated().any(), "duplicate sample_id"
    missing = df[score_columns].isna().sum()
    assert missing.sum() == 0, f"nulls in score columns:\n{missing[missing > 0]}"

    for axis, buckets in GROUPS.items():
        drift = (df[axis] - df[buckets].sum(axis=1)).abs().max()
        assert drift < 1e-9, f"{axis}: axis score is not the sum of its buckets (max drift {drift})"

    percentiles = {c: (df[c].rank(pct=True) * 100).round().astype(int) for c in score_columns}

    schema = {
        "axes": [
            {
                "key": axis,
                "buckets": [COLUMN_TO_DISPLAY[c] for c in GROUPS[axis]],
                "nSub": [n_sub[COLUMN_TO_DISPLAY[c]] for c in GROUPS[axis]],
            }
            for axis in AXIS_ORDER
        ]
    }

    patients = []
    for row_index, row in df.iterrows():
        axes_payload = []
        for axis in AXIS_ORDER:
            buckets = GROUPS[axis]
            values = [round(float(row[c]), 4) for c in buckets]
            # Mirrors axisShares() in index.html: normalise by sub-bucket count first.
            normalised = [v / n_sub[COLUMN_TO_DISPLAY[c]] for v, c in zip(values, buckets)]
            shares = largest_remainder(normalised)
            assert sum(shares) == 100, f"{row['sample_id']} / {axis}: shares sum to {sum(shares)}"
            axes_payload.append(
                {
                    "pct": int(percentiles[axis][row_index]),
                    "v": values,
                    "bucketPct": [int(percentiles[c][row_index]) for c in buckets],
                }
            )
        patients.append(
            {
                "id": str(row["sample_id"]),
                "response": str(row["ground_truth"]),
                "axes": axes_payload,
            }
        )

    bucket_columns = [c for buckets in GROUPS.values() for c in buckets]

    payload = {
        "baselineLabel": BASELINE_LABEL,
        "cohortSize": int(len(df)),
        # Upper bound for the share-input sliders, in the data's own units.
        "vMax": float(round(df[bucket_columns].max().max() * 1.2, 1)),
        "schema": schema,
        "patients": patients,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "// Generated by scripts/build_patient_petals.py - do not edit by hand.\n"
        "window.PATIENT_PETALS = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    print(f"wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:.0f} KB)")
    print(f"patients={len(patients)} baseline={BASELINE_LABEL} (n={len(df)})")
    print(f"response mix: {df['ground_truth'].value_counts(dropna=False).to_dict()}")

    for axis in AXIS_ORDER:
        buckets = GROUPS[axis]
        per_sub = df[buckets].div([n_sub[COLUMN_TO_DISPLAY[c]] for c in buckets], axis=1)
        shares = per_sub.div(per_sub.sum(axis=1), axis=0) * 100
        print(
            f"\n{axis}  axis score {df[axis].min():.2f}-{df[axis].max():.2f}  "
            f"axis percentile {percentiles[axis].min()}-{percentiles[axis].max()}"
        )
        summary = pd.DataFrame(
            {
                "n_sub": pd.Series({c: n_sub[COLUMN_TO_DISPLAY[c]] for c in buckets}),
                "share_mean": shares.mean(),
                "share_sd": shares.std(),
                "share_min": shares.min(),
                "share_max": shares.max(),
                "pct_min": pd.Series({c: percentiles[c].min() for c in buckets}),
                "pct_max": pd.Series({c: percentiles[c].max() for c in buckets}),
            }
        )
        print(summary.round(2).to_string())


if __name__ == "__main__":
    main()
