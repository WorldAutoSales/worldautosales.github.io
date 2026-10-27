"""Builds the per-brand site layers of the charging map: assets/brand-sites/<slug>.js (one file per brand, loaded on demand)
and assets/charging-brand-index.js (BRAND_INDEX: brand, file, sites, ports, fast ports, countries, per-source counts).

Positions come from the best public source available for each place:
  * AFDC / NRCan station locator API (United States + Canada; public, operating stations only), cached as .scratch/chg/qc/afdc_us.json / afdc_ca.json
      curl -G "https://developer.nlr.gov/api/alt-fuel-stations/v1.json" -d api_key=DEMO_KEY -d fuel_type=ELEC -d country=US -d limit=all
  * Open Charge Map (every other country, and any US/Canada site of a brand that the AFDC feed does not list within 120 m), cached in .scratch/chg/ocm/
  * Tesla Superchargers are not here: they have their own layer (supercharge.info, exact sites and stalls).
Rows: [lat, lon, ports, fast ports (>= 50 kW)]. A site found by both sources is kept once (AFDC wins in the US/Canada).
Run from the repo root after build_charging.py:  python scripts/charging/build_brand_sites.py
"""
import json, math, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import build_charging as bc  # noqa: E402
from charging_sources import COUNTRIES  # noqa: E402

CACHE = os.path.join(ROOT, '.scratch', 'chg')
OUT = os.path.join(ROOT, 'assets', 'brand-sites')
TOP_N = 90
FORCE = ['Couche-Tard / Circle K']      # small networks the map should always offer
SKIP = {bc.UNKNOWN, bc.SELF, 'Other brands', 'Other operators', 'Tesla', 'Non-Networked', 'Unknown operator'}
EXTRA_ALIASES = [(r'couche|circle ?k', 'Couche-Tard / Circle K'), (r'^red e$|^red e ', 'Red E Charge'), (r'^evoke', 'EVoke Systems')]


def brand_name(title):
    t = bc.norm(title or '')
    for rx, name in EXTRA_ALIASES:
        if re.search(rx, t):
            return name
    return bc.brand_of(title)


def slug(b):
    return re.sub(r'[^a-z0-9]+', '-', bc.norm(b)).strip('-')


class Sites:
    """sites of one brand, deduplicated within about 120 m"""
    def __init__(self):
        self.cells = {}
        self.rows = []

    def key(self, lat, lon):
        return int(math.floor(lat / 0.0011)), int(math.floor(lon * max(0.2, math.cos(math.radians(lat))) / 0.0011))

    def find(self, lat, lon):
        ky, kx = self.key(lat, lon)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                i = self.cells.get((ky + dy, kx + dx))
                if i is not None:
                    return i
        return None

    def add(self, lat, lon, ports, fast, src):
        i = self.find(lat, lon)
        if i is not None:
            return False
        self.cells[self.key(lat, lon)] = len(self.rows)
        self.rows.append([round(lat, 5), round(lon, 5), max(1, int(round(ports))), int(round(min(fast, max(1, ports)))), src])
        return True


def load_afdc():
    """AFDC rows per brand: (lat, lon, ports, fast)"""
    out = defaultdict(list)
    for fn in ('afdc_us.json', 'afdc_ca.json'):
        for s in json.load(open(os.path.join(CACHE, 'qc', fn), encoding='utf8'))['fuel_stations']:
            if s.get('status_code') != 'E' or s.get('latitude') is None or s.get('access_code') != 'public':
                continue
            net = (s.get('ev_network') or '').replace('_', ' ')
            if not net or net == 'Non-Networked':
                continue
            b = brand_name(net)
            f = s.get('ev_dc_fast_num') or 0
            p = f + (s.get('ev_level2_evse_num') or 0) + (s.get('ev_level1_evse_num') or 0)
            out[b].append((s['latitude'], s['longitude'], p, f))
    return out


