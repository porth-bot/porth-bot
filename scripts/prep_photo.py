#!/usr/bin/env python3
"""Turn a headshot into a clean grayscale plate for ASCII conversion.

The conversion downstream maps dark pixels to dense characters, so the goal
here is: subject holding all the tone, background pushed to pure white (which
becomes empty space). Anything left in between reads as noise in the portrait
- the lettering on the backdrop of the source photo especially.

Isolation is deliberately dumb and self-contained rather than a segmentation
model: find the large dark blobs (hair, suit), throw away the small ones (the
backdrop text), then fill the horizontal span between them row by row so the
face and neck come along with the silhouette.

    python scripts/prep_photo.py assets/source-photo.jpg
"""

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

WORK = 300  # isolation runs on a downscaled copy, then the mask is scaled back


def components(mask):
    """4-connected labels for a boolean array, as (labels, sizes)."""
    height, width = mask.shape
    labels = np.zeros((height, width), dtype=np.int32)
    sizes = [0]
    current = 0
    for sy in range(height):
        for sx in range(width):
            if not mask[sy, sx] or labels[sy, sx]:
                continue
            current += 1
            size = 0
            queue = deque([(sy, sx)])
            labels[sy, sx] = current
            while queue:
                y, x = queue.popleft()
                size += 1
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < height and 0 <= nx < width:
                        if mask[ny, nx] and not labels[ny, nx]:
                            labels[ny, nx] = current
                            queue.append((ny, nx))
            sizes.append(size)
    return labels, np.array(sizes)


def silhouette(image, dark_level, min_blob, envelope):
    """Boolean subject mask at WORK resolution."""
    small = np.array(image.resize((WORK, WORK), Image.LANCZOS), dtype=np.uint8)
    labels, sizes = components(small < int(dark_level * 255))

    keep = np.where(sizes >= min_blob * WORK * WORK)[0]
    keep = keep[keep > 0]
    if keep.size == 0:
        return np.ones((WORK, WORK), dtype=bool)
    blobs = np.isin(labels, keep)

    # horizontal span per row, so the face between the hair and the collar is
    # carried along instead of being whited out with the backdrop
    rows = np.arange(WORK)
    filled = blobs.any(axis=1)
    if not filled.any():
        return np.ones((WORK, WORK), dtype=bool)

    left = np.full(WORK, np.nan)
    right = np.full(WORK, np.nan)
    for y in rows[filled]:
        cols = np.where(blobs[y])[0]
        left[y], right[y] = cols[0], cols[-1]

    # rows with no subject pixels (a bare neck) borrow a span from their
    # neighbours
    left = np.interp(rows, rows[filled], left[filled])
    right = np.interp(rows, rows[filled], right[filled])

    # then widen each row to the envelope of its neighbourhood. taking the raw
    # per-row span alone pinches to a sliver where the hair tapers out, and
    # interpolating from that sliver down to the collar slices the jaw and
    # neck clean off. the envelope keeps the head at head width all the way
    # down to the shoulders. over-covering costs nothing: what it pulls in is
    # background, and background is already white
    reach = int(WORK * envelope)
    lo = np.array([left[max(0, y - reach) : y + reach + 1].min() for y in rows])
    hi = np.array([right[max(0, y - reach) : y + reach + 1].max() for y in rows])

    grid = np.arange(WORK)[None, :]
    mask = (grid >= lo[:, None]) & (grid <= hi[:, None])
    # nothing above the crown
    mask[: int(rows[filled][0])] = False
    return mask


def backdrop(image, bright_level):
    """Bright pixels reachable from the frame edge, i.e. the actual backdrop.

    A plain brightness threshold cannot tell a white dress shirt from a white
    wall. Connectivity can: the wall runs to the edge of the frame, the shirt
    is fenced in by the suit.
    """
    small = np.array(image.resize((WORK, WORK), Image.LANCZOS), dtype=np.uint8)
    labels, _ = components(small >= int(bright_level * 255))

    border = set(labels[0]) | set(labels[-1]) | set(labels[:, 0]) | set(labels[:, -1])
    border.discard(0)
    if not border:
        return np.zeros((WORK, WORK), dtype=bool)
    return np.isin(labels, list(border))


