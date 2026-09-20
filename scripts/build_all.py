#!/usr/bin/env python3
"""Regenerate everything: python scripts/build_all.py [--offline]

--offline skips the network fetch and re-renders from the existing data/contributions.json.
"""
import subprocess
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
steps = ["make_ascii_svg.py", "make_info_card.py"]
for s in steps:
    print(f"\n$ {s}")
    subprocess.run([sys.executable, str(here / s)], check=True)
