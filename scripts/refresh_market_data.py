#!/usr/bin/env python3
"""
Rebuilds the `const MARKETS = {...}` block in auto-markets-by-country.html
from the current contents of the world_auto_sales_annual Supabase table.

Run this any time world_auto_sales_annual changes (new YTD figures, a
recomputed 2026 projection, a backfill, etc.) so the static site's baked-in
data stays in sync with the database. Safe to re-run any number of times —
it's a full rebuild, not an incremental patch.

Usage:
    python scripts/refresh_market_data.py

Only touches auto-markets-by-country.html. It does not regenerate
world-auto-sales.html or powertrain-mix-by-country.html — those pages use a
different baked-in data shape (monthly HIST arrays) and are not covered by
this script.
"""
import json
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

SUPABASE_PROJECT = "rtmlxvjpjxcvjdykrkvm"
SUPABASE_URL = f"https://{SUPABASE_PROJECT}.supabase.co"
# Legacy anon (public, read-only-by-RLS-policy) key — safe to keep in the repo,
# same key already used throughout this project's population scripts.
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0bWx4dmpwanhjdmpkeWtya3ZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcwNzY1NDYsImV4cCI6MjEwMjY1MjU0Nn0."
    "yxV9iE9xP4MZnMnZOPupKr2_eyRo-_jGoT5lTTnHS14"
)
PAGE_SIZE = 1000
REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_HTML = REPO_ROOT / "auto-markets-by-country.html"

# OICA first (most globally standardized, present for nearly every country),
# else the alphabetically-first remaining source — keeps the output a single
# clean series even though the DB intentionally keeps multiple sources per
# (country, year) for cross-verification.
SOURCE_PRIORITY = ["OICA"]


def fetch_all_rows():
    rows = []
    offset = 0
    while True:
        url = (
            f"{SUPABASE_URL}/rest/v1/world_auto_sales_annual"
            f"?select=year,country,country_abbr,continent,total_units,source,period_type"
            f"&order=id.asc&offset={offset}&limit={PAGE_SIZE}"
        )
        req = urllib.request.Request(
            url,
            headers={"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            page = json.load(resp)
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def pick(rows_for_year):
    for pref in SOURCE_PRIORITY:
        for src, val in rows_for_year:
            if src == pref and val is not None:
                return val
    remaining = sorted((src, val) for src, val in rows_for_year if val is not None)
    return remaining[0][1] if remaining else None


def esc(s):
    if s is None:
        return "null"
    s = str(s).replace("\\", "\\\\").replace('"', '\\"')
    return '"' + s + '"'


def build_markets_js(rows):
    by_country_year = defaultdict(dict)
    projected = defaultdict(dict)
    meta = {}
    for r in rows:
        c = r["country"]
        if c not in meta:
            meta[c] = {"abbr": r["country_abbr"], "continent": r["continent"]}
        if r["period_type"] == "PROJECTED":
            projected[c][r["year"]] = r["total_units"]
        else:
            by_country_year[c].setdefault(r["year"], []).append((r["source"], r["total_units"]))

    countries = sorted(set(list(by_country_year.keys()) + list(projected.keys())))

    lines = ["const MARKETS = {"]
    for c in countries:
        years_map = by_country_year.get(c, {})
        pairs = []
        for y in sorted(years_map.keys()):
            v = pick(years_map[y])
            if v is not None:
                pairs.append((y, v))
        series = ",".join('"%d":%d' % (y, v) for y, v in pairs)
        proj = projected.get(c, {})
        proj_str = ",".join('"%d":%d' % (y, v) for y, v in sorted(proj.items()))
        m = meta[c]
        lines.append(
            "%s:{abbr:%s,continent:%s,series:{%s},projected:{%s}},"
            % (esc(c), esc(m["abbr"]), esc(m["continent"]), series, proj_str)
        )
    lines.append("};")
    return "\n".join(lines), len(countries), len(projected)


def splice_into_html(markets_js):
    text = TARGET_HTML.read_text(encoding="utf-8")
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l == "const MARKETS = {")
    end = next(i for i in range(start, len(lines)) if lines[i] == "};")
    new_lines = lines[:start] + markets_js.split("\n") + lines[end + 1 :]
    TARGET_HTML.write_text("\n".join(new_lines), encoding="utf-8", newline="\n")


def main():
    rows = fetch_all_rows()
    if len(rows) < 1000:
        print(f"ERROR: only fetched {len(rows)} rows — pagination likely broken, aborting without writing.", file=sys.stderr)
        sys.exit(1)
    markets_js, n_countries, n_projected = build_markets_js(rows)
    splice_into_html(markets_js)
    print(f"OK: {len(rows)} rows fetched, {n_countries} countries, {n_projected} with a 2026 projection.")
    print(f"Wrote {TARGET_HTML}")


if __name__ == "__main__":
    main()
