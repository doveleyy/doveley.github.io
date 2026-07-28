# TME Bucket Percentile Plot

Static GitHub Pages prototype for the TME bucket percentile petal plot.

Each score petal bulges by its TME axis percentile. Inside it, bucket wedges span the petal's radius and
take an angular slice equal to their share of the score, so buckets are contained within their score petal
by construction and their displayed percentages total 100%. Percentile to baseline is shown as a legend
bullet strip rather than by bucket petal size.

## Preview locally

```bash
./view_tme_visual.sh
```

Then open:

```text
http://127.0.0.1:8000/index.html
```

If port `8000` is busy:

```bash
./view_tme_visual.sh 8001
```

## Site structure

- `index.html` - main page: primary petal plot, rationale, and archive links.
- `pages/gene-set-explorer.html` - filterable table for genes, buckets, and subbuckets.
- `pages/score-size-bias.html` - archived rationale page for bucket-size bias and raw contribution examples.
- `pages/score-blob-summary.html` - archived alternate visual.
- `data/` - source CSVs and bucket mapping outputs used to generate/check the figures.
- `data/outputs/patient_petals.js` - generated per-patient plot data loaded by `index.html`.
- `scripts/` - analysis helper scripts.
- `tme_bucket_percentile_overlay.html`, `score_size_bias_scatter.html`, `tme_score_blob_summary.html`, `tme_organic_tumour_overlay.html` - compatibility redirects for older links.

## Regenerating Patient Data

The site itself has no build step: `data/outputs/patient_petals.js` is generated ahead of time and committed.
Regenerate it after changing the source CSV or bucket values with:

```bash
pixi run build-data
```

The generator asserts that every axis score equals the sum of its bucket scores, that there are no missing
score values, and that every displayed bucket share total is exactly 100%.

## Optional analysis helper

The site itself has no build step. To rerun the optional analysis helper, install the Pixi environment and run:

```bash
pixi run python scripts/analyze_gc_pd1_scores.py
```

## GitHub Pages

This repo is ready to publish from the repository root. In GitHub:

1. Go to **Settings > Pages**.
2. Set **Source** to the branch you push.
3. Set the folder to `/root`.
4. Save.

The public page will load `index.html` automatically.

## Notes

- The oversized discussion deck is intentionally kept in `local/` and ignored by Git, because GitHub blocks files over 100 MB.
- The site is plain HTML/CSS/JavaScript and has no build step.
