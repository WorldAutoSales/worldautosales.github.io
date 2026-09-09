#!/usr/bin/env python3
"""
Rebuilds `const MANUFACTURER_YEARLY = {...}` in assets/manufacturer-yearly-data.js
from the current contents of sales_manufacturer_country_year (Germany + Canada).

Run this any time that table changes for either country (a data fix, a new
brand, a new year). Safe to re-run any number of times -- full rebuild.

Usage:
    python scripts/refresh_manufacturer_data.py
"""
import json
import sys
import urllib.request
from pathlib import Path

SUPABASE_PROJECT = "rtmlxvjpjxcvjdykrkvm"
SUPABASE_URL = f"https://{SUPABASE_PROJECT}.supabase.co"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0bWx4dmpwanhjdmpkeWtya3ZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcwNzY1NDYsImV4cCI6MjEwMjY1MjU0Nn0."
    "yxV9iE9xP4MZnMnZOPupKr2_eyRo-_jGoT5lTTnHS14"
)
PAGE_SIZE = 1000
REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_JS = REPO_ROOT / "assets" / "manufacturer-yearly-data.js"
TABLE = "sales_manufacturer_country_year"
COUNTRIES = ["Germany", "Canada"]

COLUMNS = "year,brand,nb_bev,nb_phev,nb_hev,nb_petrol,nb_diesel"


def fetch_country_rows(country):
    rows = []
    offset = 0
    while True:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{TABLE}?select={COLUMNS}&country=eq.{country}"
            f"&order=brand.asc,year.asc&limit={PAGE_SIZE}&offset={offset}",
            headers={"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"},
        )
        with urllib.request.urlopen(req) as resp:
            batch = json.loads(resp.read())
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def build_rows(raw_rows):
    out = []
    for r in raw_rows:
        bev = r["nb_bev"] or 0
        phev = r["nb_phev"] or 0
        hev = r["nb_hev"] or 0
        petrol = r["nb_petrol"] or 0
        diesel = r["nb_diesel"] or 0
        total = bev + phev + hev + petrol + diesel
        if total <= 0:
            continue
        out.append({
            "year": r["year"], "brand": r["brand"],
            "bev": bev, "phev": phev, "hev": hev, "petrol": petrol, "diesel": diesel,
            "total": total,
        })
    return out


def main():
    data = {}
    for country in COUNTRIES:
        raw = fetch_country_rows(country)
        if not raw:
            print(f"ERROR: 0 rows fetched for {country} -- aborting without writing.", file=sys.stderr)
            sys.exit(1)
        data[country] = build_rows(raw)

    body = json.dumps(data, separators=(",", ":"), ensure_ascii=True)
    TARGET_JS.write_text(f"const MANUFACTURER_YEARLY = {body};\n", encoding="utf-8", newline="\n")

    for country in COUNTRIES:
        brands = {r["brand"] for r in data[country]}
        print(f"OK: {country} -- {len(data[country])} rows, {len(brands)} brands.")
    print(f"Wrote {TARGET_JS}")


if __name__ == "__main__":
    main()
