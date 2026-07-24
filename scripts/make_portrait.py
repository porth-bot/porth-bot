#!/usr/bin/env python3
"""Render the prepped headshot as an ASCII portrait that types itself in.

Rows are drawn as monospace <text> runs pinned with textLength, so the glyph
grid lines up the same way whether the viewer has SF Mono, Menlo, or DejaVu.
Each row is revealed by a SMIL clip animating left to right, staggered top to
bottom, which reads like a terminal painting the image line by line.

    python scripts/make_portrait.py --preview     # eyeball it in a terminal
    python scripts/make_portrait.py               # write assets/portrait.svg
"""

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

# sparse to dense. inverted at lookup time so dark pixels get the heavy glyphs
RAMP = " .:-=+*#%@"

FONT = (
    "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
    "'DejaVu Sans Mono', monospace"
)


def to_rows(path, cols, rows, floor):
    image = Image.open(path).convert("LA").resize((cols, rows), Image.LANCZOS)
    pixels = image.load()
    out = []
    for y in range(rows):
        line = []
        for x in range(cols):
            value, cover = pixels[x, y]
            if cover < 128:
                # off the subject entirely: leave the card dark
                line.append(" ")
                continue
            # light ink on a dark card, so a bright pixel is what earns a
            # dense glyph. anything on the subject gets at least the faintest
            # mark, which is what holds the silhouette together
            level = value / 255.0
            index = int(floor + level * (len(RAMP) - floor))
            line.append(RAMP[min(len(RAMP) - 1, index)])
        out.append("".join(line).rstrip())

    # the source is a circle crop with headroom on every side, so crop the
    # empty bands rather than padding the card out with nothing
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()

    inset = min((len(line) - len(line.lstrip()) for line in out if line.strip()), default=0)
    return [line[inset:] for line in out]


def build_svg(lines, font_size, cell_w, line_h, pad, ink, bg):
    width = round(max(len(line) for line in lines) * cell_w + pad * 2)
    height = round(len(lines) * line_h + pad * 2)

    per_row = 0.055
    body = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        y = pad + (index + 1) * line_h - line_h * 0.22
        delay = round(0.15 + index * per_row, 3)
        # textLength is per row, not the full card width: rows are ragged
        # right, and pinning them all to the same length would stretch the
        # short ones across the whole card and shear the character grid
        body.append(
            f'<text class="t" x="{pad}" y="{y:.1f}" '
            f'textLength="{len(line) * cell_w:.2f}" '
            f'lengthAdjust="spacingAndGlyphs" xml:space="preserve" '
            f'style="animation-delay:{delay}s">{escape(line)}</text>'
        )

    cursor_y = pad + len(lines) * line_h
    body.append(
        f'<rect class="cur" x="{pad}" y="{cursor_y - line_h * 0.78:.1f}" '
        f'width="{cell_w * 1.6:.1f}" height="{line_h * 0.9:.1f}" fill="{ink}"/>'
    )

    # animation-fill-mode backwards, and no opacity/clip in the base rules, so
    # the finished state is also the no-animation state. anywhere that freezes
    # or refuses CSS animation in an <img> still gets the whole portrait
    style = (
        ".t{animation:type .42s steps(30,end) backwards}"
        "@keyframes type{from{clip-path:inset(0 100% 0 0)}"
        "to{clip-path:inset(0 0 0 0)}}"
        ".cur{opacity:.55;animation:blink 1.1s steps(1,end) infinite}"
        "@keyframes blink{0%,50%{opacity:.55}50.01%,100%{opacity:0}}"
        "@media(prefers-reduced-motion:reduce){"
        ".t,.cur{animation:none}}"
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="{FONT}" role="img" '
        f'aria-label="ASCII portrait of Parth Rana">'
        f"<style>{style}</style>"
        f'<rect width="{width}" height="{height}" rx="10" fill="{bg}"/>'
        f'<g font-size="{font_size}" fill="{ink}">{"".join(body)}</g></svg>'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="assets/source-prepped.png")
    parser.add_argument("--out", default="assets/portrait.svg")
    parser.add_argument("--cols", type=int, default=104)
    parser.add_argument("--font-size", type=float, default=6.2)
    parser.add_argument("--pad", type=float, default=14)
    parser.add_argument("--ink", default="#c9d1d9")
    parser.add_argument("--bg", default="#0d1117")
    parser.add_argument("--floor", type=int, default=1,
                        help="lowest ramp index used on the subject")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    # monospace advance is ~0.6em; keeping line height at 1.0em means the
    # character grid is 0.6 wide by 1.0 tall, so a square photo needs
    # 0.6 * cols rows to come out square rather than stretched
    cell_w = args.font_size * 0.6
    line_h = args.font_size
    rows = round(args.cols * 0.6)

    lines = to_rows(args.src, args.cols, rows, args.floor)

    if args.preview:
        print("\n".join(lines))
        return

    svg = build_svg(
        lines, args.font_size, cell_w, line_h, args.pad, args.ink, args.bg
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg + "\n")
    print(f"wrote {out} ({args.cols}x{rows} chars, {len(svg) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
