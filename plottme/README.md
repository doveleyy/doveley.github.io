# `plottme` SVG generator

`generate.py` creates a complete standalone vector graphic for a selected patient. It uses only the Python
standard library and the committed `data/outputs/patient_petals.js` payload—no browser, Node, or plotting package
is required.

Each export includes the whole report-ready graphic: grey 100th-percentile tumour silhouette, coloured TME score
lobes, 50th-percentile TME arcs and key, bucket petals, and all four legends with baseline bars.

## Export one patient

```bash
python plottme/generate.py --patient RHF1545
```

This writes `plottme/output/RHF1545-tme-bucket-plot.svg`.

Choose an explicit output file when integrating with a templated report:

```bash
python plottme/generate.py --patient RHF1545 --output reports/assets/RHF1545.svg
```

## Export all patients

```bash
python plottme/generate.py --all --output reports/assets/tme
```

Use `--input` to point to another compatible `patient_petals.js` file. The SVGs have a white/cream background,
so they remain visually consistent when embedded in Word, PowerPoint, HTML, or PDF templates.
