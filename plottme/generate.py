#!/usr/bin/env python3
"""Generate standalone TME bucket SVGs without browser or package dependencies.

The generator reads ``data/outputs/patient_petals.js`` and writes a complete
1260 x 600 SVG for one patient (or every patient).  Each SVG includes the full
visualisation: the grey 100th-percentile silhouette, coloured TME lobes,
TME-score median arcs, bucket petals, and all four legends.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/outputs/patient_petals.js"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "output"

WIDTH, HEIGHT = 1260, 600
CX, CY = 630, 300
BASE_R, EXTRA_R, CORE_R, AXIS_GAP = 76, 148, 30, 5
FULL_SCALE_FILL = "#cfcfc9"
TME_MEDIAN_COLOR = "#4a4640"
RULE_COLOR = "#d9d1c4"
CORE_FILL = "#fffdf8"
WEDGE_STROKE = "#f0ebe2"

AXES = [
    ("angiogenesis", "Angiogenesis", "#378ADD", ["#378add", "#499cef", "#5baeff"]),
    ("immunogenicity", "Immunogenicity", "#0F6E56", ["#0f6e56", "#218068", "#33927a", "#45a48c"]),
    ("fibrosis", "Fibrosis", "#993C1D", ["#993c1d", "#ab4e2f", "#bd6041", "#cf7253"]),
    ("emt", "EMT", "#993556", ["#993556", "#ab4768", "#bd597a", "#cf6b8c"]),
]
LABEL_BLOCKS = [(898, 112, 330), (898, 404, 330), (32, 404, 330), (32, 112, 330)]


def shade(hex_colour: str, amount: int) -> str:
    """Lighten or darken a #rrggbb colour, matching the browser implementation."""
    value = int(hex_colour[1:], 16)
    channels = [max(0, min(255, ((value >> shift) & 255) + amount)) for shift in (16, 8, 0)]
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def point(radius: float, angle_degrees: float) -> tuple[float, float]:
    radians = math.radians(angle_degrees)
    return CX + radius * math.cos(radians), CY + radius * math.sin(radians)


def middle_lift(t: float) -> float:
    return 0.84 + 0.16 * math.sin(math.pi * t)


def radius_at(axis_index: int, percentile: float, angle: float) -> float:
    """Organic lobe radius for an axis percentile at a particular angle."""
    angle_normalised = angle % 360
    start = -90 + axis_index * 90 + AXIS_GAP
    end = -90 + (axis_index + 1) * 90 - AXIS_GAP
    t = (angle - start) / (end - start)
    radius = (BASE_R + max(0, min(100, percentile)) / 100 * EXTRA_R) * middle_lift(t)
    radius += 7 * math.sin(angle_normalised * 0.09) + 4 * math.sin(angle_normalised * 0.21 + 1.3)
    return max(30, radius)


def path_from_points(points: list[tuple[float, float]], close: bool = False) -> str:
    commands = [f"M{points[0][0]:.1f} {points[0][1]:.1f}"]
    commands.extend(f"L{x:.1f} {y:.1f}" for x, y in points[1:])
    if close:
        commands.append("Z")
    return " ".join(commands)


def lobe_path(axis_index: int, percentile: float, start: float, end: float, steps: int = 28) -> str:
    outer = [point(radius_at(axis_index, percentile, start + (end - start) * step / steps), start + (end - start) * step / steps) for step in range(steps + 1)]
    inner = [point(CORE_R, start + (end - start) * step / steps) for step in range(steps, -1, -1)]
    return path_from_points(outer + inner, close=True)


def arc_path(axis_index: int, percentile: float, start: float, end: float, steps: int = 28) -> str:
    points = [point(radius_at(axis_index, percentile, start + (end - start) * step / steps), start + (end - start) * step / steps) for step in range(steps + 1)]
    return path_from_points(points)


def relative_weights(percentiles: list[int]) -> list[int]:
    """Largest-remainder normalisation, producing integer values that sum to 100."""
    values = [max(0, value) for value in percentiles]
    total = sum(values)
    if not total:
        base, remainder = divmod(100, len(values))
        return [base + int(index < remainder) for index in range(len(values))]
    exact = [value / total * 100 for value in values]
    weights = [math.floor(value) for value in exact]
    remainder = 100 - sum(weights)
    order = sorted(range(len(values)), key=lambda index: exact[index] - weights[index], reverse=True)
    for index in order[:remainder]:
        weights[index] += 1
    return weights


