#!/usr/bin/env python3
"""
Rebuilds `assets/canada-province-data.js` (`const CANADA_PROVINCE_MONTHLY = [...]`)
from the current contents of the canada_province_powertrain_monthly Supabase table.

Run this any time that table changes. Safe to re-run any number of times --
it's a full rebuild, not an incremental patch.

Usage:
    python scripts/refresh_canada_province_data.py
"""
import json
import sys
import urllib.request
from pathlib import Path

SUPABASE_PROJECT = "rtmlxvjpjxcvjdykrkvm"
SUPABASE_URL = f"https://{SUPABASE_PROJECT}.supabase.co"
# Legacy anon (public, read-only-by-RLS-policy) key -- safe to keep in the repo,
# same key already used throughout this project's population scripts.
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0bWx4dmpwanhjdmpkeWtya3ZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcwNzY1NDYsImV4cCI6MjEwMjY1MjU0Nn0."
    "yxV9iE9xP4MZnMnZOPupKr2_eyRo-_jGoT5lTTnHS14"
)
PAGE_SIZE = 1000
REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_JS = REPO_ROOT / "assets" / "canada-province-data.js"
TABLE = "canada_province_powertrain_monthly"

COLUMNS = "year_month,year,province,province_abbr,bev,phev,hev,petrol,diesel,others,total"


def fetch_all_rows():
    rows = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{TABLE}?select={COLUMNS}&order=province.asc,year_month.asc"
            f"&limit={PAGE_SIZE}&offset={offset}",
            headers={"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"},
        )
        with urllib.request.urlopen(req) as resp:
            batch = json.loads(resp.read())
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def build_js(rows):
    # compact array-of-arrays, one row per [year_month, province_abbr, bev, phev, hev, petrol, diesel, others, total]
    # province full name kept in a separate lookup so it's not repeated ~111x per province
    provinces = {}
    for r in rows:
        provinces.setdefault(r["province_abbr"] or r["province"], r["province"])

    lines = ["const CANADA_PROVINCE_NAMES = " + json.dumps(provinces, ensure_ascii=False, separators=(",", ":")) + ";"]
    lines.append("const CANADA_PROVINCE_MONTHLY = [")
    for r in rows:
        row = [
            r["year_month"], r["province_abbr"] or r["province"],
            r["bev"], r["phev"], r["hev"], r["petrol"], r["diesel"], r["others"], r["total"],
        ]
        lines.append(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + ",")
    lines.append("];")
    return "\n".join(lines) + "\n"


def main():
    rows = fetch_all_rows()
    if len(rows) < 500:
        print(f"ERROR: only fetched {len(rows)} rows -- pagination likely broken, aborting without writing.", file=sys.stderr)
        sys.exit(1)
    js = build_js(rows)
    TARGET_JS.write_text(js, encoding="utf-8", newline="\n")
    provinces = {r["province_abbr"] or r["province"] for r in rows}
    print(f"OK: {len(rows)} rows fetched, {len(provinces)} provinces/territories.")
    print(f"Wrote {TARGET_JS}")


if __name__ == "__main__":
    main()
