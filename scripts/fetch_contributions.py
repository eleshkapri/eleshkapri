#!/usr/bin/env python3
"""Fetch your public contribution calendar (no token needed) -> data/contributions.json.

GitHub serves the calendar as an HTML fragment at
https://github.com/users/<username>/contributions (the same one the profile page uses).

Usage:
    python scripts/fetch_contributions.py [username]

Username resolution: CLI arg > $GH_USER > data/profile.json.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

from _common import DATA, load_profile, write_text

URL = "https://github.com/users/{user}/contributions"


def resolve_user() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    return os.environ.get("GH_USER") or load_profile()["username"]


def fetch_html(user: str) -> str:
    headers = {
        "User-Agent": f"Mozilla/5.0 (profile-readme-art; +https://github.com/{user})",
        "Accept": "text/html",
    }
    last_err = None
    for attempt in range(4):
        try:
            r = requests.get(URL.format(user=user), headers=headers, timeout=30)
            if r.status_code == 200 and "ContributionCalendar-day" in r.text:
                return r.text
            last_err = f"HTTP {r.status_code}"
        except requests.RequestException as e:  # network hiccup
            last_err = str(e)
        time.sleep(2 ** attempt)
    raise SystemExit(f"could not fetch contributions for {user!r}: {last_err}")


def parse(html: str) -> tuple[list[list], int | None]:
    soup = BeautifulSoup(html, "html.parser")

    # Day counts live in the <tool-tip> that points at each cell via its `for` attribute.
    tips = {t.get("for"): t.get_text(" ", strip=True) for t in soup.select("tool-tip")}

    days: list[list] = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        tip = tips.get(td.get("id"), "")
        m = re.match(r"([\d,]+)\s+contribution", tip)
        count = int(m.group(1).replace(",", "")) if m else 0
        days.append([td["data-date"], count, int(td.get("data-level", 0))])
    days.sort(key=lambda d: d[0])

    header_total = None
    m = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", soup.get_text(" ", strip=True))
    if m:
        header_total = int(m.group(1).replace(",", ""))
    return days, header_total


def compute_stats(days: list[list]) -> dict:
    total = sum(d[1] for d in days)

    longest = (0, None, None)
    run, start = 0, None
    for date, count, _ in days:
        if count > 0:
            if run == 0:
                start = date
            run += 1
            if run > longest[0]:
                longest = (run, start, date)
        else:
            run = 0

    # Current streak: today may simply not have a contribution *yet*, so skip it if empty.
    i = len(days) - 1
    if days[i][1] == 0:
        i -= 1
    current = 0
    while i >= 0 and days[i][1] > 0:
        current += 1
        i -= 1

    best = max(days, key=lambda d: d[1])
    monthly: dict[str, int] = {}
    for date, count, _ in days:
        monthly[date[:7]] = monthly.get(date[:7], 0) + count

    return {
        "total": total,
        "active_days": sum(1 for d in days if d[1] > 0),
        "current_streak": current,
        "longest_streak": {"days": longest[0], "start": longest[1], "end": longest[2]},
        "best_day": {"date": best[0], "count": best[1]},
        "monthly": monthly,
    }


def main() -> None:
    user = resolve_user()
    days, header_total = parse(fetch_html(user))
    if len(days) < 300:  # a full year is ~365 cells; refuse to overwrite good data with a bad scrape
        raise SystemExit(f"only parsed {len(days)} day cells - GitHub's markup may have changed")

    payload = {
        "user": user,
        "generated": dt.date.today().isoformat(),  # date only, so same-day reruns don't churn git
        "from": days[0][0],
        "to": days[-1][0],
        "header_total": header_total,
        **compute_stats(days),
    }
    if header_total is not None and header_total != payload["total"]:
        print(f"note: summed {payload['total']} vs page header {header_total}", file=sys.stderr)

    # one day per line keeps git diffs readable
    head = json.dumps(payload, indent=2)[:-2]
    body = ",\n".join("    " + json.dumps(d, separators=(",", ":")) for d in days)
    write_text(DATA / "contributions.json", head + ',\n  "days": [\n' + body + "\n  ]\n}\n")
    print(f"{user}: {payload['total']} contributions, current streak {payload['current_streak']}d")


if __name__ == "__main__":
    main()
