"""Brand attribution from the station name, for Open Charge Map stations whose operator field is empty ("Unknown operator").
Open Charge Map's NOBIL import (Norway, Sweden, Finland...) keeps the station name -- often the forecourt or retailer ("Circle K Lysaker",
"Uno-X Steinkjer", "Ishavsveien - Shell Talvik") -- but drops the operator.  Only well-known fuel and charging brands are matched, with word
boundaries; retail chains whose name says who hosts the charger but not who runs it (Kiwi, Coop, Rema...) are left unknown.
A match means "charger on a site of this brand", which can include partner-run chargers (Circle K Norway hosts Tesla and IONITY units too)."""
import json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, '.scratch', 'chg', 'ocm')

RULES = [
    (r'\bcircle ?k\b|\bcouche-?tard\b', 'Couche-Tard / Circle K'),
    (r'\buno-?x\b|\byx\b', 'Uno-X'),
    (r'\besso\b', 'Esso'),
    (r'\bshell\b', 'Shell Recharge'),
    (r'\bst1\b', 'St1'),
    (r'\bneste\b', 'Neste Lataus'),
    (r'\bpreem\b', 'Preem'),
    (r'\bokq8\b', 'OKQ8'),
    (r'\bingo\b', 'Ingo'),
    (r'\bionity\b', 'IONITY'),
    (r'\bfortum\b', 'Fortum'),
    (r'\brecharge\b', 'Recharge'),
    (r'\beviny\b', 'Eviny'),
    (r'\bkople\b', 'Kople'),
    (r'\bgr.nn kontakt\b', 'Grønn Kontakt'),
    (r'\bchargeup\b', 'ChargeUp'),
    (r'\bpwr ?up\b', 'PWR UP'),
    (r'\bvirta\b', 'Virta'),
    (r'\bk-?lataus\b', 'K Lataus'),
    (r'\babc\b', 'ABC Lataus'),
    (r'\blidl\b', 'Lidl'),
    (r'\bkaufland\b', 'Kaufland eCharge'),
    (r'\borlen\b', 'Orlen'),
    (r'\bapplegreen\b', 'Applegreen Fast Charge'),
]
_rx = [(re.compile(p, re.I), b) for p, b in RULES]
_cache = {}


def names(iso):
    if iso not in _cache:
        f = os.path.join(CACHE, iso + '.names.json')
        _cache[iso] = {int(k): v for k, v in json.load(open(f, encoding='utf8')).items()} if os.path.exists(f) else {}
    return _cache[iso]


def name_brand(iso, poi_id):
    t = names(iso).get(poi_id)
    if not t:
        return None
    for rx, b in _rx:
        if rx.search(t):
            return b
    return None
