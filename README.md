# TME Bucket Percentile Plot

Static GitHub Pages prototype for the TME bucket percentile petal plot.

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
- `pages/score-size-bias.html` - evidence page for raw score size bias and raw contribution petal examples.
- `pages/score-blob-summary.html` - archived alternate visual.
- `data/` - source CSVs and bucket mapping outputs used to generate/check the figures.
- `scripts/` - analysis helper scripts.
- `tme_bucket_percentile_overlay.html`, `score_size_bias_scatter.html`, `tme_score_blob_summary.html`, `tme_organic_tumour_overlay.html` - compatibility redirects for older links.

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
