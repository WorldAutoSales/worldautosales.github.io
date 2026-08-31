"""
One-off script that built the "2020 (Annual)"/"2021 (Annual)"/"2022 (Annual)" comparison
periods for powertrain-mix-by-country.html's MONTHLY_DATA, sourced from world_auto_sales_annual
(the 2020-2022 rows already existed in the DB from the 2026-08-29 Eurostat backfill; this just
exposed them as selectable periods on the page). Historical record / adaptable reference for
exposing further years the same way — not run automatically, writes block_YYYY.txt files that
then need to be spliced into the HTML by hand (see the population log entry for the exact splice
used). Requires scripts/annual_2020_2022.json (a REST dump of those years) to already exist.
"""
import json
import urllib.request
from collections import defaultdict

KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
       "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJ0bWx4dmpwanhjdmpkeWtya3ZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODcwNzY1NDYsImV4cCI6MjEwMjY1MjU0Nn0."
       "yxV9iE9xP4MZnMnZOPupKr2_eyRo-_jGoT5lTTnHS14")

d = json.load(open('annual_2020_2022.json', encoding='utf8'))

url = ("https://rtmlxvjpjxcvjdykrkvm.supabase.co/rest/v1/world_auto_sales_annual"
       "?select=country,year,bev,source,period_type&year=eq.2019&period_type=eq.ANNUAL&order=id.asc&limit=1000")
req = urllib.request.Request(url, headers={"apikey": KEY, "Authorization": "Bearer " + KEY})
d2019 = json.loads(urllib.request.urlopen(req).read())

FUELS = ('bev', 'phev', 'hev', 'petrol', 'diesel', 'others')


def has_split(r):
    return r['source'] != 'OICA' and r['bev'] is not None


by_year = defaultdict(dict)
gap_notes = defaultdict(list)
for r in d:
    if not has_split(r):
        continue
    by_year[r['year']][r['country']] = r

all_rows_by_year_country = defaultdict(dict)
for r in d + d2019:
    all_rows_by_year_country[r['year']][r['country']] = r


def esc(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


blocks = []
for year in [2020, 2021, 2022]:
    countries = by_year[year]
    raw_parts = []
    for c in sorted(countries.keys()):
        r = countries[c]
        bev, phev, hev, petrol, diesel, others = (r[k] or 0 for k in FUELS)
        total = r['total_units']
        # None is used two different ways in this DB: a deliberate "folded into Petrol, this is
        # genuinely zero" (diesel, for many non-European countries) vs. "the source just didn't
        # publish this category for this country/year" (seen for HEV on a handful of Eurostat
        # rows, e.g. Iceland 2020). Per the user's explicit call: treat every None as 0 and put
        # whatever gap remains into "others" (clipped at 0, never negative) rather than excluding
        # the country — every tracked country stays visible, at the cost of a slightly fuzzy
        # "others" bucket for the handful of rows with a real gap.
        gap = total - (bev + phev + hev + petrol + diesel + others)
        if gap != 0:
            others = max(0, others + gap)
            gap_notes[year].append((c, gap))
        raw_parts.append('%s: [%d,%d,%d,%d,%d,%d,%d]' % (esc(c), bev, phev, hev, others, petrol, diesel, total))
    raw_str = ",\n      ".join(raw_parts)

    prior_year = year - 1
    prior_map = all_rows_by_year_country.get(prior_year, {})
    prior_parts = []
    for c in countries.keys():
        pr = prior_map.get(c)
        if pr and pr.get('bev') is not None:
            prior_parts.append('%s:%d' % (esc(c), pr['bev']))
    prior_str = ",".join(prior_parts)

    block = '"%d-annual": {\n    label: "%d (Annual)",\n    raw: {\n      %s\n    },\n    priorYearBev: {\n      %s\n    }\n  }' % (
        year, year, raw_str, prior_str)
    blocks.append((year, len(countries), block))
    print(year, "countries with split:", len(countries), "priorYearBev entries:", len(prior_parts),
          "had a gap folded into others:", gap_notes[year])

for year, n, block in blocks:
    open('block_%d.txt' % year, 'w', encoding='utf8').write(block)
print("done")
