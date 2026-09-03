#!/usr/bin/env python3
"""
Adds (or updates) one country's real monthly powertrain figures across every
hand-maintained site file that needs them, and recomputes that country's
year-to-date and full-year-projection figures to match.

This mechanizes the multi-file edit this project does by hand every time a
new month lands for a country with real monthly granularity (Australia,
Japan, India, ...): append to the two JSON asset files, patch the matching
period block in powertrain-mix-by-country.html (monthly + YTD + projection),
and patch the country's entry in auto-markets-by-country.html.

Deliberately NOT automated by this script:
  - Finding and reading the source article/table. That's a judgment call
    (picking the right table when a source is inconsistent, noticing when a
    figure doesn't reconcile) that has to stay a human/LLM step.
  - The Supabase database (world_auto_sales / world_auto_sales_annual /
    data_release_schedule) -- those are a handful of fast SQL statements,
    not the slow part, and are left as a separate manual step.
  - world-auto-sales.html -- not every country is wired into that page (e.g.
    Australia isn't); wiring a NEW country into it is a bigger, rarer edit
    than this script's job of extending a country already fully wired in.
  - Creating a brand-new period block (a month/year no country has any data
    for yet) or wiring in a country that has never appeared in a given file
    before. Both are rare, one-time edits safer done by hand; this script
    only updates/inserts within blocks and country entries that already
    exist, and stops with a clear error rather than fabricate structure.

Usage:
    python scripts/add_monthly_country_data.py \\
      --country Australia --ym 2026-09 \\
      --bev 30500 --phev 11200 --hev 19800 --petrol 24100 --diesel 22600 \\
      --comment "FCAI (VFACTS) via CarExpert, Australia (monthly) -- light vehicles only, excludes heavy commercial; others=0" \\
      --source-label "FCAI (VFACTS)" \\
      [--others 0] [--prior-year-bev 9999] [--prior-year-total 88888] [--dry-run]

Run with --dry-run first: it prints every change it would make (and the
recomputed YTD/projection numbers) without writing anything.
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MONTHLY_JS = REPO_ROOT / "assets" / "country-monthly-data.js"
YEARLY_JS = REPO_ROOT / "assets" / "country-yearly-data.js"
MIX_HTML = REPO_ROOT / "powertrain-mix-by-country.html"
MARKETS_HTML = REPO_ROOT / "auto-markets-by-country.html"

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FUELS = ["bev", "phev", "hev", "petrol", "diesel", "others"]


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--country", required=True)
    p.add_argument("--ym", required=True, help="YYYY-MM, e.g. 2026-09")
    for f in ["bev", "phev", "hev", "petrol", "diesel"]:
        p.add_argument(f"--{f}", required=True, type=int)
    p.add_argument("--others", type=int, default=0)
    p.add_argument("--comment", required=True, help="inline // comment text for the monthly raw entry (no leading //)")
    p.add_argument("--source-label", required=True, help='short source label, e.g. "FCAI (VFACTS)" -- used in the YTD source text')
    p.add_argument("--projection-label", default=None, help="label for the PROJECTED source text's trailing parenthetical; defaults to --source-label")
    p.add_argument("--prior-year-bev", type=int, default=None)
    p.add_argument("--prior-year-total", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


# ---------- JSON asset files (country-monthly-data.js / country-yearly-data.js) ----------

def load_js_const(path, varname):
    text = path.read_text(encoding="utf-8")
    prefix = f"const {varname} = "
    if not text.startswith(prefix) or not text.rstrip("\n").endswith("};"):
        raise SystemExit(f"{path.name}: doesn't match the expected 'const {varname} = {{...}};' single-statement shape")
    body = text[len(prefix):]
    body = body.rstrip("\n")
    assert body.endswith(";")
    body = body[:-1]
    return json.loads(body)


def dump_js_const(path, varname, obj):
    body = json.dumps(obj, separators=(",", ":"), ensure_ascii=True)
    path.write_text(f"const {varname} = {body};\n", encoding="utf-8", newline="\n")


def update_monthly_asset(country, ym, values, dry_run):
    data = load_js_const(MONTHLY_JS, "COUNTRY_MONTHLY")
    if country not in data:
        raise SystemExit(f"{MONTHLY_JS.name}: {country!r} has no existing entry -- this script only extends a country already present")
    entries = data[country]
    entry = {"ym": ym, **{f: values[f] for f in FUELS}, "total": sum(values[f] for f in FUELS)}
    existing_idx = next((i for i, e in enumerate(entries) if e["ym"] == ym), None)
    if existing_idx is not None:
        action = "UPDATE"
        entries[existing_idx] = entry
    else:
        action = "INSERT"
        entries.append(entry)
        entries.sort(key=lambda e: e["ym"])
    print(f"[{MONTHLY_JS.name}] {action} {country} {ym}: {entry}")
    if not dry_run:
        dump_js_const(MONTHLY_JS, "COUNTRY_MONTHLY", data)
    return data[country]


def compute_ytd_and_projection(month_entries, year):
    """From this country's full list of monthly entries, sum every month in
    `year` for YTD, then project the full year using the same method the
    site already documents: per fuel, rate = max(avg of last 3 actual
    months, YTD average), applied to the remaining months, added to YTD."""
    year_months = sorted([e for e in month_entries if e["ym"].startswith(f"{year}-")], key=lambda e: e["ym"])
    if not year_months:
        raise SystemExit(f"no {year} monthly entries found to compute YTD/projection from")
    months_covered = len(year_months)
    ytd = {f: sum(e[f] for e in year_months) for f in FUELS}
    ytd["total"] = sum(ytd[f] for f in FUELS)

    last3 = year_months[-3:]
    last3_avg = {f: sum(e[f] for e in last3) / len(last3) for f in FUELS}
    ytd_avg = {f: ytd[f] / months_covered for f in FUELS}
    rate = {f: max(last3_avg[f], ytd_avg[f]) for f in FUELS}
    remaining = 12 - months_covered
    full_year = {f: ytd[f] + round(rate[f] * remaining) for f in FUELS}
    full_year["total"] = sum(full_year[f] for f in FUELS)

    return months_covered, remaining, ytd, full_year


def update_yearly_asset(country, year, months_covered, ytd, full_year, remaining, source_label, projection_label, dry_run):
    data = load_js_const(YEARLY_JS, "COUNTRY_YEARLY")
    if country not in data:
        raise SystemExit(f"{YEARLY_JS.name}: {country!r} has no existing entry -- this script only extends a country already present")
    records = data[country]
    mon = MONTH_ABBR[months_covered - 1]

    ytd_source = f"{source_label}, summed Jan-{mon} {year} from monthly data"
    ytd_record = {"year": year, "period_type": "YTD", "months_covered": months_covered,
                  **{f: ytd[f] for f in FUELS}, "total": ytd["total"], "source": ytd_source}
    proj_source = (f"Projected -- each fuel trended from the last 3 actual months' average "
                    f"(or the {months_covered}-month YTD average if higher), applied to the "
                    f"remaining {remaining} months ({projection_label or source_label})")
    proj_record = {"year": year, "period_type": "PROJECTED", "months_covered": months_covered,
                    **{f: full_year[f] for f in FUELS}, "total": full_year["total"], "source": proj_source}

    for label, record in [("YTD", ytd_record), ("PROJECTED", proj_record)]:
        idx = next((i for i, r in enumerate(records) if r["year"] == year and r["period_type"] == label), None)
        if idx is not None:
            print(f"[{YEARLY_JS.name}] UPDATE {country} {year} {label}: total={record['total']}")
            records[idx] = record
        else:
            print(f"[{YEARLY_JS.name}] INSERT {country} {year} {label}: total={record['total']}")
            records.append(record)

    if not dry_run:
        dump_js_const(YEARLY_JS, "COUNTRY_YEARLY", data)


# ---------- powertrain-mix-by-country.html (hand-formatted JS object literal) ----------

def find_matching_brace(text, open_idx):
    """Return the index of the `}` matching the `{` at open_idx, skipping
    over string literals (with \\" escapes) and // line comments."""
    assert text[open_idx] == "{"
    depth = 0
    i = open_idx
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            nl = text.find("\n", i)
            i = n if nl == -1 else nl + 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise SystemExit("unbalanced braces while scanning powertrain-mix-by-country.html")


def extract_block(text, key_pattern, label):
    m = re.search(key_pattern, text)
    if not m:
        raise SystemExit(f"{MIX_HTML.name}: couldn't find {label} -- it must already exist (this script won't create a period block from scratch)")
    open_idx = text.index("{", m.end() - 1)
    close_idx = find_matching_brace(text, open_idx)
    return open_idx, close_idx


def extract_subkey_block(text, block_start, block_end, subkey):
    section = text[block_start:block_end]
    m = re.search(rf"\b{subkey}\s*:\s*\{{", section)
    if not m:
        return None
    open_idx = block_start + section.index("{", m.end() - 1)
    close_idx = find_matching_brace(text, open_idx)
    return open_idx, close_idx


LINE_ENDING = "\r\n"  # this file uses CRLF throughout


def upsert_array_entry(text, obj_start, obj_end, country, new_value_literal, comment=None):
    """Inside the object spanning (obj_start, obj_end] (braces excluded via
    +1/-0 handled by caller), replace an existing '"Country": [...]' line's
    array, or insert a new line (with an optional preceding comment) right
    before the object's closing brace."""
    section = text[obj_start:obj_end]
    pat = re.compile(r'"' + re.escape(country) + r'":\s*\[[^\]]*\]')
    m = pat.search(section)
    if m:
        new_section = section[:m.start()] + f'"{country}": {new_value_literal}' + section[m.end():]
        return text[:obj_start] + new_section + text[obj_end:], "UPDATE"
    # insert before the last non-whitespace char in section (the closing brace is at obj_end, excluded)
    insertion = ""
    if comment:
        insertion += f"      // {comment}{LINE_ENDING}"
    insertion += f'      "{country}": {new_value_literal}'
    # section currently ends with the previous entry's trailing content (often ending in a value with
    # no trailing comma, since it was the last key) -- ensure a comma separates it from our insertion.
    stripped = section.rstrip()
    if stripped and not stripped.endswith(("{", ",")):
        section = section[:len(stripped)] + "," + section[len(stripped):]
    new_section = section + insertion
    return text[:obj_start] + new_section + text[obj_end:], "INSERT"


def upsert_scalar_entry(text, obj_start, obj_end, country, new_value_literal):
    section = text[obj_start:obj_end]
    pat = re.compile(r'"' + re.escape(country) + r'":\s*(?:"[^"]*"|-?\d+(?:\.\d+)?)')
    m = pat.search(section)
    if m:
        new_section = section[:m.start()] + f'"{country}":{new_value_literal}' + section[m.end():]
        return text[:obj_start] + new_section + text[obj_end:], "UPDATE"
    stripped = section.rstrip()
    if stripped and not stripped.endswith(("{", ",")):
        section = section[:len(stripped)] + "," + section[len(stripped):]
    new_section = section + f'      "{country}":{new_value_literal}'
    return text[:obj_start] + new_section + text[obj_end:], "INSERT"


def array_literal(values, order=("bev", "phev", "hev", "others", "petrol", "diesel"), spaced=False):
    total = sum(values[f] for f in FUELS)
    nums = [values[f] for f in order] + [total]
    sep = ", " if spaced else ","
    return "[" + sep.join(str(n) for n in nums) + "]"


def update_mix_html(country, ym, year, values, comment, months_covered, ytd, full_year, remaining,
                     prior_year_bev, prior_year_total, dry_run):
    text = MIX_HTML.read_text(encoding="utf-8")
    mon = MONTH_ABBR[months_covered - 1]

    # 1) the month's own block
    b_start, b_end = extract_block(text, rf'"{re.escape(ym)}"\s*:\s*\{{', f'period block "{ym}"')
    raw = extract_subkey_block(text, b_start, b_end, "raw")
    if raw is None:
        raise SystemExit(f'{MIX_HTML.name}: period block "{ym}" has no raw{{}} -- unexpected shape')
    text, action = upsert_array_entry(text, raw[0] + 1, raw[1], country, array_literal(values), comment=comment)
    print(f'[{MIX_HTML.name}] {action} "{ym}".raw.{country}')

    for subkey, val in [("priorYearBev", prior_year_bev), ("priorYearTotal", prior_year_total)]:
        if val is None:
            continue
        b_start, b_end = extract_block(text, rf'"{re.escape(ym)}"\s*:\s*\{{', f'period block "{ym}"')  # re-find, text shifted
        sub = extract_subkey_block(text, b_start, b_end, subkey)
        if sub is None:
            print(f'[{MIX_HTML.name}] SKIP "{ym}".{subkey} -- block has no {subkey}{{}} to insert into')
            continue
        text, action = upsert_scalar_entry(text, sub[0] + 1, sub[1], country, str(val))
        print(f'[{MIX_HTML.name}] {action} "{ym}".{subkey}.{country} = {val}')

    # 2) the "{year}-ytd" block
    b_start, b_end = extract_block(text, rf'"{year}-ytd"\s*:\s*\{{', f'period block "{year}-ytd"')
    raw = extract_subkey_block(text, b_start, b_end, "raw")
    ytd_comment = f"source: {comment.split(' -- ')[0] if ' -- ' in comment else comment.split(',')[0]} -- Jan-{mon} {year} summed from monthly"
    text, action = upsert_array_entry(text, raw[0] + 1, raw[1], country, array_literal(ytd), comment=ytd_comment)
    print(f'[{MIX_HTML.name}] {action} "{year}-ytd".raw.{country}')

    b_start, b_end = extract_block(text, rf'"{year}-ytd"\s*:\s*\{{', f'period block "{year}-ytd"')
    asof = extract_subkey_block(text, b_start, b_end, "asOf")
    text, action = upsert_scalar_entry(text, asof[0] + 1, asof[1], country, f'"through {mon} {year}"')
    print(f'[{MIX_HTML.name}] {action} "{year}-ytd".asOf.{country}')

    # 3) the "{year}-projection" block
    b_start, b_end = extract_block(text, rf'"{year}-projection"\s*:\s*\{{', f'period block "{year}-projection"')
    raw = extract_subkey_block(text, b_start, b_end, "raw")
    text, action = upsert_array_entry(text, raw[0] + 1, raw[1], country, array_literal(full_year, spaced=True))
    print(f'[{MIX_HTML.name}] {action} "{year}-projection".raw.{country}')

    if not dry_run:
        MIX_HTML.write_text(text, encoding="utf-8", newline="")


# ---------- auto-markets-by-country.html ----------

def update_markets_html(country, year, ytd_total, projected_total, dry_run):
    text = MARKETS_HTML.read_text(encoding="utf-8")
    m = re.search(r'"' + re.escape(country) + r'":\{[^{}]*series:\{', text)
    if not m:
        raise SystemExit(f"{MARKETS_HTML.name}: {country!r} entry not found in MARKETS -- this script only updates a country already present")
    series_open = text.index("{", m.end() - 1)
    series_close = find_matching_brace(text, series_open)
    section = text[series_open + 1:series_close]
    pat = re.compile(rf'"{year}":\d+')
    if pat.search(section):
        section = pat.sub(f'"{year}":{ytd_total}', section)
    else:
        section = section.rstrip() + f',"{year}":{ytd_total}'
    text = text[:series_open + 1] + section + text[series_close:]

    m2 = re.search(r'"' + re.escape(country) + r'":\{[^{}]*series:\{[^{}]*\},projected:\{', text)
    if not m2:
        raise SystemExit(f"{MARKETS_HTML.name}: {country!r} projected{{}} not found")
    proj_open = text.index("{", m2.end() - 1)
    proj_close = find_matching_brace(text, proj_open)
    psection = text[proj_open + 1:proj_close]
    ppat = re.compile(rf'"{year}":\d+')
    if ppat.search(psection):
        psection = ppat.sub(f'"{year}":{projected_total}', psection)
    else:
        psection = (psection.rstrip() + f',"{year}":{projected_total}') if psection.strip() else f'"{year}":{projected_total}'
    text = text[:proj_open + 1] + psection + text[proj_close:]

    print(f"[{MARKETS_HTML.name}] {country} series[{year}]={ytd_total} projected[{year}]={projected_total}")
    if not dry_run:
        MARKETS_HTML.write_text(text, encoding="utf-8", newline="")


def main():
    args = parse_args()
    year = int(args.ym[:4])
    values = {f: getattr(args, f) for f in FUELS}

    print(f"=== {'DRY RUN — ' if args.dry_run else ''}{args.country} {args.ym} ===")
    month_entries = update_monthly_asset(args.country, args.ym, values, args.dry_run)
    months_covered, remaining, ytd, full_year = compute_ytd_and_projection(month_entries, year)
    print(f"YTD ({months_covered} mo): {ytd}")
    print(f"Projected full year ({remaining} mo remaining): {full_year}")

    update_yearly_asset(args.country, year, months_covered, ytd, full_year, remaining, args.source_label, args.projection_label, args.dry_run)
    update_mix_html(args.country, args.ym, year, values, args.comment, months_covered, ytd, full_year, remaining,
                     args.prior_year_bev, args.prior_year_total, args.dry_run)
    update_markets_html(args.country, year, ytd["total"], full_year["total"], args.dry_run)

    if args.dry_run:
        print("\n(dry run -- nothing written; drop --dry-run to apply)")
    else:
        print("\nDone. Now: verify in-browser, update the Supabase DB separately, then commit.")


if __name__ == "__main__":
    main()
