#!/usr/bin/env python3
"""data/profile.json -> assets/info-card.svg (neofetch-style panel that prints line by line).

Edit the text in data/profile.json ("card" section), then re-run this script.
STATIC=1 python scripts/make_info_card.py    # frozen frame for previews
"""
from __future__ import annotations

import textwrap
from html import escape

from _common import (ACCENT, ASCII_COLS, ASCII_PAD, ASCII_ROWS, ASCII_SHOWN_W, ASSETS, BG, BORDER, CELL_H, CELL_W, FG,
                     GREEN, MONO, MUTED, STATIC, load_profile, write_text)

W = 490
BAR_H = 34
LINE_H = 19
KEY_X, VAL_X = 24, 118
WRAP = 48                 # characters per value line (monospace ~7.2px at 12px font)
# rendered height of the ASCII portrait, so the two panels line up side by side in the README
_asc_w, _asc_h = ASCII_COLS * CELL_W + 2 * ASCII_PAD, ASCII_ROWS * CELL_H + 2 * ASCII_PAD
MIN_H = round(_asc_h * ASCII_SHOWN_W / _asc_w)
SWATCHES = ["#ff5f56", "#ffbd2e", "#27c93f", "#58a6ff", "#d2a8ff", "#ffa657", "#7ee787", "#c9d1d9"]


BULLET_INDENT = 14        # px between the bullet and the wrapped text


def wrap_item(text: str, width: int) -> list[str]:
    return textwrap.wrap(text, width, break_on_hyphens=False, break_long_words=False) or [""]


def build(profile: dict) -> str:
    card = profile["card"]
    # (key on a row's first line, bullet on this line?, indented?, text)
    lines: list[tuple[str | None, bool, bool, str]] = []
    for row in card["rows"]:
        is_list = isinstance(row["value"], list)
        first = True
        for v in row["value"] if is_list else [row["value"]]:
            for j, text in enumerate(wrap_item(v, WRAP - 2 if is_list else WRAP)):
                lines.append((row["key"] if first else None, is_list and j == 0, is_list, text))
                first = False

    y = BAR_H + 34
    host_y = y
    y += LINE_H
    dash_y = y
    y += LINE_H + 2
    body_y0 = y
    swatch_y = body_y0 + len(lines) * LINE_H + 8
    H = max(MIN_H, swatch_y + 12 + 22)

    out: list[str] = []
    a = out.append
    a('<?xml version="1.0" encoding="UTF-8"?>')
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">')
    a(f"<title id=\"t\">{escape(profile['name'])} - profile card</title>")
    a("<style>")
    a(f"text{{font-family:{MONO};font-size:12px;fill:{FG};white-space:pre}}")
    a(f".k{{fill:{ACCENT};font-weight:700}} .m{{fill:{MUTED}}} .h{{fill:{GREEN};font-weight:700}}")
    a(".l{animation:in .45s ease-out both}")
    a("@keyframes in{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}")
    a("@media (prefers-reduced-motion:reduce){.l{animation:none}}")
    a("</style>")
    a(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>')
    a(f'<line x1="1" y1="{BAR_H}" x2="{W - 1}" y2="{BAR_H}" stroke="{BORDER}"/>')
    for i, colour in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        a(f'<circle cx="{20 + i * 18}" cy="{BAR_H / 2}" r="5.5" fill="{colour}"/>')
    a(f'<text x="{W / 2}" y="{BAR_H / 2 + 4}" text-anchor="middle" class="m">{escape(card["title"])}</text>')

    def delay(i: int) -> str:
        return "" if STATIC else f' style="animation-delay:{0.25 + i * 0.09:.2f}s"'

    cls = "" if STATIC else " l"
    step = 0
    host = card["host"]
    a(f'<text x="{KEY_X}" y="{host_y}" class="h{cls}"{delay(step)}>{escape(host)}</text>')
    step += 1
    a(f'<text x="{KEY_X}" y="{dash_y}" class="m{cls}"{delay(step)}>{"-" * len(host)}</text>')
    step += 1

    for i, (key, bullet, indented, text) in enumerate(lines):
        ly = body_y0 + i * LINE_H
        if key:
            a(f'<text x="{KEY_X}" y="{ly}" class="k{cls}"{delay(step)}>{escape(key)}<tspan class="m" font-weight="400">:</tspan></text>')
        if bullet:
            a(f'<text x="{VAL_X}" y="{ly}" class="m{cls}"{delay(step)}>›</text>')
        x = VAL_X + (BULLET_INDENT if indented else 0)
        a(f'<text x="{x}" y="{ly}" class="{cls.strip()}"{delay(step)}>{escape(text)}</text>')
        step += 1

    for i, colour in enumerate(SWATCHES):
        a(f'<rect x="{KEY_X + i * 20}" y="{swatch_y}" width="16" height="16" rx="3" fill="{colour}" class="{cls.strip()}"{delay(step)}/>')
    a("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    write_text(ASSETS / "info-card.svg", build(load_profile()))


if __name__ == "__main__":
    main()