def main():
    ref = json.load(open(os.path.join(CACHE, 'refdata.json')))
    ops = {o['ID']: o['Title'] for o in ref['Operators']}
    usage = {u['ID']: u['Title'] for u in ref['UsageTypes']}
    chg = json.loads(re.search(r'const CHARGING = (\{.*\});', open(os.path.join(ROOT, 'assets', 'charging-data.js'), encoding='utf8').read(), re.S).group(1))
    # brand ranking: world ports as on the page, plus the AFDC networks of the US / Canada
    rank = defaultdict(int)
    for w in chg['worldBrands']:
        rank[brand_name(w['b'])] += sum((v[1] or 0) for v in w['c'].values())
    afdc = load_afdc()
    for b, rows in afdc.items():
        rank[b] = max(rank[b], sum(r[2] for r in rows))
    brands = [b for b, _ in sorted(rank.items(), key=lambda kv: -kv[1]) if b not in SKIP][:TOP_N]
    brands += [b for b in FORCE if b not in brands]
    want = set(brands)
    sites = {b: Sites() for b in brands}
    ctry = {b: defaultdict(int) for b in brands}
    # 1. AFDC first (US + Canada)
    for b in brands:
        for lat, lon, p, f in afdc.get(b, []):
            sites[b].add(lat, lon, p, f, 'a')
    # 2. Open Charge Map everywhere
    for iso in COUNTRIES:
        f = os.path.join(CACHE, 'ocm', iso + '.json')
        if not os.path.exists(f):
            continue
        for p in json.load(open(f, encoding='utf8')):
            if p.get('StatusTypeID') in (100, 150, 200, 210) or 'Private' in usage.get(p.get('UsageTypeID'), ''):
                continue
            b = brand_name(ops.get(p.get('OperatorID')))
            if b not in want:
                continue
            ai = p.get('AddressInfo') or {}
            if ai.get('Latitude') is None or ai.get('Longitude') is None:
                continue
            conns = p.get('Connections') or []
            q = sum((c.get('Quantity') or 1) for c in conns) or 1
            n = p.get('NumberOfPoints') or q
            fast = sum((c.get('Quantity') or 1) for c in conns if (c.get('PowerKW') or 0) >= 50) * n / q
            sites[b].add(ai['Latitude'], ai['Longitude'], n, fast, 'o')
    os.makedirs(OUT, exist_ok=True)
    for fn in os.listdir(OUT):
        os.remove(os.path.join(OUT, fn))
    index = []
    for b in brands:
        rows = sites[b].rows
        if not rows:
            continue
        rows.sort(key=lambda r: (r[0], r[1]))
        n_a = sum(1 for r in rows if r[4] == 'a')
        data = [r[:4] for r in rows]
        sl = slug(b)
        open(os.path.join(OUT, sl + '.js'), 'w', encoding='utf8').write(
            '(window.BRAND_SITES = window.BRAND_SITES || {})[%s] = %s;\n' % (json.dumps(b, ensure_ascii=False), json.dumps(data, separators=(',', ':'))))
        index.append({'b': b, 'f': sl, 'n': len(rows), 'p': sum(r[2] for r in rows), 'fp': sum(r[3] for r in rows), 'a': n_a, 'o': len(rows) - n_a,
                      'rep': round(rank[b])})
    open(os.path.join(ROOT, 'assets', 'charging-brand-index.js'), 'w', encoding='utf8').write(
        '// Brands with a site layer on the charging map (assets/brand-sites/<f>.js): n sites, p ports, fp fast ports (50+ kW), a = sites from AFDC, o = from Open Charge Map, rep = ports reported for the brand on this page\n'
        'const BRAND_INDEX = ' + json.dumps(index, ensure_ascii=False, separators=(',', ':')) + ';\n')
    tot = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(len(index), 'brands,', sum(i['n'] for i in index), 'sites,', tot // 1024, 'KB')
    for i in index[:60]:
        print('%-34s sites %6d ports %7d (afdc %6d, ocm %6d) reported %7d  cov %3d%%' % (i['b'], i['n'], i['p'], i['a'], i['o'], i['rep'], 100 * i['p'] / max(1, i['rep'])))


if __name__ == '__main__':
    main()
