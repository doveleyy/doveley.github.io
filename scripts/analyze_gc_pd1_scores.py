from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


GROUPS = {
    "immunogenicity": [
        "antigen_presentation",
        "inflammation",
        "innate_immune_activation",
        "tme_stroma",
    ],
    "fibrosis": [
        "cell-matrix_adhesion",
        "ecm_remodelling",
        "fibroblast_signature",
        "pro-fibrotic_signalling",
    ],
    "angiogenesis": [
        "angiogenic_signalling",
        "endothelial_cell_signature",
        "hypoxia_signalling",
    ],
    "emt": [
        "emt_initiation",
        "emt_maintenance",
        "epithelial_markers",
        "mesenchymal_markers",
    ],
}

DISPLAY_TO_COLUMN = {
    "Antigen Presentation": "antigen_presentation",
    "Inflammation": "inflammation",
    "Innate Immune Activation": "innate_immune_activation",
    "TME/Stroma": "tme_stroma",
    "Cell-Matrix Adhesion": "cell-matrix_adhesion",
    "ECM Remodelling": "ecm_remodelling",
    "Fibroblast Signature": "fibroblast_signature",
    "Pro-Fibrotic Signalling": "pro-fibrotic_signalling",
    "Angiogenic Signalling": "angiogenic_signalling",
    "Endothelial Cell Signature": "endothelial_cell_signature",
    "Hypoxia Signalling": "hypoxia_signalling",
    "EMT Initiation": "emt_initiation",
    "EMT Maintenance": "emt_maintenance",
    "Epithelial Markers": "epithelial_markers",
    "Mesenchymal Markers": "mesenchymal_markers",
}


def main() -> None:
    df = pd.read_csv(ROOT / "data/gc_pd1_harmonised.csv")
    bucket_sets = pd.read_csv(ROOT / "data/outputs/tme_bucket_gene_sets.csv")
    column_to_display = {column: display for display, column in DISPLAY_TO_COLUMN.items()}
    contribution_rows = []

    print(f"rows={len(df)} cols={len(df.columns)}")

    for score, buckets in GROUPS.items():
        summed = df[buckets].sum(axis=1)
        diff = df[score] - summed
        contrib = df[buckets].div(df[score].replace(0, np.nan), axis=0)
        corr = df[[score, *buckets]].corr()[score].drop(score)

        print(f"\n{score}")
        print(f"  max_abs_diff={diff.abs().max():.12g}")
        print(f"  mean_abs_diff={diff.abs().mean():.12g}")
        print("  contribution fractions:")
        print(contrib.agg(["mean", "std", "min", "max"]).T.round(4).to_string())
        print("  bucket correlation with final score:")
        print(corr.round(4).to_string())

        for bucket in buckets:
            display = column_to_display[bucket]
            meta = bucket_sets.loc[bucket_sets["bucket"].eq(display)].iloc[0]
            contribution_rows.append(
                {
                    "score": score,
                    "bucket": display,
                    "n_sub_buckets": int(meta["n_sub_buckets"]),
                    "n_genes": int(meta["n_genes"]),
                    "mean_contribution": contrib[bucket].mean(),
                }
            )

    contribution_summary = pd.DataFrame(contribution_rows)
    print("\nmean contribution versus bucket size")
    print(
        contribution_summary.sort_values(
            ["score", "mean_contribution"], ascending=[True, False]
        )
        .round(4)
        .to_string(index=False)
    )
    print(
        "\ncorrelation: mean contribution vs n_sub_buckets = "
        f"{contribution_summary['mean_contribution'].corr(contribution_summary['n_sub_buckets']):.4f}"
    )
    print(
        "correlation: mean contribution vs n_genes = "
        f"{contribution_summary['mean_contribution'].corr(contribution_summary['n_genes']):.4f}"
    )


if __name__ == "__main__":
    main()
