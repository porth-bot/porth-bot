#!/usr/bin/env python3
"""Draw the cached contribution calendar as an animated SVG heatmap.

Cells reveal in a left-to-right sweep, one column of the year at a time. The
animation is CSS inside the SVG rather than a GIF, so it stays sharp at any
size and the whole card is a few tens of kilobytes.

    python scripts/render_heatmap.py
"""

import argparse
import json
from pathlib import Path

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}

# github's own dark ramp, so the card reads as a contribution graph on sight
LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

BG = "#0d1117"
EDGE = "#21262d"
DIM = "#7d8590"
TEXT = "#c9d1d9"

FONT = (
    "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
    "'DejaVu Sans Mono', monospace"
)

PAD = 20
GUTTER = 32
CELL = 11.0
GAP = 3.0
PITCH = CELL + GAP
MONTH_ROW = 15
FOOT_GAP = 20


def thresholds(counts):
    """Quartiles of the active days, the way GitHub buckets its own graph."""
    active = sorted(c for c in counts if c > 0)
    if not active:
        return [1, 2, 3, 4]
    return [active[int(len(active) * q)] for q in (0.0, 0.25, 0.5, 0.75)]


def level_of(count, cuts):
    if count <= 0:
        return 0
    return sum(count >= cut for cut in cuts)


def pretty(iso):
    year, month, day = (int(part) for part in iso.split("-"))
    return f"{MONTHS[month - 1]} {day}"


def month_ticks(weeks):
    """(column, label) for each week where a new month starts."""
    ticks = []
    seen = None
    for index, column in enumerate(weeks):
        first = next((day for day in column if day), None)
        if not first:
            continue
        month = int(first["date"].split("-")[1])
        if month != seen:
            # skip a label that would collide with the previous one
            if not ticks or index - ticks[-1][0] >= 3:
                ticks.append((index, MONTHS[month - 1]))
            seen = month
    return ticks


def build(data):
    weeks = data["weeks"]
    cuts = thresholds([d["count"] for col in weeks for d in col if d])

    grid_w = len(weeks) * PITCH - GAP
    grid_x = PAD + GUTTER
    grid_y = PAD + MONTH_ROW
    grid_h = 7 * PITCH - GAP

    foot_y = grid_y + grid_h + FOOT_GAP
    width = round(grid_x + grid_w + PAD)
    height = round(foot_y + 12 + PAD)

    parts = []

    for column, label in month_ticks(weeks):
        x = grid_x + column * PITCH
        parts.append(
            f'<text class="lbl" x="{x:.1f}" y="{PAD + 8}" fill="{DIM}">{label}</text>'
        )

    for weekday, label in DAY_LABELS.items():
        y = grid_y + weekday * PITCH + CELL * 0.78
        parts.append(
            f'<text class="lbl" x="{PAD}" y="{y:.1f}" fill="{DIM}">{label}</text>'
        )

    for index, column in enumerate(weeks):
        x = grid_x + index * PITCH
        for weekday, day in enumerate(column):
            if not day:
                continue
            y = grid_y + weekday * PITCH
            level = level_of(day["count"], cuts)
            delay = round(0.25 + index * 0.026 + weekday * 0.008, 3)
            plural = "" if day["count"] == 1 else "s"
            parts.append(
                f'<rect class="d" x="{x:.1f}" y="{y:.1f}" width="{CELL}" '
                f'height="{CELL}" rx="2.5" fill="{LEVELS[level]}" '
                f'style="animation-delay:{delay}s">'
                f'<title>{day["count"]} contribution{plural} on '
                f'{pretty(day["date"])}</title></rect>'
            )

    sweep = round(0.25 + len(weeks) * 0.026 + 0.5, 2)

    # runs of spaces collapse in SVG text, so the separator has to be a glyph
    stats = " · ".join(
        [
            f"{data['total']} contributions",
            f"{data['current_streak']}-day streak",
            f"longest {data['longest_streak']}",
            f"busiest {pretty(data['busiest']['date'])} ({data['busiest']['count']})",
        ]
    )
    parts.append(
        f'<text class="foot" x="{PAD}" y="{foot_y:.1f}" fill="{TEXT}" '
        f'style="animation-delay:{sweep}s">{stats}</text>'
    )

    # laid out from the right edge of the grid inward, so "More" lands inside
    # the card rather than under the border
    legend_w = 128
    legend_x = grid_x + grid_w - legend_w
    parts.append(
        f'<text class="foot" x="{legend_x:.1f}" y="{foot_y:.1f}" fill="{DIM}" '
        f'style="animation-delay:{sweep}s">Less</text>'
    )
    for step, colour in enumerate(LEVELS):
        parts.append(
            f'<rect class="foot" x="{legend_x + 30 + step * 14:.1f}" '
            f'y="{foot_y - 8:.1f}" width="10" height="10" rx="2.5" fill="{colour}" '
            f'style="animation-delay:{sweep}s"/>'
        )
    parts.append(
        f'<text class="foot" x="{legend_x + 100:.1f}" y="{foot_y:.1f}" '
        f'fill="{DIM}" style="animation-delay:{sweep}s">More</text>'
    )

    style = (
        f".lbl{{font:9px {FONT}}}"
        f".foot{{font:10px {FONT}}}"
        # backwards fill, and nothing hidden in the base rules, so the settled
        # state is also what a viewer sees if CSS animation never runs
        ".d,.foot{animation:pop .5s cubic-bezier(.2,.8,.3,1) backwards}"
        ".d{transform-box:fill-box;transform-origin:50% 50%}"
        "@keyframes pop{0%{opacity:0;transform:scale(.3)}"
        "65%{opacity:1;transform:scale(1.08)}100%{opacity:1;transform:scale(1)}}"
        "@media(prefers-reduced-motion:reduce){.d,.foot{animation:none}}"
    )

    label = (
        f"{data['total']} GitHub contributions by {data['login']} "
        f"from {data['start']} to {data['end']}"
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{label}">'
        f"<style>{style}</style>"
        f'<rect width="{width}" height="{height}" rx="10" fill="{BG}" '
        f'stroke="{EDGE}"/>'
        f'{"".join(parts)}</svg>'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="scripts/contrib.json")
    parser.add_argument("--out", default="assets/contrib-heatmap.svg")
    args = parser.parse_args()

    data = json.loads(Path(args.data).read_text())
    svg = build(data)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg + "\n")
    print(f"wrote {out} ({len(svg) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
