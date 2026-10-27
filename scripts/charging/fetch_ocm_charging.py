"""Downloads every Open Charge Map POI per country (compact JSON: operator id, number of points, connections with kW, position)
into .scratch/chg/ocm/<ISO2>.json (git-ignored raw cache), plus the reference data (operators, connection types, status types).
The API key lives in .scratch/chg/ocm.key (never committed). OCM data: Open Charge Map contributors, CC BY 4.0 / ODbL by provider.
Run:  python scripts/charging/fetch_ocm_charging.py [ISO2 ...]
"""
import json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CACHE = os.path.join(ROOT, '.scratch', 'chg')
OUT = os.path.join(CACHE, 'ocm')
KEY = open(os.path.join(CACHE, 'ocm.key')).read().strip()
UA = 'WorldAutoSalesResearch/1.0 (francois.savard@gmail.com)'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from charging_sources import COUNTRIES  # noqa: E402


def get(url):
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={'X-API-Key': KEY, 'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read().decode('utf8'))
        except Exception as e:  # noqa: BLE001
            last = e
            print('  retry', url[-60:], attempt, repr(e)[:100], flush=True)
            time.sleep(20 * (attempt + 1))
    raise RuntimeError(repr(last))


def main():
    os.makedirs(OUT, exist_ok=True)
    ref = os.path.join(CACHE, 'refdata.json')
    if not os.path.exists(ref):
        json.dump(get('https://api.openchargemap.io/v3/referencedata'), open(ref, 'w'), separators=(',', ':'))
    todo = [a.upper() for a in sys.argv[1:]] or list(COUNTRIES)
    for iso in todo:
        f = os.path.join(OUT, iso + '.json')
        if os.path.exists(f):
            continue
        t0 = time.time()
        d = get('https://api.openchargemap.io/v3/poi?output=json&countrycode=%s&maxresults=300000&compact=true&verbose=false' % iso)
        json.dump(d, open(f, 'w', encoding='utf8'), separators=(',', ':'))
        print(iso, len(d), 'POIs', round(time.time() - t0), 's', flush=True)
        time.sleep(3)


if __name__ == '__main__':
    main()
