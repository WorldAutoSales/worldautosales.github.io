#!/usr/bin/env python3
"""
Rebuilds `const MANUFACTURER_MODEL_MONTHLY = {...}` in assets/manufacturer-model-monthly-data.js
from the current contents of sales_manufacturer_country_model_month.

Companion to refresh_manufacturer_monthly_data.py (brand-level) -- same countries,
same date-range caps, but with model-level detail for the "By Model" toggle on the
Sales by Brand & Model section (individual-country.html / powertrain-mix-by-country.html).

Run this any time that table changes for a covered country (a data fix, a new
month, a newly added country) -- and always alongside the brand-level script, since
both feed the same site section. Safe to re-run any number of times -- full rebuild.

Usage:
    python scripts/refresh_manufacturer_model_monthly_data.py
"""
import json
import sys
import urllib.parse
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
TARGET_JS = REPO_ROOT / "assets" / "manufacturer-model-monthly-data.js"
TABLE = "sales_manufacturer_country_model_month"
# Keep in sync with refresh_manufacturer_monthly_data.py's COUNTRIES/MIN_YEAR_MONTH.
COUNTRIES = ["Canada", "United States", "Germany"]
MIN_YEAR_MONTH = {"Germany": "2026-01"}

COLUMNS = "year_month,brand,model,nb_bev,nb_phev,nb_hev,nb_petrol,nb_diesel"


def fetch_country_rows(country, min_year_month=None):
    rows = []
    offset = 0
    while True:
        min_filter = f"&year_month=gte.{min_year_month}" if min_year_month else ""
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{TABLE}?select={COLUMNS}&country=eq.{urllib.parse.quote(country)}"
            f"{min_filter}"
            f"&order=year_month.asc,brand.asc,model.asc&limit={PAGE_SIZE}&offset={offset}",
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
            "year_month": r["year_month"], "brand": r["brand"], "model": r["model"],
            "bev": bev, "phev": phev, "hev": hev, "petrol": petrol, "diesel": diesel,
            "total": total,
        })
    return out


def main():
    data = {}
    for country in COUNTRIES:
        raw = fetch_country_rows(country, MIN_YEAR_MONTH.get(country))
        if not raw:
            print(f"ERROR: 0 rows fetched for {country} -- aborting without writing.", file=sys.stderr)
            sys.exit(1)
        data[country] = build_rows(raw)

    body = json.dumps(data, separators=(",", ":"), ensure_ascii=True)
    TARGET_JS.write_text(f"const MANUFACTURER_MODEL_MONTHLY = {body};\n", encoding="utf-8", newline="\n")

    for country in COUNTRIES:
        months = {r["year_month"] for r in data[country]}
        models = {(r["brand"], r["model"]) for r in data[country]}
        print(f"OK: {country} -- {len(data[country])} rows, {len(months)} months, {len(models)} brand+model pairs.")
    print(f"Wrote {TARGET_JS}")


if __name__ == "__main__":
    main()
