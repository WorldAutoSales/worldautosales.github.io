"""Builds the data of the charging stations page.

Inputs (raw caches, see fetch_ocm_charging.py / fetch notes in the log):
  scripts/charging/data/iea/*.json      IEA Global EV Data Explorer API (public charging points slow / fast / ultra-fast, EV stock)
  .scratch/chg/ocm/<ISO2>.json          Open Charge Map POIs per country (+ refdata.json)
  .scratch/chg/supercharge_all.json     supercharge.info (Tesla Supercharger sites)
  assets/population-energy-data.js      population 15-64 (workPop)
  charging_sources.py                   country table, US AFDC official counts
Outputs:
  assets/charging-data.js               CHARGING  (country table, IEA series, OCM brand/power splits, Tesla, official counts)
  assets/charging-grid-data.js          CHARGING_GRID (0.5 degree cells of OCM ports, for the map)
  assets/charging-tesla-sites-data.js   TESLA_SITES (open Supercharger sites: lat, lon, stalls, kW)
  scripts/charging/out/charging_*.sql   Supabase load (charging_country_year, charging_country_brand)
Run from the repo root:  python scripts/charging/build_charging.py
"""
import json, os, re, sys, unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from charging_sources import COUNTRIES, OFFICIAL, AFDC_NETWORKS_NA  # noqa: E402
from charging_sql import write_sql  # noqa: E402

IEA = os.path.join(HERE, 'data', 'iea')
CACHE = os.path.join(ROOT, '.scratch', 'chg')
YEARS = [2019, 2022, 2023, 2024, 2025]
BANDS = ['<50 kW', '50-99 kW', '100-249 kW', '250-349 kW', '350+ kW']
SNAPSHOT = '2026-10-27'

# ---- brand normalisation (OCM operator titles -> one brand)
ALIASES = [
    (r'^tesla', 'Tesla'), (r'chargepoint', 'ChargePoint'), (r'^blink', 'Blink'), (r'^flo$|^flo ', 'FLO'), (r'circuit electrique|circuit .lectrique', 'Circuit électrique'),
    (r'iberdrola|bp pulse|bp ?pulse|chargemaster|polar ', 'bp pulse'), (r'enel x|enel way|enel', 'Enel X Way'), (r'evgo', 'EVgo'), (r'pod ?point', 'Pod Point'),
    (r'ev ?connect', 'EV Connect'), (r'^loop', 'Loop'), (r'shell recharge|newmotion|greenlots|shell ', 'Shell Recharge'), (r'electrify america', 'Electrify America'),
    (r'power ?dot', 'PowerDot'), (r'allego', 'Allego'), (r'endesa', 'Endesa X'), (r'mercadona', 'Mercadona'), (r'r.v.o|reveo', 'Révéo'), (r'innogy|rwe', 'RWE / innogy'),
    (r'mobie', 'MOBI.E'), (r'ionity', 'IONITY'), (r'^enbw', 'EnBW'), (r'ladenetz', 'ladenetz'), (r'swtch', 'SWTCH'), (r'vialynk|lynkwell', 'ViaLynk'),
    (r'izivia|sodetrel', 'Izivia'), (r'ampup', 'AmpUp'), (r'chargeplace scotland', 'ChargePlace Scotland'), (r'red e charge', 'Red E Charge'), (r'evnetnl', 'EVnetNL'),
    (r'char\.gy', 'char.gy'), (r'evgateway', 'EVGateway'), (r'^electra', 'Electra'), (r'powerflex', 'PowerFlex'), (r'be charge', 'Be Charge'), (r'^edp', 'EDP'),
    (r'repsol|ibil', 'Repsol'), (r'total ?energies|^total ', 'TotalEnergies'), (r'evbox', 'EVBox'), (r'zunder', 'Zunder'), (r'semaconnect', 'SemaConnect'),
    (r'opconnect', 'OpConnect'), (r'freshmile', 'Freshmile'), (r'^eborn', 'Eborn'), (r'atlante', 'Atlante'), (r'fastned', 'Fastned'), (r'e\.?on ', 'E.ON Drive'),
    (r'vattenfall|incharge', 'Vattenfall InCharge'), (r'^recharge', 'Recharge'), (r'^mer$|^mer ', 'Mer'), (r'^ionna', 'IONNA'), (r'rivian', 'Rivian'),
    (r'electric highway|ecotricity', 'Ecotricity Electric Highway'), (r'instavolt', 'InstaVolt'), (r'osprey', 'Osprey'), (r'gridserve', 'GRIDSERVE'),
    (r'virta', 'Virta'), (r'smatrics', 'SMATRICS'), (r'monta', 'Monta'), (r'plugsurfing', 'Plugsurfing'), (r'esb ecars', 'ESB ecars'), (r'ezo', 'EZO'),
    (r'chargefox', 'Chargefox'), (r'evie', 'Evie Networks'), (r'noodoe', 'Noodoe'), (r'evcs', 'EVCS'), (r'ev ?go', 'EVgo'), (r'^nio', 'NIO Power'),
    (r'state grid|national grid', 'State Grid'), (r'teld|telai|特来电', 'TELD'), (r'star ?charge|xingxing', 'Star Charge'), (r'^pln', 'PLN'), (r'otopriz', 'Otopriz'),
    (r'zes |zorlu', 'ZES'), (r'e-?sarj|eşarj', 'Eşarj'), (r'trugo', 'Trugo'), (r'lidl', 'Lidl'), (r'engie', 'Engie'), (r'ewe ', 'EWE'),
]
UNKNOWN = 'Unknown operator'
SELF = 'Independent / business owner'


