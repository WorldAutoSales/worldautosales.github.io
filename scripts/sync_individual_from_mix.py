#!/usr/bin/env python3
"""Copy period-block data (raw arrays with their source comments, asOf, priorYearBev, priorYearTotal)
from powertrain-mix-by-country.html into individual-country.html, which keeps its own, older copy.
Only inserts missing countries and updates differing values; never deletes. --dry-run prints the changes."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import add_monthly_country_data as a

ROOT = a.REPO_ROOT
MIX = ROOT / "powertrain-mix-by-country.html"
IND = ROOT / "individual-country.html"
dry = "--dry-run" in sys.argv

mix = MIX.read_text(encoding="utf-8")
ind = IND.read_text(encoding="utf-8", newline="")
a.LINE_ENDING = "\r\n" if "\r\n" in ind[:200000] else "\n"

keys = re.findall(r'^  "(20\d\d-[a-z0-9]+)": \{', ind, re.M)
stats = {"INSERT": 0, "UPDATE": 0}


def raw_entries(text, s, e):
    out, pending = [], []
    for line in text[s:e].splitlines():
        t = line.strip()
        if t.startswith("//"):
            pending.append(t[2:].strip())
            continue
        m = re.match(r'"([^"]+)":\s*(\[[^\]]*\])\s*,?\s*(//.*)?$', t)
        if m:
            c = " ".join(pending) if pending else (m.group(3)[2:].strip() if m.group(3) else None)
            out.append((m.group(1), m.group(2), c))
        pending = []
    return out


for k in keys:
    mb = a.extract_block(mix, rf'"{re.escape(k)}"\s*:\s*\{{', k)
    for sub in ("raw", "asOf", "priorYearBev", "priorYearTotal"):
        ms = a.extract_subkey_block(mix, mb[0], mb[1], sub)
        if ms is None:
            continue
        ib = a.extract_block(ind, rf'"{re.escape(k)}"\s*:\s*\{{', k)
        isub = a.extract_subkey_block(ind, ib[0], ib[1], sub)
        if isub is None:
            print("SKIP", k, sub, "(no such sub-block in individual page)")
            continue
        if sub == "raw":
            for c, lit, com in raw_entries(mix, ms[0] + 1, ms[1]):
                ib = a.extract_block(ind, rf'"{re.escape(k)}"\s*:\s*\{{', k)
                isub = a.extract_subkey_block(ind, ib[0], ib[1], sub)
                cur = re.search(r'"' + re.escape(c) + r'":\s*(\[[^\]]*\])', ind[isub[0]:isub[1]])
                if cur and re.sub(r"\s", "", cur.group(1)) == re.sub(r"\s", "", lit):
                    continue
                ind, act = a.upsert_array_entry(ind, isub[0] + 1, isub[1], c, lit, comment=com)
                stats[act] += 1
                print(act, k, "raw", c)
        else:
            for m in re.finditer(r'"([^"]+)"\s*:\s*("[^"]*"|-?\d+(?:\.\d+)?)', mix[ms[0] + 1:ms[1]]):
                c, v = m.group(1), m.group(2)
                ib = a.extract_block(ind, rf'"{re.escape(k)}"\s*:\s*\{{', k)
                isub = a.extract_subkey_block(ind, ib[0], ib[1], sub)
                cur = re.search(r'"' + re.escape(c) + r'"\s*:\s*("[^"]*"|-?\d+(?:\.\d+)?)', ind[isub[0]:isub[1]])
                if cur and cur.group(1) == v:
                    continue
                ind, act = a.upsert_scalar_entry(ind, isub[0] + 1, isub[1], c, v)
                stats[act] += 1
                print(act, k, sub, c)
print(stats)
if not dry:
    IND.write_text(ind, encoding="utf-8", newline="")
    print("written")
