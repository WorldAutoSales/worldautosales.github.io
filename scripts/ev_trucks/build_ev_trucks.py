"""Builds assets/ev-trucks-data.js (EVT) for ev-trucking.html.

Inputs (raw API pulls, committed under scripts/ev_trucks/data/):
  iea_evs_commercial.json   IEA Global EV Data Explorer: Trucks / Vans / Buses, parameters EV sales, EV stock, EV sales share, EV stock share,
                            powertrains EV (= all electric), BEV, PHEV, FCEV, years 2012-2025, every region the explorer lists
  iea_evs_cars_sel.json     same for Cars, a few regions only (comparison line)
  Pull recipe (plain request, no key):  https://api.iea.org/electric-vehicles?parameter=EV+sales&category=Historical&mode=Trucks&year=2025
Output: EVT = { years, regions: { <region>: { Trucks: { sales:[...], stock:[...], sShare:[...], tShare:[...], bev:[...], fcev:[...], phev:[...] }, Vans:{...}, Buses:{...}, Cars:{sales, sShare} } } }
Values are per year (null = not published); shares are in percent as published (rounded by the IEA to 2 significant digits).
Run from the repo root:  python scripts/ev_trucks/build_ev_trucks.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
YEARS = list(range(2012, 2026))
KEY = {'EV sales': 'sales', 'EV stock': 'stock', 'EV sales share': 'sShare', 'EV stock share': 'tShare'}

rows = json.load(open(os.path.join(HERE, 'data', 'iea_evs_commercial.json')))
cars = json.load(open(os.path.join(HERE, 'data', 'iea_evs_cars_sel.json')))
regions = {}


def put(reg, mode, field, year, val):
    r = regions.setdefault(reg, {}).setdefault(mode, {})
    arr = r.setdefault(field, [None] * len(YEARS))
    if year in YEARS:
        arr[YEARS.index(year)] = val


for x in rows:
    f = KEY.get(x['parameter'])
    if not f:
        continue
    if x['powertrain'] == 'EV':
        put(x['region'], x['mode'], f, x['year'], x['value'])
    elif x['parameter'] in ('EV sales', 'EV stock') and x['powertrain'] in ('BEV', 'PHEV', 'FCEV'):
        put(x['region'], x['mode'], x['powertrain'].lower() + ('' if f == 'sales' else 'Stock'), x['year'], x['value'])
for x in cars:
    if x['powertrain'] != 'EV' or x['parameter'] not in ('EV sales', 'EV sales share'):
        continue
    reg = 'United States' if x['region'] == 'USA' else x['region']
    put(reg, 'Cars', KEY[x['parameter']], x['year'], x['value'])


def clean(v):
    return None if v is None else (round(v, 3) if isinstance(v, float) else v)


out = {'years': YEARS, 'regions': {r: {m: {k: [clean(v) for v in a] for k, a in d.items()} for m, d in ms.items()} for r, ms in regions.items()}}
js = '// IEA Global EV Data Explorer (CC BY 4.0): electric trucks, vans, buses (and cars for comparison) by region, 2012-2025. Built by scripts/ev_trucks/build_ev_trucks.py\nconst EVT = ' + json.dumps(out, separators=(',', ':')) + ';\n'
open(os.path.join(ROOT, 'assets', 'ev-trucks-data.js'), 'w', encoding='utf8').write(js)
print(len(regions), 'regions,', len(js) // 1024, 'KB')
