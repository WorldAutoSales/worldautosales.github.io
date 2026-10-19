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
    g = min(max(math.log(pc[2010] / pc[2005]) / 5, 0.0), 0.25)
    for y in range(1980, 2005): pc[y] = pc[2005] * math.exp(-g * (2005 - y))
    lv = {y: v * RATIO(y) for y, v in pc.items()}
    S = B.survival(B.CURVES['Latin America'])
    fleet = {t: sum(lv[y] * S(t - y) for y in range(1980, t + 1)) for t in range(2000, 2026)}
    return lv, fleet


def main():
    write = '--write' in sys.argv
    rows, info = B.build(first_model=2000)
    tracked = {t: sum(x['bev'] + x['nonBev'] for c in rows for x in rows[c] if x['year'] == t) for t in range(2000, 2026)}
    lv, row = rest_of_world()
    world = {t: tracked[t] + row[t] for t in range(2000, 2026)}
    text = JS.read_text(encoding='utf-8')
    data = json.loads(re.search(r'const WCS = (\{.*\});', text, re.S).group(1))
    for r in data['fleet']:
        y = r['y']
        r['total'] = int(round(world[y]))
        r['tracked'] = int(round(tracked[y]))
        r['row'] = int(round(row[y]))
        r['ice'] = r['total'] - r['bev'] - r['phev']
    print('year  tracked(50)  rest of world  world   IEA-implied')
    for r in data['fleet']:
        if r['y'] in (2000, 2005, 2010, 2015, 2020, 2024, 2025):
            print(r['y'], round(r['tracked'] / 1e6), round(r['row'] / 1e6), round(r['total'] / 1e6), round((r['iea'] or 0) / 1e6))
    if write:
        head = text[:text.index('const WCS')]
        JS.write_text(head + 'const WCS = ' + json.dumps(data, separators=(',', ':')) + ';\n', encoding='utf-8', newline='\n')
        print('wrote', JS.name)


if __name__ == '__main__':
    main()
