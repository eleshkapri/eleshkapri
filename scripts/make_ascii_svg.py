#!/usr/bin/env python3
"""Photo (or wordmark) -> one-colour ASCII art SVG that prints itself row by row.

Source priority:
    --text / --image / --avatar flags
    photo/source-prepped.png      (output of prep_photo.py - best results)
    photo/source-photo.*          (raw photo, converted as-is)
    fallback wordmark from data/profile.json ("ESK"), so the README works out of the box

Examples:
    python scripts/make_ascii_svg.py
    python scripts/make_ascii_svg.py --avatar          # your public GitHub avatar
    python scripts/make_ascii_svg.py --image me.jpg --flip
    STATIC=1 python scripts/make_ascii_svg.py          # frozen frame for previews
"""
from __future__ import annotations

import argparse
import io
from html import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from _common import (ASCII_COLS as COLS, ASCII_PAD as PAD, ASCII_ROWS as ROWS, ASSETS, BG, BORDER, CELL_H, CELL_W,
                     MONO, PHOTO, STATIC, load_profile, write_text)

GRID_W, GRID_H = COLS * CELL_W, ROWS * CELL_H
SVG_W, SVG_H = round(GRID_W + 2 * PAD), round(GRID_H + 2 * PAD)
INK = "#b8c2cc"                          # single light-grey fill: monochrome on purpose

RAMP = " .`:-=+*cs#%@"                   # bright (sparse) -> dark (dense); leading space clears the background

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "DejaVuSans-Bold.ttf",
]


def get_font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)   # Pillow >= 10.1


def render_wordmark(text: str) -> Image.Image:
    """Big bold text + an underscore cursor inside a thin frame, in the character grid's aspect ratio."""
    w = 1520
    h = round(w * GRID_H / GRID_W)
    img = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(img)

    # thin rounded frame (renders as a ring of mid-weight glyphs)
    inset = 70
    d.rounded_rectangle((inset, inset, w - inset, h - inset), radius=90, outline=120, width=22)

    # largest size at which text + cursor fit in ~76% of the width
    size = 700
    while size > 40:
        font = get_font(size)
        l, t, r, b = d.textbbox((0, 0), text, font=font)
        if (r - l) + size * 0.46 <= w * 0.76:
            break
        size -= 10
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    cap_h = b - t
    total_w = (r - l) + size * 0.46
    x0 = (w - total_w) / 2
    y0 = h / 2 - cap_h / 2
    d.text((x0 - l, y0 - t), text, font=font, fill=0)
    cx = x0 + (r - l) + size * 0.10          # terminal-style underscore cursor: reads "ESK_"
    d.rectangle((cx, y0 + cap_h * 0.86, cx + size * 0.36, y0 + cap_h), fill=0)
    return img


def load_source(args, profile: dict) -> tuple[Image.Image, bool]:
    """Returns (image, is_photo)."""
    if args.text:
        return render_wordmark(args.text), False
    if args.image:
        return Image.open(args.image), True
    if args.avatar:
        import requests
        r = requests.get(f"https://github.com/{profile['username']}.png?size=460", timeout=30)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)), True
    prepped = PHOTO / "source-prepped.png"
    if prepped.exists():
        return Image.open(prepped), True
    raws = sorted(PHOTO.glob("source-photo.*"))
    if raws:
        print("using the raw photo; run scripts/prep_photo.py first for a much cleaner result")
        return Image.open(raws[0]), True
    text = profile.get("ascii", {}).get("fallback_text", profile["name"][:3].upper())
    return render_wordmark(text), False


def to_grayscale(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA") or "transparency" in img.info:
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, rgba)
    return img.convert("L")


def cover_crop(img: Image.Image, focus_y: float) -> Image.Image:
    target = GRID_W / GRID_H
    w, h = img.size
    if w / h > target:                      # too wide: trim the sides
        new_w = round(h * target)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = round(w / target)               # too tall: trim top/bottom, biased towards the face
    top = round((h - new_h) * focus_y)
    return img.crop((0, top, w, top + new_h))


def to_indices(img: Image.Image, is_photo: bool, flip: bool) -> np.ndarray:
    img = cover_crop(to_grayscale(img), focus_y=0.30 if is_photo else 0.5)
    img = img.resize((COLS, ROWS), Image.LANCZOS)
    a = np.asarray(img, dtype=np.float32) / 255.0

    if is_photo:                            # stretch contrast over the subject only (ignore white backdrop)
        subject = a < 0.97
        if subject.sum() > 50:
            lo, hi = np.percentile(a[subject], [2, 98])
            a = np.where(subject, np.clip((a - lo) / max(hi - lo, 1e-3), 0, 1), 1.0)

    a = np.where(a > 0.93, 1.0, a)          # near-white -> blank, so no speckle in the background
    ink = a if flip else 1.0 - a            # default: dark pixels get dense glyphs
    return np.rint(ink * (len(RAMP) - 1)).astype(int)


def build_svg(rows: list[str]) -> str:
    out: list[str] = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}" role="img" aria-label="ASCII portrait">')
    a("<title>ASCII portrait</title>")
    a("<style>")
    a(f".g{{font-family:{MONO};font-size:6.1px;fill:{INK};white-space:pre}}")
    a("</style>")
    a(f'<rect x="0.5" y="0.5" width="{SVG_W - 1}" height="{SVG_H - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>')

    for r, row in enumerate(rows):
        s = row.rstrip()
        if not s.strip():
            continue
        lead = len(s) - len(s.lstrip())
        seg = s[lead:]
        x = PAD + lead * CELL_W
        top = PAD + r * CELL_H
        base = top + CELL_H - 1.3
        length = len(seg) * CELL_W
        text = (f'<text class="g" x="{x:.2f}" y="{base:.2f}" textLength="{length:.2f}" '
                f'lengthAdjust="spacing" xml:space="preserve"')
        if STATIC:
            a(f"{text}>{escape(seg)}</text>")
            continue

        begin, dur = 0.3 + r * 0.05, 0.55
        a(f'<clipPath id="c{r}"><rect x="{PAD}" y="{top - 0.5:.2f}" width="0" height="{CELL_H + 1}">'
          f'<animate attributeName="width" from="0" to="{GRID_W:.1f}" begin="{begin:.2f}s" dur="{dur}s" fill="freeze"/></rect></clipPath>')
        a(f'{text} clip-path="url(#c{r})">{escape(seg)}</text>')
        a(f'<rect x="{PAD}" y="{top + 0.4:.2f}" width="{CELL_W * 0.8:.2f}" height="{CELL_H - 1.4:.2f}" fill="#e6edf3" opacity="0">'
          f'<animate attributeName="x" from="{PAD}" to="{PAD + GRID_W:.1f}" begin="{begin:.2f}s" dur="{dur}s" fill="freeze"/>'
          f'<animate attributeName="opacity" values="0;.9;.9;0" keyTimes="0;.05;.95;1" begin="{begin:.2f}s" dur="{dur}s" fill="freeze"/></rect>')
    a("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", help="path to an image to convert")
    ap.add_argument("--avatar", action="store_true", help="download your public GitHub avatar and convert it")
    ap.add_argument("--text", help="render this text as a big wordmark instead of a photo")
    ap.add_argument("--flip", action="store_true", help="bright pixels get dense glyphs (use with a black-background prep)")
    args = ap.parse_args()

    profile = load_profile()
    img, is_photo = load_source(args, profile)
    idx = to_indices(img, is_photo, args.flip)
    rows = ["".join(RAMP[i] for i in row) for row in idx]
    write_text(ASSETS / "ascii.svg", build_svg(rows))


if __name__ == "__main__":
    main()
