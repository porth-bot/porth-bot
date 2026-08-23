#!/usr/bin/env python3
"""Render the neofetch-style info panel that sits beside the ASCII portrait.

Everything a reader would otherwise have to dig through six repos to learn,
on one card. Edit CARD below; the layout sizes itself around it.

    python scripts/make_info_card.py
"""

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

USER = "parth"
HOST = "github"

CARD = [
    ("school", ["Wayzata High School '28, Minnesota"]),
    ("math", ["UMTYMP at UMN: multivariable, diffeq, linalg"]),
    ("summer", ["MIT Beaver Works Summer Institute '26"]),
    ("focus", ["computer vision, probability, training dynamics"]),
    (None, []),
    ("langs", ["Python, C++, Java, C#, JavaScript"]),
    ("ml", ["PyTorch, TensorFlow, NumPy, Core ML, OpenCV"]),
    ("stack", ["FastAPI, Next.js, Docker, Postgres, Redis, Linux"]),
    (None, []),
    (
        "research",
        [
            "DeepScope, real-time deepfake detection",
            "3rd Grand Award, Software Design, ISEF 2026",
            "ChemPrint, PFAS source attribution",
            "Stockholm Junior Water Prize national finalist",
        ],
    ),
    (None, []),
    (
        "building",
        [
            "ML from scratch: mcmc, gp, grokking, pinn,",
            "diffusion. 1,337 tests, all vs ground truth",
        ],
    ),
]

PALETTE = [
    "#39d353",
    "#26a641",
    "#006d32",
    "#58a6ff",
    "#a371f7",
    "#f778ba",
    "#f0883e",
    "#c9d1d9",
]

BG = "#0d1117"
EDGE = "#21262d"
KEY = "#58a6ff"
VALUE = "#c9d1d9"
DIM = "#7d8590"
ACCENT = "#39d353"

FONT = (
    "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
    "'DejaVu Sans Mono', monospace"
)

PAD = 18
SIZE = 9.6
LINE = 14.6
KEY_X = PAD
VALUE_X = PAD + 62


def rows():
    """Flatten CARD into drawable lines: (key or None, value or None)."""
    out = []
    for key, values in CARD:
        if key is None:
            out.append((None, None))
            continue
        for index, value in enumerate(values):
            out.append((key if index == 0 else None, value))
    return out


def build(width, min_height):
    lines = rows()

    y = PAD + SIZE + 4
    parts = [
        f'<text class="r" x="{KEY_X}" y="{y:.1f}" style="animation-delay:0.1s">'
        f'<tspan fill="{ACCENT}">{USER}</tspan>'
        f'<tspan fill="{DIM}">@</tspan>'
        f'<tspan fill="{KEY}">{HOST}</tspan></text>'
    ]

    y += 7
    parts.append(
        f'<line class="r" x1="{PAD}" y1="{y:.1f}" x2="{width - PAD}" y2="{y:.1f}" '
        f'stroke="{EDGE}" style="animation-delay:0.16s"/>'
    )

    y += LINE
    for index, (key, value) in enumerate(lines):
        delay = round(0.22 + index * 0.05, 3)
        if key:
            parts.append(
                f'<text class="r" x="{KEY_X}" y="{y:.1f}" fill="{KEY}" '
                f'style="animation-delay:{delay}s">{key}</text>'
            )
        if value:
            parts.append(
                f'<text class="r" x="{VALUE_X}" y="{y:.1f}" fill="{VALUE}" '
                f'style="animation-delay:{delay}s">{escape(value)}</text>'
            )
        y += LINE if value else LINE * 0.55

    swatch = 13
    y = max(y + 8, min_height - PAD - swatch)
    tail = round(0.22 + len(lines) * 0.05 + 0.1, 3)
    for index, colour in enumerate(PALETTE):
        parts.append(
            f'<rect class="r" x="{PAD + index * (swatch + 4)}" y="{y:.1f}" '
            f'width="{swatch}" height="{swatch}" rx="2.5" fill="{colour}" '
            f'style="animation-delay:{round(tail + index * 0.04, 3)}s"/>'
        )

    height = max(round(y + swatch + PAD), min_height)

    style = (
        f"text{{font:{SIZE}px {FONT}}}"
        # backwards fill and no hidden base state, so a renderer that freezes
        # or skips CSS animation still shows the finished card
        ".r{animation:slide .45s ease-out backwards}"
        "@keyframes slide{from{opacity:0;transform:translateX(-6px)}"
        "to{opacity:1;transform:translateX(0)}}"
        "@media(prefers-reduced-motion:reduce){.r{animation:none}}"
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{USER}@{HOST}: school, stack, research and current work">'
        f"<style>{style}</style>"
        f'<rect width="{width}" height="{height}" rx="10" fill="{BG}" '
        f'stroke="{EDGE}"/>'
        f'{"".join(parts)}</svg>'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="assets/info-card.svg")
    parser.add_argument("--width", type=int, default=380)
    parser.add_argument(
        "--min-height",
        type=int,
        default=363,
        help="pad to this so the card lines up with the portrait beside it",
    )
    args = parser.parse_args()

    svg = build(args.width, args.min_height)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg + "\n")
    print(f"wrote {out} ({len(svg) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