def circle_fade(size, feather=0.03):
    """Alpha that goes to zero outside the inscribed circle."""
    axis = (np.arange(size) - (size - 1) / 2) / ((size - 1) / 2)
    distance = np.sqrt(axis[:, None] ** 2 + axis[None, :] ** 2)
    return np.clip((1.0 - distance) / feather, 0.0, 1.0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("photo")
    parser.add_argument("--out", default="assets/source-prepped.png")
    parser.add_argument("--size", type=int, default=900)
    parser.add_argument("--envelope", type=float, default=0.10)
    parser.add_argument("--isolate", action="store_true", default=True)
    parser.add_argument("--no-isolate", dest="isolate", action="store_false")
    parser.add_argument("--dark-level", type=float, default=0.42)
    parser.add_argument("--min-blob", type=float, default=0.02)
    parser.add_argument("--white-cut", type=float, default=0.80)
    parser.add_argument("--rim", type=int, default=3,
                        help="odd kernel; grows the backdrop to eat the antialiased edge")
    parser.add_argument("--highlight-knee", type=float, default=0.78)
    parser.add_argument("--highlight", type=float, default=0.5)
    parser.add_argument("--contrast", type=float, default=1.1)
    parser.add_argument("--gamma", type=float, default=1.5)
    args = parser.parse_args()

    image = Image.open(args.photo).convert("L")
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    image = image.resize((args.size, args.size), Image.LANCZOS)

    # knock the corners out first. the source is circle-cropped onto a near
    # black square, and those corners are dark enough to be mistaken for the
    # subject - they span the full width, so the row fill below would then
    # drag the whole backdrop back in with them
    alpha = circle_fade(args.size)
    image = Image.fromarray(
        np.clip(np.array(image, dtype=np.float32) * alpha + 255.0 * (1 - alpha), 0, 255)
        .astype(np.uint8)
    )

    if args.isolate:
        mask = silhouette(image, args.dark_level, args.min_blob, args.envelope)
        soft = Image.fromarray((mask * 255).astype(np.uint8))
        soft = soft.resize((args.size, args.size), Image.BILINEAR)
        soft = soft.filter(ImageFilter.GaussianBlur(args.size * 0.004))
        alpha = alpha * (np.array(soft, dtype=np.float32) / 255.0)

    plate = np.array(image, dtype=np.float32)
    plate = ImageOps.autocontrast(
        Image.fromarray(plate.astype(np.uint8)), cutoff=(1, 6)
    )
    plate = ImageEnhance.Contrast(plate).enhance(args.contrast)
    plate = plate.point([min(255, int(255 * ((i / 255) ** (1 / args.gamma)))) for i in range(256)])

    # squeeze the top end so a white dress shirt still lands one step above
    # empty, and the subject reads as a solid silhouette rather than a head
    # floating over a gap where the collar should be
    knee = int(args.highlight_knee * 255)
    tone = np.array(
        plate.point(
            [
                i if i < knee else int(knee + (i - knee) * args.highlight)
                for i in range(256)
            ]
        ),
        dtype=np.float32,
    )

    # hold the real backdrop at pure white, so the compression above does not
    # paint a halo wherever the envelope reached past the subject
    paper = Image.fromarray((backdrop(plate, args.white_cut) * 255).astype(np.uint8))
    # grow the backdrop a pixel before thresholding. the photo's own edge
    # antialiasing leaves a band of half-hair, half-wall grey that is too dark
    # to read as backdrop and too bright to read as hair, and on a dark card
    # that band would ring the whole silhouette in dense glyphs
    paper = paper.filter(ImageFilter.MaxFilter(args.rim))
    # thresholded, not feathered, for the same reason
    paper = np.array(paper.resize(plate.size, Image.BILINEAR)) >= 128
    tone[paper] = 255.0

    # keep the subject mask as alpha rather than baking it into the grey.
    # the ASCII step needs to tell "dark because it is hair" apart from "light
    # because there is nothing there", and on a dark card a bright pixel is
    # what deserves a dense glyph. flattening to grey throws that away
    # hard edge, and the cleared pixels go to black rather than white. the
    # ASCII step downsamples this plate, and blending a subject pixel toward a
    # white background would ring the silhouette in bright, dense glyphs
    solid = (alpha >= 0.5) & ~paper
    result = Image.merge(
        "LA",
        (
            Image.fromarray(np.where(solid, tone, 0.0).astype(np.uint8)),
            Image.fromarray((solid * 255).astype(np.uint8)),
        ),
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.save(out)
    print(f"wrote {out} ({result.width}x{result.height})")


if __name__ == "__main__":
    main()