def baseline_bar(x: float, y: float, percentile: int, colour: str) -> str:
    width, height, top = 70, 6, y - 5
    fill = max(0, min(100, percentile)) / 100 * width
    return (
        f'<rect x="{x:.1f}" y="{top:.1f}" width="{width}" height="{height}" rx="3" fill="{shade(colour, 96)}" opacity="0.5"/>'
        f'<rect x="{x:.1f}" y="{top:.1f}" width="{fill:.1f}" height="{height}" rx="3" fill="{colour}"/>'
        f'<line x1="{x + width / 2:.1f}" y1="{top - 2:.1f}" x2="{x + width / 2:.1f}" y2="{top + height + 2:.1f}" stroke="#5f5d59" stroke-width="1"/>'
    )


def load_payload(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    match = re.search(r"window\.PATIENT_PETALS\s*=\s*(\{.*\})\s*;?\s*$", source, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not find window.PATIENT_PETALS JSON in {path}")
    return json.loads(match.group(1))


def render_svg(payload: dict, patient: dict) -> str:
    schema_by_key = {axis["key"]: axis for axis in payload["schema"]["axes"]}
    baseline_label = f'{payload["baselineLabel"]} (n = {payload["cohortSize"]})'
    backdrops: list[str] = []
    envelopes: list[str] = []
    petals: list[str] = []
    median_arcs: list[str] = []
    outlines: list[str] = []
    legend: list[str] = []

    for axis_index, (key, display_name, colour, palette) in enumerate(AXES):
        axis_data = patient["axes"][axis_index]
        schema = schema_by_key[key]
        bucket_names = schema["buckets"]
        bucket_percentiles = axis_data["bucketPct"]
        weights = relative_weights(bucket_percentiles)
        score_percentile = axis_data["pct"]
        start = -90 + axis_index * 90 + AXIS_GAP
        end = -90 + (axis_index + 1) * 90 - AXIS_GAP

        backdrops.append(
            f'<path d="{lobe_path(axis_index, 100, start, end)}" fill="{FULL_SCALE_FILL}" opacity="0.30"><title>{escape(display_name)} full-scale reference (100th percentile)</title></path>'
        )
        envelopes.append(
            f'<path d="{lobe_path(axis_index, score_percentile, start, end)}" fill="{shade(colour, 62)}" opacity="0.20"><title>{escape(display_name)} score envelope (percentile {score_percentile})</title></path>'
        )
        median_arcs.append(
            f'<path d="{arc_path(axis_index, 50, start, end)}" fill="none" stroke="{TME_MEDIAN_COLOR}" stroke-width="1.2" stroke-dasharray="5 4" stroke-linecap="round" opacity="0.78"><title>{escape(display_name)} 50th percentile</title></path>'
        )
        outlines.append(
            f'<path d="{arc_path(axis_index, score_percentile, start, end)}" fill="none" stroke="{colour}" stroke-width="1.4" stroke-opacity="0.55" stroke-linecap="round"/>'
        )

        bucket_gap = 1.6
        bucket_angle = (end - start - (len(bucket_names) - 1) * bucket_gap) / len(bucket_names)
        largest_weight = max(weights) if weights else 0
        for bucket_index, (bucket_name, percentile, weight) in enumerate(zip(bucket_names, bucket_percentiles, weights)):
            bucket_start = start + bucket_index * (bucket_angle + bucket_gap)
            bucket_end = bucket_start + bucket_angle
            fraction = weight / largest_weight if largest_weight else 0
            outer = []
            for step in range(17):
                angle = bucket_start + (bucket_end - bucket_start) * step / 16
                radius = CORE_R + fraction * (radius_at(axis_index, score_percentile, angle) - CORE_R)
                outer.append(point(radius, angle))
            inner = [point(CORE_R, bucket_start + (bucket_end - bucket_start) * step / 16) for step in range(16, -1, -1)]
            petal_colour = palette[bucket_index % len(palette)]
            title = (
                f"{display_name} - {bucket_name} ({weight}% relative signal; percentile {percentile} vs {baseline_label}; "
                f"{schema['nSub'][bucket_index]} sub-buckets)"
            )
            petals.append(
                f'<path d="{path_from_points(outer + inner, close=True)}" fill="{petal_colour}" stroke="{WEDGE_STROKE}" stroke-width="0.7"><title>{escape(title)}</title></path>'
            )

        label_x, label_y, label_width = LABEL_BLOCKS[axis_index]
        legend.extend(
            [
                f'<text x="{label_x}" y="{label_y}" fill="#202020" font-size="14" font-weight="800">{escape(display_name)}</text>',
                f'<text x="{label_x + label_width}" y="{label_y}" text-anchor="end" fill="{colour}" font-size="15" font-weight="800">{score_percentile}</text>',
                f'<line x1="{label_x}" y1="{label_y + 9}" x2="{label_x + label_width}" y2="{label_y + 9}" stroke="{colour}" stroke-width="1.4" opacity="0.58"/>',
                f'<text x="{label_x + 220}" y="{label_y + 27}" text-anchor="end" fill="#5f5d59" font-size="8.6" font-weight="800" letter-spacing="0.05em">REL. SIGNAL</text>',
                f'<text x="{label_x + 254}" y="{label_y + 27}" fill="#5f5d59" font-size="8.6" font-weight="800" letter-spacing="0.05em">VS BASELINE</text>',
            ]
        )
        for bucket_index, (bucket_name, percentile, weight) in enumerate(zip(bucket_names, bucket_percentiles, weights)):
            y = label_y + 52 + bucket_index * 20
            petal_colour = palette[bucket_index % len(palette)]
            legend.extend(
                [
                    f'<rect x="{label_x}" y="{y - 8}" width="9" height="9" rx="2" fill="{petal_colour}"/>',
                    f'<text x="{label_x + 14}" y="{y}" fill="#2f2f2f" font-size="9.6" font-weight="650">{escape(bucket_name)}</text>',
                    f'<text x="{label_x + 220}" y="{y}" text-anchor="end" fill="{petal_colour}" font-size="10.5" font-weight="800">{weight}%</text>',
                    baseline_bar(label_x + 254, y, percentile, petal_colour),
                ]
            )

    key_y = 558
    key = (
        f'<line x1="{CX - 154}" y1="{key_y}" x2="{CX - 122}" y2="{key_y}" stroke="{TME_MEDIAN_COLOR}" stroke-width="1.2" stroke-dasharray="5 4" stroke-linecap="round" opacity="0.78"/>'
        f'<text x="{CX - 112}" y="{key_y + 4}" fill="#4a4640" font-size="10.5" font-weight="700">TME score median · 50th percentile</text>'
        f'<text x="{CX}" y="586" text-anchor="middle" fill="#5f5d59" font-size="11">Relative signals total 100% within each TME lobe; baseline bars show bucket percentiles.</text>'
    )
    patient_title = escape(f"TME bucket tumour plot — {patient['id']} ({patient['response']})")
    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            f"<title id=\"title\">{patient_title}</title>",
            '<desc id="desc">TME score percentile tumour plot with relative bucket signals and cohort percentile baseline bars.</desc>',
            f'<rect width="{WIDTH}" height="{HEIGHT}" fill="#f8f6f1"/>',
            *backdrops,
            *envelopes,
            *petals,
            *median_arcs,
            *outlines,
            f'<circle cx="{CX}" cy="{CY}" r="{CORE_R}" fill="{CORE_FILL}" stroke="{RULE_COLOR}" stroke-width="0.5"/>',
            *legend,
            key,
            "</svg>",
        ]
    )


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "patient"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate standalone SVGs for the TME bucket plot.")
    parser.add_argument("--patient", help="Patient ID to export.")
    parser.add_argument("--all", action="store_true", help="Export every patient.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to patient_petals.js.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output directory, or output SVG file for one patient.")
    args = parser.parse_args()
    if bool(args.patient) == bool(args.all):
        parser.error("choose exactly one of --patient or --all")

    payload = load_payload(args.input)
    patients = payload["patients"]
    if args.all:
        output_dir = args.output
        output_dir.mkdir(parents=True, exist_ok=True)
        selected = patients
    else:
        selected = [patient for patient in patients if patient["id"] == args.patient]
        if not selected:
            parser.error(f"patient not found: {args.patient}")
        output_dir = args.output.parent if args.output.suffix.lower() == ".svg" else args.output
        output_dir.mkdir(parents=True, exist_ok=True)

    for patient in selected:
        output = args.output if (not args.all and args.output.suffix.lower() == ".svg") else output_dir / f"{safe_filename(patient['id'])}-tme-bucket-plot.svg"
        output.write_text(render_svg(payload, patient), encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
