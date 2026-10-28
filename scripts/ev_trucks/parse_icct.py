"""Parses the country-level appendix (pages 23-27) of the ICCT report "An overview of the global zero-emission medium- and heavy-duty
vehicle market" (August 2026, ID 651; scripts/ev_trucks/data/icct_global_zemhdv_2026-08.pdf, source https://theicct.org/global-ev-market-monitor-trucks-buses/)
into scripts/ev_trucks/data/icct_country_zemhdv.json:
  { country: { year: { zeSales, totalHDV, zeShare, buses, medium, heavy, topMaker } } }
ICCT definitions differ from the IEA's: medium-duty = 3.5-12 t (China, Europe), US Class 2b-6 (8,501-26,000 lb), heavy = above 12 t / Class 7-8;
"total HDV sales" = medium + heavy trucks + buses and coaches.  Run from the repo root:  python scripts/ev_trucks/parse_icct.py
"""
import json, os, re
import pdfplumber

HERE = os.path.dirname(os.path.abspath(__file__))
pdf = pdfplumber.open(os.path.join(HERE, 'data', 'icct_global_zemhdv_2026-08.pdf'))
lines = []
for n in range(22, 27):
    lines += (pdf.pages[n].extract_text() or '').split('\n')
num = lambda x: None if x == '-' else float(x.replace(',', ''))
rx = re.compile(r'^(?:(?P<c>[A-Za-z][A-Za-z .\-\']+?)\s+)?(?P<y>20\d\d)\s+(?P<zs>[\d,\-]+)\s+(?P<tot>[\d,]+)\s+(?P<sh>[\d.]+)\s+(?P<b>[\d,\-]+)\s+(?P<m>[\d,\-]+)\s+(?P<h>[\d,\-]+)\s*(?P<mf>.*)$')
out, block, names = {}, [], []


def flush():
    global block, names
    if block:
        name = names[0] if names else None
        out[name] = {r['year']: {k: v for k, v in r.items() if k != 'year'} for r in block}
    block, names = [], []


for l in lines:
    l = l.strip()
    m = rx.match(l)
    if m:
        d = m.groupdict()
        y = int(d['y'])
        if block and y <= block[-1]['year']:
            flush()
        if d['c']:
            names.append(d['c'])
        block.append(dict(year=y, zeSales=num(d['zs']), totalHDV=num(d['tot']), zeShare=float(d['sh']), buses=num(d['b']), medium=num(d['m']), heavy=num(d['h']), topMaker=d['mf'].strip() or None))
    elif re.match(r'^[A-Z][A-Za-z .\-]+$', l) and not l.startswith(('Country', 'COUNTRY', 'THE ', 'ICCT')):
        names.append(l)
flush()
json.dump(out, open(os.path.join(HERE, 'data', 'icct_country_zemhdv.json'), 'w'), separators=(',', ':'))
print(len(out), sorted(out))