def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower().strip()
    return s


def brand_of(title):
    if not title:
        return UNKNOWN
    if title.startswith('(Unknown'):
        return UNKNOWN
    if title.startswith('(Business Owner'):
        return SELF
    if title.startswith('Stadtwerke Clausthal'):
        return UNKNOWN     # OCM files stations of several countries (JP, DK, SG...) under this German utility by mistake
    t = norm(title)
    for rx, name in ALIASES:
        if re.search(rx, t):
            return name
    t = re.sub(r'\s*\([^)]*\)\s*', ' ', title).strip()   # drop "(UK)", "(DE)" country suffixes
    return t[:40] or UNKNOWN


def band_of(kw):
    if kw is None or kw < 50:
        return 0
    if kw < 100:
        return 1
    if kw < 250:
        return 2
    if kw < 350:
        return 3
    return 4


def load_iea():
    out = defaultdict(lambda: defaultdict(dict))
    for kind, fn in (('slow', 'slow'), ('fast', 'fast'), ('ultra', 'ultra-fast')):
        for y in YEARS:
            for r in json.load(open(os.path.join(IEA, 'iea_cp_%s_%d.json' % (fn, y)))):
                out[r['region']][y][kind] = r['value']
    stock = defaultdict(dict)
    for pw in ('BEV', 'PHEV'):
        for y in (2024, 2025):
            for r in json.load(open(os.path.join(IEA, 'iea_stock_%s_%d.json' % (pw, y)))):
                stock[r['region']][(pw, y)] = r['value']
    return out, stock


def load_pop():
    t = open(os.path.join(ROOT, 'assets', 'population-energy-data.js'), encoding='utf8').read()
    d = json.loads(re.search(r'const POPULATION_ENERGY = (\{.*\});', t, re.S).group(1))
    return d


def tesla():
    sites = json.load(open(os.path.join(CACHE, 'supercharge_all.json')))
    by = defaultdict(lambda: {'sites': 0, 'stalls': 0, 'b': [0] * 5})
    pts = []
    names = {v[2]: iso for iso, v in COUNTRIES.items() if v[2]}
    for s in sites:
        if s['status'] != 'OPEN':
            continue
        c = s['address']['country']
        kw = s.get('powerKilowatt') or 0
        e = by[c]
        e['sites'] += 1
        e['stalls'] += s['stallCount']
        e['b'][band_of(kw)] += s['stallCount']
        pts.append([round(s['gps']['latitude'], 3), round(s['gps']['longitude'], 3), s['stallCount'], kw, names.get(c, '')])
    return by, pts


