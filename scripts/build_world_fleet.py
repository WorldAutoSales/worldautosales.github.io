#!/usr/bin/env python3
"""
Rebuilds the world light-vehicle fleet series (2000-2025) used by world-car-sales.html section 11C.

World fleet = 50 tracked countries (scripts/build_cars_on_road.py, same real fleet counts / survival curves, run from 2000)
            + rest of world.
Rest of world: OICA passenger-car sales of all countries minus the 50 tracked countries
(scripts/data/oica_pc_rest_of_world.json, 2005-2024; 2025 = 2024 x IEA world growth; 2000-2004 back-cast with the 2005-2010
growth, floored at 0 and capped at 25%/yr), converted to light vehicles with the LV/passenger-car ratio observed 2010-2024
(IEA / OICA, 1.07 in 2000 -> 1.23 in 2024), aged with the Latin America survival curve (a long-lived proxy). Fleets of
countries that rely on used imports (much of Africa, Middle East, Central Asia, Central America) are undercounted by this
new-sales method.
BEV and PHEV stocks are not changed: they stay the IEA-based series already in assets/world-car-sales-data.js
(cumulative IEA sales with a 1.5% yearly loss, matching the IEA's measured electric stock); only the total, and therefore
the 'ICE & hybrids' remainder, comes from the bottom-up model.
2026 is a PROJECTED point: tracked countries use their 2026 projected registrations (YTD + trend, the site's standard method);
rest-of-world sales are held at the 2025 level; BEV and PHEV 2026 sales = IEA 2025 sales x the YoY growth of the site's own
2026 projection (61 countries with a 2025 annual and a 2026 projected fuel split), stocks rolled forward with the same
1.5% yearly loss.
Usage: python scripts/build_world_fleet.py [--write]
"""
import json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cars_on_road as B

JS = ROOT / 'assets' / 'world-car-sales-data.js'
OICA = json.load(open(B.DATA / 'oica_pc_rest_of_world.json'))['series']
IEA_GROWTH_2025 = 84.8 / 83.333333   # IEA world light-vehicle sales 2025 / 2024
RATIO = lambda y: min(max(0.006509353687550288 * y - 11.95049785026572, 1.0), 1.3)


def rest_of_world():
    pc = {int(y): v['row'] for y, v in OICA.items()}
    pc[2025] = pc[2024] * IEA_GROWTH_2025
    pc[2026] = pc[2025]   # held flat: no 2026 information for the rest of the world
    g = min(max(math.log(pc[2010] / pc[2005]) / 5, 0.0), 0.25)
    for y in range(1980, 2005): pc[y] = pc[2005] * math.exp(-g * (2005 - y))
    lv = {y: v * RATIO(y) for y, v in pc.items()}
    S = B.survival(B.CURVES['Latin America'])
    fleet = {t: sum(lv[y] * S(t - y) for y in range(1980, t + 1)) for t in range(2000, 2027)}
    return lv, fleet


def projected_growth():
    """YoY growth of BEV and PHEV sales, 2026 projection vs 2025 annual, over the countries that have both fuel splits."""
    tx = (ROOT / 'assets' / 'country-yearly-data.js').read_text(encoding='utf-8')
    d = json.loads(re.search(r'=\s*(\{.*\});', tx, re.S).group(1))
    a = {'bev': 0.0, 'phev': 0.0, 'total': 0.0}; p = dict(a)
    for c, rs in d.items():
        r25 = next((r for r in rs if r['year'] == 2025 and r['period_type'] == 'ANNUAL'), None)
        r26 = next((r for r in rs if r['year'] == 2026 and r['period_type'] == 'PROJECTED'), None)
        if r25 and r26 and r25.get('bev') is not None and r26.get('bev') is not None and r25['total'] and r26['total']:
            for k in a: a[k] += r25.get(k) or 0; p[k] += r26.get(k) or 0
    return {k: p[k] / a[k] - 1 for k in a}


def main():
    write = '--write' in sys.argv
    rows, info = B.build(first_model=2000)
    tracked = {t: sum(x['bev'] + x['nonBev'] for c in rows for x in rows[c] if x['year'] == t) for t in range(2000, 2027)}
    lv, row = rest_of_world()
    world = {t: tracked[t] + row[t] for t in range(2000, 2027)}
    text = JS.read_text(encoding='utf-8')
    data = json.loads(re.search(r'const WCS = (\{.*\});', text, re.S).group(1))
    for r in data['fleet']:
        y = r['y']
        r['total'] = int(round(world[y]))
        r['tracked'] = int(round(tracked[y]))
        r['row'] = int(round(row[y]))
        r['ice'] = r['total'] - r['bev'] - r['phev']
    data['fleet'] = [r for r in data['fleet'] if r['y'] <= 2025]
    g = projected_growth()
    pw25 = [r for r in data['powertrain'] if r['y'] == 2025][0]
    lam = data['model']['evLoss']
    last = data['fleet'][-1]
    bev_s = pw25['bev'] * (1 + g['bev']); phev_s = pw25['phev'] * (1 + g['phev'])
    bev26 = last['bev'] * (1 - lam) + bev_s; phev26 = last['phev'] * (1 - lam) + phev_s
    r26 = dict(y=2026, total=int(round(world[2026])), tracked=int(round(tracked[2026])), row=int(round(row[2026])),
               bev=int(round(bev26)), phev=int(round(phev26)), iea=None, sales=None, measuredSales=False, proj=True,
               bevSales=int(round(bev_s)), phevSales=int(round(phev_s)), growth=dict((k, round(v, 3)) for k, v in g.items()))
    r26['ice'] = r26['total'] - r26['bev'] - r26['phev']
    data['fleet'].append(r26)
    print('year  tracked(50)  rest of world  world   IEA-implied')
    for r in data['fleet']:
        if r['y'] in (2000, 2005, 2010, 2015, 2020, 2024, 2025, 2026):
            print(r['y'], round(r['tracked'] / 1e6), round(r['row'] / 1e6), round(r['total'] / 1e6), round((r['iea'] or 0) / 1e6))
    if write:
        head = text[:text.index('const WCS')]
        JS.write_text(head + 'const WCS = ' + json.dumps(data, separators=(',', ':')) + ';\n', encoding='utf-8', newline='\n')
        print('wrote', JS.name)


if __name__ == '__main__':
    main()
