#!/usr/bin/env python3
"""Prep a photo for ASCII conversion -> photo/source-prepped.png

1. remove the background (rembg)            - isolates the subject
2. boost local contrast (OpenCV CLAHE)      - gives a flat-lit face real highlights and shadows
3. composite onto a plain backdrop          - white maps to the blank end of the ASCII ramp

Usage:
    python scripts/prep_photo.py photo/source-photo.jpg
    python scripts/prep_photo.py me.jpg --no-rembg          # keep the original background
    python scripts/prep_photo.py me.jpg --bg black          # pair with: make_ascii_svg.py --flip

Needs: pip install -r scripts/requirements-portrait.txt   (rembg / opencv fall back gracefully if missing)
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
from PIL import Image, ImageOps

from _common import PHOTO


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--bg", choices=("white", "black"), default="white")
    ap.add_argument("--no-rembg", action="store_true")
    ap.add_argument("--clip", type=float, default=3.0, help="CLAHE clip limit (higher = punchier)")
    args = ap.parse_args()

    img = ImageOps.exif_transpose(Image.open(args.src)).convert("RGB")
    gray = np.asarray(img.convert("L"))

    alpha = None
    if not args.no_rembg:
        try:
            from rembg import remove
            alpha = np.asarray(remove(img).split()[-1], dtype=np.float32) / 255.0
        except ImportError:
            print("rembg not installed - keeping the original background", file=sys.stderr)

    try:
        import cv2
        gray = cv2.createCLAHE(clipLimit=args.clip, tileGridSize=(8, 8)).apply(gray)
    except ImportError:
        print("opencv not installed - using plain histogram equalisation", file=sys.stderr)
        gray = np.asarray(ImageOps.equalize(Image.fromarray(gray)))

    backdrop = 255.0 if args.bg == "white" else 0.0
    out = gray.astype(np.float32)
    if alpha is not None:
        out = out * alpha + backdrop * (1.0 - alpha)

    PHOTO.mkdir(exist_ok=True)
    dest = PHOTO / "source-prepped.png"
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(dest)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