def ocm_country(iso, ops, usage):
    f = os.path.join(CACHE, 'ocm', iso + '.json')
    if not os.path.exists(f):
        return None, []
    st = po = 0
    bands = [0] * 5
    brands = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])   # stations, ports, then 5 bands
    cells = defaultdict(lambda: [0, 0, 0])
    for p in json.load(open(f, encoding='utf8')):
        if p.get('StatusTypeID') in (100, 150, 200, 210):
            continue
        if 'Private' in usage.get(p.get('UsageTypeID'), ''):
            continue
        conns = p.get('Connections') or []
        q = sum((c.get('Quantity') or 1) for c in conns) or 1
        n = p.get('NumberOfPoints') or q
        # spread the ports over the power bands in proportion to the connectors
        alloc = [0.0] * 5
        for c in conns or [{'PowerKW': None, 'Quantity': 1}]:
            alloc[band_of(c.get('PowerKW'))] += (c.get('Quantity') or 1)
        tot = sum(alloc) or 1
        alloc = [a * n / tot for a in alloc]
        b = brand_of(ops.get(p.get('OperatorID')))
        st += 1
        po += n
        for i in range(5):
            bands[i] += alloc[i]
        e = brands[b]
        e[0] += 1
        e[1] += n
        for i in range(5):
            e[2 + i] += alloc[i]
        ai = p.get('AddressInfo') or {}
        if ai.get('Latitude') is not None and ai.get('Longitude') is not None:
            k = (int(ai['Longitude'] // 0.5), int(ai['Latitude'] // 0.5))
            cells[k][0] += 1
            cells[k][1] += n
            cells[k][2] += sum(alloc[1:])
    top = sorted(brands.items(), key=lambda kv: -kv[1][1])
    keep = [(k, v) for k, v in top[:14]]
    rest = [v for k, v in top[14:]]
    out = [[k] + [round(x) for x in v] for k, v in keep]
    if rest:
        out.append(['Other brands'] + [round(sum(v[i] for v in rest)) for i in range(7)])
    return {'st': st, 'po': round(po), 'bands': [round(x) for x in bands], 'brands': out}, cells


def main():
    iea, stock = load_iea()
    pop = load_pop()
    ref = json.load(open(os.path.join(CACHE, 'refdata.json')))
    ops = {o['ID']: o['Title'] for o in ref['Operators']}
    usage = {u['ID']: u['Title'] for u in ref['UsageTypes']}
    tby, tpts = tesla()
    countries, grid = [], {}
    for iso, (name, iea_name, tname) in COUNTRIES.items():
        e = {'n': name, 'iso': iso}
        pe = pop.get(name)
        if pe:
            e['pop'] = pe.get('population')
            e['w'] = pe.get('workPop')
            e['cont'] = pe.get('continent')
        if iea_name and iea_name in iea:
            e['iea'] = {str(y): [iea[iea_name][y].get('slow'), iea[iea_name][y].get('fast'), iea[iea_name][y].get('ultra')] for y in YEARS if y in iea[iea_name]}
            e['ev'] = {str(y): [stock[iea_name].get(('BEV', y)), stock[iea_name].get(('PHEV', y))] for y in (2024, 2025)}
        if iso in OFFICIAL:
            e['off'] = OFFICIAL[iso]
        if tname and tname in tby:
            t = tby[tname]
            e['tesla'] = {'sites': t['sites'], 'stalls': t['stalls'], 'b': t['b']}
        o, cells = ocm_country(iso, ops, usage)
        if o:
            e['ocm'] = o
            for (x, y), v in cells.items():
                grid.setdefault((x, y), [0, 0, 0])
                for i in range(3):
                    grid[(x, y)][i] += v[i]
        countries.append(e)
    meta = {'snapshot': SNAPSHOT, 'ieaYear': 2025, 'years': YEARS, 'bands': BANDS,
            'afdcNetworks': AFDC_NETWORKS_NA,
            'sources': {'iea': 'IEA Global EV Data Explorer / Global EV Outlook 2026 (CC BY 4.0): public charging points; slow <=22 kW, fast 22-150 kW, ultra-fast >150 kW',
                        'ocm': 'Open Charge Map (open registry of charging locations, crowd-sourced and imported from operators; coverage varies by country)',
                        'tesla': 'supercharge.info (community database of Tesla Supercharger sites)',
                        'afdc': 'US DOE Alternative Fuels Data Center'}}
    js = '// Public EV charging by country. Built by scripts/charging/build_charging.py -- see the notes card on charging-stations.html for sources and caveats.\nconst CHARGING = ' + json.dumps({'meta': meta, 'countries': countries}, ensure_ascii=False, separators=(',', ':')) + ';\n'
    open(os.path.join(ROOT, 'assets', 'charging-data.js'), 'w', encoding='utf8').write(js)
    cells = sorted(([x, y] + v for (x, y), v in grid.items()), key=lambda r: (r[0], r[1]))
    open(os.path.join(ROOT, 'assets', 'charging-grid-data.js'), 'w', encoding='utf8').write(
        '// Open Charge Map, 0.5 degree cells: [lonIndex, latIndex, stations, ports, ports>=50kW] (lon = index*0.5, lat = index*0.5 = south-west corner)\nconst CHARGING_GRID = ' + json.dumps([[a, b, c, round(d), round(e)] for a, b, c, d, e in cells], separators=(',', ':')) + ';\n')
    open(os.path.join(ROOT, 'assets', 'charging-tesla-sites-data.js'), 'w', encoding='utf8').write(
        '// Open Tesla Supercharger sites (supercharge.info, %s): [lat, lon, stalls, kW, ISO2]\nconst TESLA_SITES = ' % SNAPSHOT + json.dumps(tpts, separators=(',', ':')) + ';\n')
    print('sql rows (year, snapshot, brand):', write_sql(countries, SNAPSHOT, os.path.join(HERE, 'out')))
    n_ocm = sum(1 for c in countries if 'ocm' in c)
    print(len(countries), 'countries,', n_ocm, 'with OCM,', len(cells), 'grid cells,', len(tpts), 'tesla sites')
    for c in sorted(countries, key=lambda c: -(c.get('ocm', {}).get('po', 0)))[:12]:
        print(c['n'], c.get('ocm', {}).get('st'), c.get('ocm', {}).get('po'), (c.get('iea') or {}).get('2025'))


if __name__ == '__main__':
    main()
