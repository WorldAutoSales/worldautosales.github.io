"""Downloads the station names of Open Charge Map for countries whose operator field is mostly empty (the NOBIL import of Norway/Sweden, Finland...).
Writes .scratch/chg/ocm/<ISO2>.names.json : {poi id: "title | address line"} -- used by ocm_names.name_brand() to attribute stations whose operator is
unknown from their name (e.g. "Circle K Lysaker", "Uno-X Steinkjer").  Needs the OCM key in .scratch/chg/ocm.key.
Run from the repo root:  python scripts/charging/fetch_ocm_names.py NO SE DK FI
"""
import json, os, sys, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, '.scratch', 'chg')
KEY = open(os.path.join(CACHE, 'ocm.key')).read().strip()
DEFAULT = ['NO', 'SE', 'DK', 'FI', 'EE', 'LV', 'LT', 'PL', 'IE']

for iso in (sys.argv[1:] or DEFAULT):
    req = urllib.request.Request('https://api.openchargemap.io/v3/poi?countrycode=%s&maxresults=60000&compact=false&verbose=false' % iso, headers={'X-API-Key': KEY, 'User-Agent': 'world-auto-sales-research/1.0'})
    d = json.loads(urllib.request.urlopen(req, timeout=600).read())
    names = {}
    for x in d:
        a = x.get('AddressInfo') or {}
        names[x['ID']] = ((a.get('Title') or '') + ' | ' + (a.get('AddressLine1') or '')).strip()
    json.dump(names, open(os.path.join(CACHE, 'ocm', iso + '.names.json'), 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print(iso, len(names))
