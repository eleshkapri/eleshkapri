"""Shared paths, palette and helpers for the profile-art scripts."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
PHOTO = ROOT / "photo"

# System monospace stack: SVGs rendered through <img> cannot load web fonts.
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace"

BG = "#0d1117"
BORDER = "#30363d"
FG = "#c9d1d9"
MUTED = "#8b949e"
ACCENT = "#58a6ff"
GREEN = "#7ee787"
ORANGE = "#ffa657"
PURPLE = "#d2a8ff"

STATIC = os.environ.get("STATIC") == "1"  # frozen final frame, handy for previews

# ASCII portrait grid + the widths README.md displays the SVGs at. The info card reads these to
# match the portrait's rendered height, so change them in one place.
ASCII_COLS, ASCII_ROWS = 100, 74
CELL_W, CELL_H = 3.8, 6.4                     # glyph cell in SVG px (roughly 1 : 1.7)
ASCII_PAD = 10
ASCII_SHOWN_W = 370                           # <img width> in README.md


def load_profile() -> dict:
    return json.loads((DATA / "profile.json").read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {path.relative_to(ROOT)} ({len(text.encode('utf-8')) / 1024:.1f} KB)")
