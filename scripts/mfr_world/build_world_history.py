"""Builds assets/manufacturer-world-history.js (MFR_WORLD_HISTORY) and scripts/mfr_world/out/manufacturer_world_history.sql
from scripts/mfr_world/data/wikipedia_group_history_raw.json (see parse_wikipedia_group_history.py).

World volume per manufacturer GROUP and year, 2001-2025:
  basis 'p' = OICA production (cars + light/heavy commercial vehicles + buses), 2001-2017
  basis 's' = F&I Tools USA worldwide sales, 2018-2025 (light vehicles; includes joint ventures the group reports, e.g. SAIC-GM-Wuling in GM and SAIC)
The two bases are NOT the same measure (the page marks the break); groups outside the top 15-20 of a year have no figure for that year (gaps stay gaps).
Run from the repo root:  python scripts/mfr_world/build_world_history.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
raw = json.load(open(os.path.join(HERE, 'data', 'wikipedia_group_history_raw.json'), encoding='utf8'))

# canonical group -> ordered list of raw Wikipedia names that feed it ("+" parts are summed within a year, "|" alternatives: first present wins)
GROUPS = {
    'Toyota Motor Corporation': (['Toyota'], 'OICA lists Toyota without Daihatsu/Hino in the early years (e.g. 2003: 6.24 M against 7.22 M with them); F&I 2018+ is the whole group'),
    'Volkswagen Group': (['Volkswagen Group'], ''),
    'General Motors': (['General Motors'], '2018+ includes SAIC-GM-Wuling'),
    'Hyundai Motor Group': (['Hyundai Motor Group', 'Hyundai-Kia'], '2001-2002 is the Hyundai-Kia listing'),
    'Ford Motor Company': (['Ford'], '2001-2007 includes Mazda in some OICA tables'),
    'Honda': (['Honda'], ''),
    'Nissan': (['Nissan'], ''),
    'Renault Group': (['Renault'], 'no figure after 2020 (outside the F&I top 15)'),
    'BMW Group': (['BMW'], 'no figure after 2020'),
    'Mazda': (['Mazda'], 'no figure after 2020'),
    'Suzuki': (['Suzuki'], 'gap 2018-2021 (Maruti Suzuki listed separately by F&I)'),
    'Mitsubishi Motors': (['Mitsubishi'], 'to 2017'),
    'Mercedes-Benz Group': (['DaimlerChrysler', 'Daimler', 'Mercedes'], '2001-2005 is DaimlerChrysler (includes Chrysler); 2006-2017 Daimler; 2018-2020 Mercedes (F&I)'),
    'Stellantis': (None, 'Reconstructed lineage: 2001-2008 Fiat + PSA; 2009-2012 Fiat + Chrysler + PSA; 2013-2020 FCA + PSA; 2021+ Stellantis'),
    'SAIC Motor': (['SAIC Motor', 'SAIC'], 'F&I 2021+ includes SAIC-GM-Wuling; gap 2018-2020'),
    'Geely Holding': (['Geely'], 'sparse before 2018; F&I 2021+ includes Volvo Cars, Polestar, Zeekr, Lynk & Co'),
    'Changan Automobile': (['Changan'], ''),
    'BYD': (['BYD Auto'], '2022+ only in the F&I top 15'),
    'Chery Automobile': (['Chery'], '2021+ only'),
    'FAW Group': (['FAW Group', 'FAW'], 'sparse'),
    'Dongfeng Motor': (['Dongfeng Motor', 'Dongfeng'], 'to 2017'),
    'BAIC Group': (['BAIC', 'Beijing Automotive'], 'to 2017'),
    'Tata Motors': (['Tata'], '2006-2015 (includes Jaguar Land Rover)'),
    'Great Wall Motor': (['Great Wall'], '2016 only'),
}
# COMPANY-REPORTED worldwide volumes (basis 'r'), read in the companies' own filings / sales releases. They fill years the Wikipedia compilation lacks
# (Renault Group after 2020) and add groups it never lists (Tesla). For a group already present, a reported value is only used for a year with no value yet.
# group -> (note, {year: units}, source line, [approximate years])
REPORTED = {
    'Tesla': ('Company-reported deliveries (Tesla 10-K for 2019-2022, quarterly production & deliveries releases 2018 and 2023-2025); 2013-2017 rounded to the nearest 100 (sources differ by up to 0.3%)',
              {2013: 22400, 2014: 31700, 2015: 50600, 2016: 76200, 2017: 103100, 2018: 245240, 2019: 367656, 2020: 499647, 2021: 936222, 2022: 1313851, 2023: 1808581, 2024: 1789226, 2025: 1636129}),
    'Renault Group': ('2021-2025 are the group own reported sales (Renault, Dacia, Alpine, Renault Korea; 2021 also Lada and Jinbei/Huasong; Russia is out from 2022, so 2021 is not comparable)',
                      {2021: 2696401, 2022: 2051174, 2023: 2235345, 2024: 2264815, 2025: 2336807}),
}
STELLANTIS_PARTS = {
    'fiat': ['Fiat'], 'chrysler': ['Chrysler'], 'fca': ['Fiat Chrysler', 'FCA', 'Fiat-Chrysler'], 'psa': ['PSA Peugeot Citroën', 'Groupe PSA', 'PSA Group'], 'stl': ['Stellantis'],
}


def val(names, y):
    for n in names:
        v = raw.get(n, {}).get(str(y))
        if v:
            return v
    return None


out = {}
for key, (names, note) in GROUPS.items():
    s, b = {}, {}
    for y in range(2001, 2026):
        if key == 'Stellantis':
            if y >= 2021:
                v = val(STELLANTIS_PARTS['stl'], y); tot = v['v'] if v else None; bas = v['basis'] if v else None
            else:
                parts = []
                psa = val(STELLANTIS_PARTS['psa'], y)
                if y >= 2013:
                    f = val(STELLANTIS_PARTS['fca'], y); parts = [f, psa]
                elif y >= 2009:
                    parts = [val(STELLANTIS_PARTS['fiat'], y), val(STELLANTIS_PARTS['chrysler'], y), psa]
                else:
                    parts = [val(STELLANTIS_PARTS['fiat'], y), psa]
                if all(parts):
                    tot = sum(p['v'] for p in parts); bas = parts[0]['basis']
                else:
                    tot = None; bas = None
        else:
            v = val(names, y); tot = v['v'] if v else None; bas = v['basis'] if v else None
        if tot:
            s[str(y)] = tot; b[str(y)] = 'p' if bas == 'production' else 's'
    if s:
        out[key] = {'s': s, 'b': b, 'note': note}
for key, (rnote, vals) in REPORTED.items():
    d = out.setdefault(key, {'s': {}, 'b': {}, 'note': ''})
    added = 0
    for y, v in vals.items():
        if str(y) not in d['s']:
            d['s'][str(y)] = v; d['b'][str(y)] = 'r'; added += 1
    d['note'] = rnote
    d['s'] = dict(sorted(d['s'].items(), key=lambda kv: int(kv[0]))); d['b'] = {k: d['b'][k] for k in d['s']}
meta = {'years': [2001, 2025], 'p': 'OICA world ranking of manufacturers: motor vehicle production (cars, light and heavy commercial vehicles, buses), 2001-2017',
        's': 'F&I Tools USA worldwide sales by group, 2018-2025', 'r': 'Company-reported worldwide deliveries / sales (Tesla 2013-2025, Renault Group 2021-2025): see each group note', 'via': 'Wikipedia "List of automotive manufacturers by production" (compiled 2026-10-28)',
        'url': 'https://en.wikipedia.org/wiki/List_of_automotive_manufacturers_by_production'}
js = '// World volume per manufacturer group: OICA production 2001-2017, F&I Tools sales 2018-2025 (series break at 2018). Built by scripts/mfr_world/build_world_history.py\nconst MFR_WORLD_HISTORY = ' + json.dumps({'meta': meta, 'groups': out}, ensure_ascii=False, separators=(',', ':')) + ';\n'
open(os.path.join(ROOT, 'assets', 'manufacturer-world-history.js'), 'w', encoding='utf8').write(js)
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
rows = []
for g, d in out.items():
    for y, v in d['s'].items():
        rows.append("('%s',%s,%d,'%s')" % (g.replace("'", "''"), y, v, 'production' if d['b'][y] == 'p' else 'reported' if d['b'][y] == 'r' else 'sales'))
sql = ("create table if not exists public.manufacturer_world_history (group_name text not null, year integer not null, volume bigint not null, basis text not null check (basis in ('production','sales','reported')),\n"
       "  source text not null default 'Wikipedia (OICA production 2001-2017, F&I Tools sales 2018-2025), compiled 2026-10-28', primary key (group_name, year));\n"
       "alter table public.manufacturer_world_history enable row level security;\n"
       "comment on table public.manufacturer_world_history is 'World volume per manufacturer group and year: OICA production 2001-2017 (all motor vehicles), F&I Tools sales 2018-2025; the two bases differ. Built by scripts/mfr_world/build_world_history.py.';\n"
       "insert into public.manufacturer_world_history (group_name, year, volume, basis) values\n" + ',\n'.join(rows) + "\non conflict (group_name, year) do update set volume = excluded.volume, basis = excluded.basis;\n")
open(os.path.join(HERE, 'out', 'manufacturer_world_history.sql'), 'w', encoding='utf8').write(sql)
print(len(out), 'groups,', len(rows), 'rows,', len(js) // 1024, 'KB')
for g, d in out.items():
    ys = sorted(d['s'], key=int)
    print('%-26s %s-%s (%d yrs)' % (g, ys[0], ys[-1], len(ys)))
