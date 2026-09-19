#!/usr/bin/env python3
"""data/contributions.json -> assets/contrib-heatmap.svg (53-week grid that slides in once).

STATIC=1 python scripts/render_heatmap_svg.py   # frozen frame for previews
"""
from __future__ import annotations

import datetime as dt
import json
from html import escape

from _common import (ASSETS, BG, BORDER, DATA, FG, MONO, MUTED, STATIC, load_profile, write_text)

# GitHub's dark-mode ramp, one colour per data-level (0..4)
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

W = 860
LEFT, RIGHT = 46, 20
BAR_H = 34           # fake window title bar
GRID_TOP = 62        # first row of cells
GAP = 3.2
STEP = 0.011         # seconds of delay per diagonal step


def nice(date_iso: str) -> str:
    d = dt.date.fromisoformat(date_iso)
    return f"{d.strftime('%b')} {d.day}"


def build(data: dict) -> str:
    profile = load_profile()
    days = [(dt.date.fromisoformat(d), c, l) for d, c, l in data["days"]]
    first = days[0][0]
    sunday0 = first - dt.timedelta(days=(first.weekday() + 1) % 7)   # calendar weeks start on Sunday
    n_weeks = (days[-1][0] - sunday0).days // 7 + 1

    pitch = (W - LEFT - RIGHT) / n_weeks
    cell = pitch - GAP
    grid_bottom = GRID_TOP + 7 * pitch
    foot_y = grid_bottom + 22
    H = round(foot_y + 20)

    out: list[str] = []
    a = out.append
    title = f"{data['total']:,} GitHub contributions in the last year by {data['user']}"
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t">')
    a(f"<title id=\"t\">{escape(title)}</title>")
    a("<style>")
    a(f"text{{font-family:{MONO};font-size:11px;fill:{MUTED}}}")
    a(".c{animation:pop .45s cubic-bezier(.2,.8,.2,1) both}")
    a(".f{animation:fade .7s ease-out both;animation-delay:1.3s}")
    a("@keyframes pop{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}")
    a("@keyframes fade{from{opacity:0}to{opacity:1}}")
    a("@media (prefers-reduced-motion:reduce){.c,.f{animation:none}}")
    a("</style>")
    a(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="{BG}" stroke="{BORDER}"/>')

    # title bar
    a(f'<line x1="1" y1="{BAR_H}" x2="{W - 1}" y2="{BAR_H}" stroke="{BORDER}"/>')
    for i, colour in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        a(f'<circle cx="{20 + i * 18}" cy="{BAR_H / 2}" r="5.5" fill="{colour}"/>')
    a(f'<text x="{W / 2}" y="{BAR_H / 2 + 4}" text-anchor="middle" style="fill:{FG}">'
      f'{escape(profile["prompt"])}: ~/contributions</text>')

    # month labels
    prev_month, last_col = None, -10
    for col in range(n_weeks):
        d = sunday0 + dt.timedelta(days=7 * col)
        if d.month != prev_month:
            if col - last_col >= 3 and LEFT + col * pitch + 26 < W - 8:   # skip labels that would clip
                a(f'<text x="{LEFT + col * pitch:.1f}" y="{GRID_TOP - 8}">{d.strftime("%b")}</text>')
                last_col = col
            prev_month = d.month

    # weekday labels
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        a(f'<text x="{LEFT - 8}" y="{GRID_TOP + row * pitch + cell * 0.82:.1f}" text-anchor="end">{label}</text>')

    # cells
    for d, count, level in days:
        col = (d - sunday0).days // 7
        row = (d.weekday() + 1) % 7
        x = LEFT + col * pitch
        y = GRID_TOP + row * pitch
        style = "" if STATIC else f' class="c" style="animation-delay:{(col + row) * STEP:.3f}s"'
        a(f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell:.2f}" height="{cell:.2f}" rx="2.6" '
          f'fill="{PALETTE[min(level, 4)]}"{style}/>')

    # footer: stats on the left, legend on the right
    streak = data["longest_streak"]["days"]
    stats = (f"{data['total']:,} contributions in the last year  ·  current streak {data['current_streak']}d  ·  "
             f"longest {streak}d  ·  best day {data['best_day']['count']} ({nice(data['best_day']['date'])})")
    foot_cls = "" if STATIC else ' class="f"'
    a(f'<g{foot_cls}>')
    a(f'<text x="{LEFT}" y="{foot_y:.1f}">{escape(stats)}</text>')
    x_right = W - RIGHT
    a(f'<text x="{x_right}" y="{foot_y:.1f}" text-anchor="end">More</text>')
    box, bgap = 11, 3
    boxes_end = x_right - 34
    boxes_start = boxes_end - (5 * box + 4 * bgap)
    for i, colour in enumerate(PALETTE):
        a(f'<rect x="{boxes_start + i * (box + bgap)}" y="{foot_y - 10:.1f}" width="{box}" height="{box}" rx="2.4" fill="{colour}"/>')
    a(f'<text x="{boxes_start - 6}" y="{foot_y:.1f}" text-anchor="end">Less</text>')
    a("</g>")
    a("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    data = json.loads((DATA / "contributions.json").read_text(encoding="utf-8"))
    write_text(ASSETS / "contrib-heatmap.svg", build(data))


if __name__ == "__main__":
    main()
