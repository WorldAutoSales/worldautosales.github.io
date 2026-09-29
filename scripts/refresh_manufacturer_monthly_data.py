#!/usr/bin/env python3
"""
Rebuilds `const MANUFACTURER_MONTHLY = {...}` in assets/manufacturer-monthly-data.js
from the current contents of sales_manufacturer_country_month.

Unlike sales_manufacturer_country_year (annual, feeds manufacturer-yearly-data.js),
this table holds real single-month brand-level sales for markets where a genuine
monthly source exists (currently just Canada, via BestSellingCarsBlog/DesRosiers).

Run this any time that table changes for a covered country (a data fix, a new
month, a newly added country). Safe to re-run any number of times -- full rebuild.

Usage:
    python scripts/refresh_manufacturer_monthly_data.py
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
TARGET_JS = REPO_ROOT / "assets" / "manufacturer-monthly-data.js"
TABLE = "sales_manufacturer_country_month"
# Germany's KBA data goes back to 2008 -- this page's month picker is meant for a
# short list of recent months (unlike the full-history annual view on manufacturers.html,
# which is untouched), so Germany is capped to 2026 onward to keep the payload sane.
# Panama: ADAP publishes no fuel split at all -- its units sit in nb_others and are
# exported as "others" (powertrain unknown), never folded into petrol.
# France is deliberately NOT in this list. Its real Jan-Aug 2026 monthly data (PFA/AAA
# DATA) lives only in this JS asset -- sales_manufacturer_country_month never had more
# than a single stray month for France -- so running this script with France included
# regenerates the file FROM that near-empty DB slice and silently wipes 7 of 8 real
# months (this happened once already, 2026-09-23, merge commit 164ab7e; restored
# 2026-09-29 from the last good pre-clobber commit, c9b76b8). Matches the same
# DB-bypassed convention already established for France's/Germany's *yearly* model
# data -- see [[project_world_auto_sales]]/[[feedback_shared_repo_git_caution]]. Do not
# add "France" back here unless its monthly data is first fully loaded into
# sales_manufacturer_country_month/_model_month to match.
COUNTRIES = ["Canada", "United States", "Germany", "Japan", "Spain", "Panama"]
MIN_YEAR_MONTH = {"Germany": "2026-01"}

COLUMNS = "year_month,brand,nb_bev,nb_phev,nb_hev,nb_petrol,nb_diesel,nb_others"


def fetch_country_rows(country, min_year_month=None):
    rows = []
    offset = 0
    while True:
        min_filter = f"&year_month=gte.{min_year_month}" if min_year_month else ""
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{TABLE}?select={COLUMNS}&country=eq.{urllib.parse.quote(country)}"
            f"{min_filter}"
            f"&order=year_month.asc,brand.asc&limit={PAGE_SIZE}&offset={offset}",
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
        others = r.get("nb_others") or 0
        total = bev + phev + hev + petrol + diesel + others
        if total <= 0:
            continue
        row = {
            "year_month": r["year_month"], "brand": r["brand"],
            "bev": bev, "phev": phev, "hev": hev, "petrol": petrol, "diesel": diesel,
            "total": total,
        }
        if others:  # only emitted where a source has no fuel split, keeps other countries' rows unchanged
            row["others"] = others
        out.append(row)
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
    TARGET_JS.write_text(f"const MANUFACTURER_MONTHLY = {body};\n", encoding="utf-8", newline="\n")

    for country in COUNTRIES:
        months = {r["year_month"] for r in data[country]}
        brands = {r["brand"] for r in data[country]}
        print(f"OK: {country} -- {len(data[country])} rows, {len(months)} months, {len(brands)} brands.")
    print(f"Wrote {TARGET_JS}")


if __name__ == "__main__":
    main()
