"""Downloads every Tesla Supercharger site from supercharge.info (community database) to .scratch/chg/supercharge_all.json.
Run:  python scripts/charging/fetch_supercharge.py"""
import os, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
out = os.path.join(ROOT, '.scratch', 'chg', 'supercharge_all.json')
os.makedirs(os.path.dirname(out), exist_ok=True)
req = urllib.request.Request('https://supercharge.info/service/supercharge/allSites', headers={'User-Agent': 'WorldAutoSalesResearch/1.0 (francois.savard@gmail.com)'})
open(out, 'wb').write(urllib.request.urlopen(req, timeout=120).read())
print('saved', out)
