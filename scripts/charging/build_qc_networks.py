"""Builds assets/charging-qc-networks-data.js: site-level positions for Circuit électrique and Couche-Tard / Circle K (Canada).

Sources (both public, no login):
  * AFDC / NRCan station locator API (developer.nlr.gov, DEMO_KEY), ev_network "Circuit électrique" and "COUCHE_TARD"
    -> cached as .scratch/chg/qc/afdc_ca.json  (curl -G "https://developer.nlr.gov/api/alt-fuel-stations/v1.json" -d api_key=DEMO_KEY -d fuel_type=ELEC -d country=CA -d limit=all)
  * Open Charge Map cache .scratch/chg/ocm/CA.json (operator 90 = Circuit Electrique, 3510 = Circle K), added where no AFDC site of the
    same network lies within 120 m.
The Circuit électrique API behind lecircuitelectrique.com (api.lecircuitelectrique.com) needs a token held by their app, so it is not used.
Output rows: [lat, lon, ports, fast_ports]  (ports = DC fast + level 2 + level 1 EVSE; OCM rows use NumberOfPoints / kW>=50)
"""
import json, math, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
afdc = json.load(open(os.path.join(ROOT, '.scratch/chg/qc/afdc_ca.json'), encoding='utf8'))['fuel_stations']
ocm = json.load(open(os.path.join(ROOT, '.scratch/chg/ocm/CA.json'), encoding='utf8'))
SNAPSHOT = '2026-10-27'

def ports(s):
    f = s.get('ev_dc_fast_num') or 0
    return f + (s.get('ev_level2_evse_num') or 0) + (s.get('ev_level1_evse_num') or 0), f

sites = {'ce': [], 'ct': []}
for s in afdc:
    net = s.get('ev_network') or ''
    name = (s.get('station_name') or '')
    k = 'ce' if net == 'Circuit électrique' else 'ct' if (net == 'COUCHE_TARD' or re.match(r'\s*(couche-?tard|circle ?k)\b', name, re.I)) else None
    if not k or s.get('latitude') is None or s.get('status_code') != 'E': continue
    p, f = ports(s)
    sites[k].append([round(s['latitude'], 5), round(s['longitude'], 5), max(p, 1), f])
afdc_n = {k: len(v) for k, v in sites.items()}

def near(k, lat, lon, m=120):
    dl = m / 111000.0
    dn = dl / max(0.2, math.cos(math.radians(lat)))
    return any(abs(r[0] - lat) < dl and abs(r[1] - lon) < dn for r in sites[k])

OPS = {90: 'ce', 3510: 'ct'}
added = {'ce': 0, 'ct': 0}
for x in ocm:
    k = OPS.get(x.get('OperatorID'))
    a = x.get('AddressInfo') or {}
    if not k or a.get('Latitude') is None or x.get('StatusTypeID') in (100, 150, 200, 210): continue   # skip planned / removed / not operational
    lat, lon = a['Latitude'], a['Longitude']
    if near(k, lat, lon): continue
    conns = x.get('Connections') or []
    p = x.get('NumberOfPoints') or sum(c.get('Quantity') or 1 for c in conns) or 1
    f = sum((c.get('Quantity') or 1) for c in conns if (c.get('PowerKW') or 0) >= 50)
    sites[k].append([round(lat, 5), round(lon, 5), p, min(f, p)])
    added[k] += 1

print('AFDC', afdc_n, 'OCM added', added, 'total', {k: len(v) for k, v in sites.items()},
      'ports', {k: sum(r[2] for r in v) for k, v in sites.items()})
out = ('// Circuit électrique and Couche-Tard / Circle K charging sites in Canada (AFDC/NRCan locator + Open Charge Map, %s): [lat, lon, ports, fast ports]\n'
       'const QC_NETWORKS = ' % SNAPSHOT) + json.dumps(sites, separators=(',', ':')) + ';\n'
open(os.path.join(ROOT, 'assets', 'charging-qc-networks-data.js'), 'w', encoding='utf8').write(out)
print(len(out) // 1024, 'KB')
