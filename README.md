# TME Bucket Plot

TME Bucket Plot is a static, patient-level visualisation of tumour microenvironment (TME) scores and their
underlying gene-set buckets. It is designed to run as a simple web page and to export complete vector graphics for
reports.

The site has no frontend build step. The committed patient payload is loaded directly by the page, so it can be
hosted on GitHub Pages or any static web server.

## What the plot shows

Each patient is shown as a four-lobed tumour:

- **Outer coloured lobes** represent the percentile of the four TME scores: Angiogenesis, Immunogenicity,
  Fibrosis, and EMT.
- A **faint grey silhouette** shows the 100th-percentile extent, providing a common visual scale.
- A **dashed arc** in every lobe marks the 50th percentile for that TME score.
- **Inner bucket petals** represent percentile-derived *relative signal*. Bucket percentiles are rebased within
  each TME score so their displayed values total exactly 100%.
- The legend's **baseline bar** shows the original bucket percentile against the baseline cohort. Its centre tick
  is the 50th percentile.

Relative signal shows which buckets are most prominent within a patient's percentile pattern. It is not a raw-score
contribution, a variance decomposition, or a percentage of the TME score.

## Quick start

Start a local static server from the repository root:

```bash
./view_tme_visual.sh
```

Open [http://127.0.0.1:8000/index.html](http://127.0.0.1:8000/index.html). To use another port:

```bash
./view_tme_visual.sh 8001
```

The checked-in `data/outputs/patient_petals.js` file is sufficient to view the plot; no data build is required for
normal previewing.

## Data flow

```text
data/gc_pd1_harmonised.csv
        │
        ├── scripts/build_patient_petals.py
        │
        └── data/outputs/patient_petals.js ──┬── index.html
                                              └── plottme/generate.py → standalone SVG
```

`patient_petals.js` contains patient IDs, TME-score percentiles, bucket percentiles, raw bucket values, and the
bucket schema used by both the web page and the SVG generator.

### Rebuild the patient payload

Install [Pixi](https://pixi.sh/) if needed, then run:

```bash
pixi run build-data
```

Run this after changing `data/gc_pd1_harmonised.csv`, the score definitions, or the bucket mapping. The build checks
that each TME score equals the sum of its buckets, required values are present, and every bucket has sub-bucket
metadata.

## Generate report-ready SVGs

[`plottme/generate.py`](plottme/generate.py) is a dependency-free Python generator. It creates one complete,
standalone SVG containing the tumour, TME percentile arcs, bucket petals, legends, labels, and background.

Export one patient from the default input, `data/outputs/patient_petals.js`:

```bash
python3 plottme/generate.py --patient RHF1545
```

The result is written to:

```text
plottme/output/RHF1545-tme-bucket-plot.svg
```

Choose a report-template destination explicitly:

```bash
python3 plottme/generate.py \
  --patient RHF1545 \
  --output reports/assets/RHF1545.svg
```

Export every patient:

```bash
python3 plottme/generate.py --all --output reports/assets/tme
```

To use a different compatible payload, provide it with `--input`:

```bash
python3 plottme/generate.py \
  --input path/to/patient_petals.js \
  --patient RHF1545 \
  --output reports/assets/RHF1545.svg
```

Generated files under `plottme/output/` are ignored by Git. See [plottme/README.md](plottme/README.md) for the
generator's focused reference.

## Repository layout

| Path | Purpose |
| --- | --- |
| `index.html` | Main interactive TME Bucket Plot. |
| `data/gc_pd1_harmonised.csv` | Harmonised patient-level source scores. |
| `data/outputs/` | Generated patient payload and score/bucket mapping tables. |
| `scripts/build_patient_petals.py` | Builds the patient payload consumed by the plot and SVG generator. |
| `plottme/` | Lightweight standalone SVG generator and its documentation. |
| `pages/gene-set-explorer.html` | Browser for score, bucket, sub-bucket, and gene mappings. |
| `pages/` | Archived alternative visualisations and rationale pages. |
| `pixi.toml` | Reproducible Python environment and project tasks. |

The root-level `*_overlay.html`, `*_summary.html`, and `*_scatter.html` files are compatibility redirects for older
links.

## Static hosting

Publish the repository root with GitHub Pages or another static host. The public entry point is `index.html`; it
loads the committed patient payload with a script tag and requires no server-side application.
