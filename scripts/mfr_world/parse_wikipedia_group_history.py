"""Parses Wikipedia's "List of automotive manufacturers by production" into world volume by manufacturer group and year.

  2001-2017  OICA world ranking of manufacturers: motor vehicle PRODUCTION (cars + light/heavy commercial vehicles + buses), top 15-20 groups per year
  2018-2025  F&I Tools USA worldwide SALES by group, top 15 groups
Fetch the rendered article (plain request, browser-like user agent):
  curl -A "Mozilla/5.0" "https://en.wikipedia.org/w/api.php?action=parse&page=List_of_automotive_manufacturers_by_production&prop=text&format=json&formatversion=2" -o .scratch/mfrworld/wp_html.json
Output: scripts/mfr_world/data/wikipedia_group_history_raw.json   {raw Wikipedia group name: {year: {v, basis}}}
Run from the repo root:  python scripts/mfr_world/parse_wikipedia_group_history.py
"""
import io, json, os, re
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
html = json.load(open(os.path.join(ROOT, '.scratch', 'mfrworld', 'wp_html.json'), encoding='utf8'))['parse']['text']
tabs = pd.read_html(io.StringIO(html))
# table index in the article -> years it holds (verified against the table headers)
YEAR_OF = {3: None, 4: 2014, 5: 2013, 6: 2012, 7: 2011, 8: 2010, 9: 2009, 10: 2008, 11: 2007, 12: 2006, 13: 2005, 15: 2002, 16: 2001}
out = {}


def clean(name):
    n = re.sub(r'\[[^\]]*\]', '', str(name))          # footnote marks [4]
    n = re.sub(r'^\s*\d+\.\s*', '', n)                 # "1. Toyota"
    n = re.sub(r'\(.*?\)', '', n)                      # "(with SAIC-GM-Wuling)"
    return re.sub(r'\s+', ' ', n).strip(' /')


def num(x):
    try:
        v = float(str(x).replace(',', '').strip())
        return v if v >= 100000 else None
    except ValueError:
        m = re.match(r'^\s*([\d,]{7,11})', str(x))
        return float(m.group(1).replace(',', '')) if m else None


def put(g, y, v, basis):
    if v is not None:
        out.setdefault(clean(g), {})[str(y)] = {'v': int(v), 'basis': basis}


def multi(i, basis):
    t = tabs[i]
    cols = {c: int(re.search(r'\((20\d\d)\)', str(c)).group(1)) for c in t.columns if re.search(r'\((20\d\d)\)', str(c))}
    for _, r in t.iterrows():
        for c, y in cols.items():
            put(r['Group'], y, num(r[c]), basis)


multi(0, 'sales'); multi(1, 'sales'); multi(3, 'production'); multi(14, 'production')
for i, y in YEAR_OF.items():
    if y is None:
        continue
    t = tabs[i]
    if 'Group' in [str(c) for c in t.columns]:               # tidy tables: Group + Total / Vehicles
        col = 'Total' if 'Total' in t.columns else 'Vehicles'
        for _, r in t.iterrows():
            put(r['Group'], y, num(r[col]), 'production')
    else:                                                    # bar-chart tables (2009-2011): a "N. Group" label cell and a trailing total
        for _, r in t.iterrows():
            cells = [str(x) for x in r.tolist() if str(x) != 'nan']
            lab = next((c for c in cells if re.match(r'^\s*\d+\.\s*\D', c)), None)
            vals = [num(c) for c in cells if num(c)]
            if lab and vals:
                put(lab, y, vals[-1], 'production')
os.makedirs(os.path.join(HERE, 'data'), exist_ok=True)
json.dump(out, open(os.path.join(HERE, 'data', 'wikipedia_group_history_raw.json'), 'w', encoding='utf8'), indent=0, sort_keys=True)
print(len(out), 'groups')
for g in sorted(out, key=lambda g: -max(v['v'] for v in out[g].values())):
    ys = sorted(out[g])
    print('%-36s %s-%s (%2d yrs)' % (g[:36], ys[0], ys[-1], len(ys)))
