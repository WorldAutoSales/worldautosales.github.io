"""Builds assets/model-class-data.js: model key -> car class, plus the shared class definitions and the brand-alias map.

Run from the repo root:  python scripts/model_class/build_model_class.py

Classes follow the EU / ACEA-style segment letters (A mini, B small, C compact, D mid-size, E-F executive & luxury,
S sports, M MPV) with SUVs split by size, plus pickup and van. There is no single official legal segmentation
(EC merger decision M.1406 letters are the de-facto standard); nameplates are assigned by the term dictionaries
dict*.txt in this folder (later files win ties, longest matching term wins, brand-qualified terms get a small bonus).
Models matching no term are left out of MODEL_CLASS and read as 'U' (unclassified) on the pages.
"""
import glob, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ORDER = ['VAN', 'PU', 'M', 'S', 'EF', 'D', 'C', 'B', 'A', 'SUVL', 'SUVS']

DEFS = [
    ['A',    'A · Mini',          'Mini / city car (EC segment A): Picanto, Seagull, Alto, Kwid, Dolphin Mini'],
    ['B',    'B · Small',         'Small car (segment B): Polo, Clio, Yaris, Dolphin, Swift'],
    ['C',    'C · Compact',       'Compact car (segment C): Golf, Corolla, Civic, ID.3, Octavia'],
    ['D',    'D · Mid-size',      'Mid-size car (segment D): Passat, Camry, Model 3, 3 Series, Seal'],
    ['EF',   'E–F · Executive',   'Executive & luxury cars (segments E and F): 5 Series, E-Class, S-Class, Panamera'],
    ['S',    'Sports',            'Sports cars and coupés (segment S): 911, Mustang, MX-5, Corvette'],
    ['M',    'MPV / minivan',     'Multi-purpose vehicles and minivans (segment M): Xpander, Carnival, Sienta, Alphard'],
    ['SUVS', 'SUV small/compact', 'B- and C-segment SUVs: RAV4, Tucson, Qashqai, Song Plus, Tiguan, Nexon'],
    ['SUVL', 'SUV mid/large',     'D-, E- and F-segment SUVs: Model Y, Highlander, X5, Land Cruiser, Palisade'],
    ['PU',   'Pickup',            'Pickup trucks: Hilux, F-150, Ranger, Silverado'],
    ['VAN',  'Van / light comm.', 'Vans and light commercial vehicles: Transit, Sprinter, Hiace, Kangoo'],
    ['U',    'Unclassified',      'Models not yet assigned to a class (the long tail, about 1% of volume)'],
]


def norm(s):
    return ' '.join(re.sub(r'[^a-z0-9#]+', ' ', s.lower()).split())


def load_terms():
    terms = []
    for f in sorted(glob.glob(os.path.join(HERE, 'dict*.txt'))):
        for line in open(f, encoding='utf8'):
            if line.startswith('#') or ':' not in line:
                continue
            cls, rest = line.split(':', 1)
            cls = cls.strip()
            if cls not in ORDER:
                continue
            for t in rest.split(','):
                t = t.strip()
                if not t or t.endswith('(no)'):
                    continue
                b = None
                if ':' in t:
                    b, t = t.split(':', 1)
                    b = norm(b)
                t = norm(t)
                if t:
                    terms.append((len(t) + (5 if b else 0), b, t, cls))
    return terms


def classify(terms, brand, model):
    nb, nm = norm(brand), norm(model)
    full = ' ' + nb + ' ' + nm + ' '
    best = None
    for ln, b, t, cls in terms:
        if b and not nb.startswith(b):
            continue
        ok = (nm == t or nm.startswith(t + ' ')) if len(t) <= 3 else (' ' + t + ' ') in full
        if ok and (best is None or ln >= best[0]):
            best = (ln, cls, t)
    return best


def main():
    # every model key of the model tables, keyed exactly like manufacturers.html's modelKey()
    js = os.path.join(HERE, 'all_model_keys.js')
    out_json = os.path.join(HERE, '_all_keys.json')
    subprocess.check_call(['node', js, ROOT, out_json])
    keys = json.load(open(out_json, encoding='utf8'))
    os.remove(out_json)
    terms = load_terms()
    mapping, vol = {}, {}
    for k, brand, model, v in keys:
        r = classify(terms, brand, model)
        if r:
            mapping[k] = r[1]
            vol[r[1]] = vol.get(r[1], 0) + v
    html = open(os.path.join(ROOT, 'manufacturers.html'), encoding='utf8').read()
    aliases = json.loads(re.search(r"const BRAND_ALIASES = (\{[^\n]*\});", html).group(1).replace("'", '"'))
    asset = ('// Car class per model nameplate (see scripts/model_class/build_model_class.py). Key = modelKey(brand, model) as used by manufacturers.html.\n'
             'const MODEL_CLASS = ' + json.dumps(mapping, separators=(',', ':')) + ';\n'
             'const MODEL_CLASS_DEFS = ' + json.dumps(DEFS, ensure_ascii=False, separators=(',', ':')) + ';\n'
             'const MODEL_CLASS_ALIASES = ' + json.dumps(aliases, ensure_ascii=False, separators=(',', ':')) + ';\n'
             "const _mcAl = x => String(x).normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');\n"
             'const _mcCache = new Map();\n'
             '// class code of a model-table row (brand, model) -- \'U\' when unclassified\n'
             'function modelClassOf(brand, model){\n'
             "  const ck = brand + '|' + model;\n"
             '  let c = _mcCache.get(ck);\n'
             '  if(c === undefined){\n'
             '    const bk = _mcAl(MODEL_CLASS_ALIASES[brand] || brand);\n'
             "    let m = _mcAl(String(model).replace(/\\s+(BEV|PHEV|HEV|ICE)$/i, ''));\n"
             '    if(m.startsWith(bk) && m.length > bk.length) m = m.slice(bk.length);\n'
             "    c = MODEL_CLASS[bk + '|' + m] || 'U'; _mcCache.set(ck, c);\n"
             '  }\n'
             '  return c;\n'
             '}\n')
    open(os.path.join(ROOT, 'assets', 'model-class-data.js'), 'w', encoding='utf8').write(asset)
    tot = sum(x[3] for x in keys)
    print(len(keys), 'model keys,', len(mapping), 'classified,', round(100 * sum(vol.values()) / tot, 1), '% of volume')
    print({k: round(v / 1e6, 1) for k, v in sorted(vol.items(), key=lambda kv: -kv[1])})


if __name__ == '__main__':
    sys.exit(main())
