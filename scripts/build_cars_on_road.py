#!/usr/bin/env python3
"""
Rebuilds the on-road passenger-car fleet table (country_cars_on_road / assets/country-cars-on-road-data.js).

Method (v2, 2026-10-16)
  1. Registrations per country and year (2005-2026): total from auto-markets-by-country.html MARKETS.series
     (+ 2026 projection), BEV from assets/country-yearly-data.js. China 2005-2020 = OICA domestic passenger
     cars (scripts/data/china_domestic_pc_2005_2020.json), 2021+ = CPCA retail already in MARKETS.
     Cohorts before 2005 are back-cast: R(y) = R(2005) * exp(-g*(2005-y)), g = own 2005-2010 growth clamped to [0, 25%].
  2. Survival curve per country = the country's own curve in cars_duration_rate when real statistics exist
     (Germany, Norway, United Kingdom, Netherlands, Japan, China, United States), otherwise its region average
     (scripts/data/cars_duration_curves.json mirrors the DB table; CURVE_KEY below maps country -> curve).
     Curves give the share of a cohort still on the road at age 1..25; age 0 = 100%; cars older than 25 are not counted.
  3. Modelled stock(t) = sum_y R(y) * S(t - y), BEV and non-BEV separately.
  4. Real fleet anchors (scripts/data/fleet_real_anchors.json: Eurostat road_eqs_carage / road_eqs_carpda 2013-2025,
     DfT VEH1111 for Great Britain 2005-2025) replace the model in the years they cover (method REAL). Years before the
     first anchor are the model scaled to match it (MODEL_ANCHORED_BACK); years after the last anchor up to 2026 are the
     model scaled by the last real/model ratio (MODEL_ANCHORED). Countries without anchors are pure model (MODEL_RAW).
  5. 2027-2041: total stock is held constant at the anchor year (2026) total; each year's new registrations are
     whatever replaces the vehicles ageing out; BEV share of new registrations follows a logistic (odds-ratio) path
     whose growth rate is calibrated on 2024->2026, borrowed from a regional comparator (Germany: Europe/Middle East;
     China: everything else) when the own base is < 15% and the own rate is higher, floored at 0 and decayed with a
     6-year half-life.
Usage: python scripts/build_cars_on_road.py [--write]   (default: dry run, prints a summary)
"""
import json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'scripts' / 'data'
FIRST, END = 2005, 2041

CURVE_KEY = {}
for c in ('Germany', 'Norway', 'United Kingdom', 'Netherlands', 'Japan', 'China', 'United States'):
    CURVE_KEY[c] = c
CURVE_KEY['Canada'] = 'North America'
for c in ('Australia', 'New Zealand'): CURVE_KEY[c] = 'Oceania'
for c in ('Argentina', 'Brazil', 'Chile', 'Colombia', 'Ecuador', 'Mexico', 'Peru'): CURVE_KEY[c] = 'Latin America'
for c in ('Morocco', 'South Africa'): CURVE_KEY[c] = 'Africa'
for c in ('Israel', 'Turkey'): CURVE_KEY[c] = 'Middle East'
for c in ('Czechia', 'Hungary', 'Poland', 'Romania', 'Russian Federation', 'Slovakia'): CURVE_KEY[c] = 'East Europe'
for c in ('Austria', 'Belgium', 'Denmark', 'Finland', 'France', 'Greece', 'Ireland', 'Italy', 'Portugal', 'Spain', 'Sweden', 'Switzerland'): CURVE_KEY[c] = 'West Europe'
for c in ('India', 'Indonesia', 'Kazakhstan', 'Malaysia', 'Philippines', 'Singapore', 'South Korea', 'Taiwan', 'Thailand', 'Uzbekistan', 'Vietnam'): CURVE_KEY[c] = 'Asia (rest)'
EUROPE_GROUP = {'West Europe', 'East Europe', 'Middle East', 'Germany', 'Norway', 'United Kingdom', 'Netherlands'}


def load_markets():
    t = (ROOT / 'auto-markets-by-country.html').read_text(encoding='utf-8')
    out = {}
    for m in re.finditer(r'"([^"]+)":\{abbr:"(\w+)",continent:"([^"]+)",series:(\{[^}]*\}),projected:(\{[^}]*\})', t):
        name, ab, cont, ser, proj = m.groups()
        out[name] = dict(series={int(k): v for k, v in json.loads(ser).items()},
                         projected={int(k): v for k, v in (json.loads(proj) if proj.strip() != '{}' else {}).items()})
    return out


def load_yearly():
    t = (ROOT / 'assets' / 'country-yearly-data.js').read_text(encoding='utf-8')
    return json.loads(re.search(r'=\s*(\{.*\});', t, re.S).group(1))


MK, YR = load_markets(), load_yearly()
CURVES = json.load(open(DATA / 'cars_duration_curves.json'))
ANCH = json.load(open(DATA / 'fleet_real_anchors.json'))
CN = {int(k): v for k, v in json.load(open(DATA / 'china_domestic_pc_2005_2020.json'))['series'].items()}


def survival(curve):
    def S(a):
        if a < 0: return 0.0
        if a == 0: return 1.0
        return curve[a - 1] / 100 if a <= 25 else 0.0   # cars older than 25 years are not counted
    return S


def registrations(c):
    m = MK[c]
    tot = dict(m['series'])
    if c == 'China':
        for y, v in CN.items(): tot[y] = v
    if 2026 in m['projected']: tot[2026] = m['projected'][2026]
    bev = {}
    for r in YR.get(c, []):
        if r['period_type'] == 'ANNUAL' and r.get('bev') is not None: bev[r['year']] = r['bev']
        if r['period_type'] == 'PROJECTED' and r['year'] == 2026 and r.get('bev') is not None: bev[2026] = r['bev']
    filled = []
    first = min(tot)
    for y in range(FIRST, first):          # e.g. Taiwan: flat back-fill of its first value
        tot[y] = tot[first]; filled.append(y)
    for y in range(FIRST, 2026):           # interpolate interior gaps
        if y not in tot:
            lo = max(k for k in tot if k < y); hi = min(k for k in tot if k > y)
            tot[y] = tot[lo] + (tot[hi] - tot[lo]) * (y - lo) / (hi - lo); filled.append(y)
    anchor_year = 2026 if 2026 in tot else max(tot)
    r5, r10 = tot[2005], tot.get(2010, tot[2005])
    g = min(max(math.log(r10 / r5) / 5, 0.0), 0.25) if r5 > 0 and r10 > 0 else 0.0
    for y in range(1980, 2005): tot[y] = r5 * math.exp(-g * (2005 - y))
    return tot, bev, anchor_year, g, filled


def model(tot, bev, S, years):
    out = {}
    for t in years:
        b = n = 0.0
        for y in range(1980, t + 1):
            if y not in tot: continue
            by = bev.get(y, 0.0)
            b += by * S(t - y); n += (tot[y] - by) * S(t - y)
        out[t] = (b, n)
    return out


def odds(p): return p / (1 - p)


def own_rate(tot, bev, T):
    def share(y):
        return bev.get(y, 0) / tot[y] if y in tot and tot[y] > 0 else None
    s0, s1 = share(T), share(2024)
    if s0 is None or s1 is None or s0 <= 0 or s1 <= 0 or T <= 2024: return None, s0
    return (math.log(odds(s0)) - math.log(odds(s1))) / (T - 2024), s0


def build():
    prep = {}
    for c in CURVE_KEY:
        tot, bev, T, g_back, filled = registrations(c)
        prep[c] = dict(tot=tot, bev=bev, T=T, g_back=g_back, filled=filled)
        prep[c]['g_own'], prep[c]['s0'] = own_rate(tot, bev, T)
    comp = {'Europe': max(prep['Germany']['g_own'] or 0, 0), 'Other': max(prep['China']['g_own'] or 0, 0)}
    rows, info = {}, {}
    for c in CURVE_KEY:
        p = prep[c]; tot, bev, T = p['tot'], p['bev'], p['T']
        key = CURVE_KEY[c]; S = survival(CURVES[key])
        mod = model(tot, bev, S, range(FIRST, T + 1))
        anc = {int(y): v for y, v in ANCH.get(c, {}).items() if FIRST <= int(y) <= T}
        res = {}
        if anc:
            fy, ly = min(anc), max(anc)
            f_first = anc[fy]['total'] / (mod[fy][0] + mod[fy][1])
            f_last = anc[ly]['total'] / (mod[ly][0] + mod[ly][1])
            fb_last = (anc[ly]['bev'] / mod[ly][0]) if anc[ly].get('bev') is not None and mod[ly][0] > 0 else f_last
            # real/model ratio drifts over time (used-car trade, short registrations): extrapolate its recent trend to T
            pts = [(y, anc[y]['total'] / (mod[y][0] + mod[y][1])) for y in sorted(anc) if y >= ly - 6]
            slope = 0.0
            if len(pts) >= 3:
                mx = sum(y for y, _ in pts) / len(pts); my = sum(v for _, v in pts) / len(pts)
                slope = sum((y - mx) * (v - my) for y, v in pts) / sum((y - mx) ** 2 for y, _ in pts)
            def f_at(t):
                return min(max(f_last + slope * (t - ly), 0.94 * f_last), 1.06 * f_last) if t > ly else f_last
            for t in range(FIRST, T + 1):
                b, n = mod[t]
                if t in anc:
                    a = anc[t]
                    bb = a['bev'] if a.get('bev') is not None else b * (a['total'] / (b + n))
                    res[t] = (bb, a['total'] - bb, 'REAL')
                elif t < fy:
                    res[t] = (b * f_first, n * f_first, 'MODEL_ANCHORED_BACK')
                elif t < ly:   # between two real anchors: interpolate the real/model ratio
                    lo = max(y for y in anc if y < t); hi = min(y for y in anc if y > t)
                    flo = anc[lo]['total'] / (mod[lo][0] + mod[lo][1]); fhi = anc[hi]['total'] / (mod[hi][0] + mod[hi][1])
                    ft = flo + (fhi - flo) * (t - lo) / (hi - lo); bb = min(b * fb_last, (b + n) * ft)
                    res[t] = (bb, (b + n) * ft - bb, 'MODEL_ANCHORED_BACK')
                else:
                    ft = f_at(t); bb = min(b * fb_last, (b + n) * ft)
                    res[t] = (bb, (b + n) * ft - bb, 'MODEL_ANCHORED')
            F, Fb = f_at(T), fb_last
        else:
            for t in range(FIRST, T + 1): res[t] = (mod[t][0], mod[t][1], 'MODEL_RAW')
            F, Fb = 1.0, 1.0
        total_T = res[T][0] + res[T][1]
        g_own, s0 = p['g_own'], p['s0']
        g_c = comp['Europe'] if key in EUROPE_GROUP else comp['Other']
        if c in ('Germany', 'China'): g = g_own if g_own is not None else g_c
        elif g_own is None: g = g_c
        elif s0 is not None and s0 < 0.15 and g_own > g_c: g = g_c
        else: g = g_own
        g = max(g, 0.0)
        share = min(max(s0 or 0.0, 1e-6), 0.99)
        newreg, bev_new = {}, {}
        Rb = {y: bev.get(y, 0.0) for y in range(1980, T + 1)}
        for Y in range(T + 1, END + 1):
            k = Y - T
            o = odds(share) * math.exp(g * 0.5 ** (k / 6))
            share = min(o / (1 + o), 0.995)
            e_tot = F * sum(tot[cc] * S(Y - cc) for cc in range(1980, T + 1)) + sum(newreg[cc] * S(Y - cc) for cc in range(T + 1, Y))
            N = max(total_T - e_tot, 0.0)
            newreg[Y] = N; bev_new[Y] = N * share
            b_Y = Fb * sum(Rb[cc] * S(Y - cc) for cc in range(1980, T + 1)) + sum(bev_new[cc] * S(Y - cc) for cc in range(T + 1, Y + 1))
            b_Y = min(b_Y, total_T)
            res[Y] = (b_Y, total_T - b_Y, 'MODEL_STOCK_CONSTANT_WITH_FUTURE_REG')
        rows[c] = []
        for y in sorted(res):
            d = dict(year=y, bev=round(res[y][0]), nonBev=round(res[y][1]), method=res[y][2])
            if y in newreg: d['futureNewRegProj'] = round(newreg[y])
            rows[c].append(d)
        info[c] = dict(curve=key, anchored=bool(anc), anchor_years=[min(anc), max(anc)] if anc else None, T=T,
                       g=round(g, 3), g_own=None if g_own is None else round(g_own, 3), share0=None if s0 is None else round(s0, 3),
                       backcast_g=round(p['g_back'], 3), filled=p['filled'])
    return rows, info


HEADER = """// On-road passenger-car fleet estimates (BEV vs non-BEV), by country and year, 2005-2041.
// Rebuilt 2026-10-16 by scripts/build_cars_on_road.py (method documented in that file's docstring);
// mirrors the Supabase table `country_cars_on_road` (project rtmlxvjpjxcvjdykrkvm).
//   REAL                 = real observed passenger-car fleet: Eurostat road_eqs_carage / road_eqs_carpda
//                          (22 European countries, 2013-2025), DfT VEH1111 (Great Britain 2005-2025), or an
//                          official/industry fleet count (Japan MLIT/JAMA, United States S&P Global Mobility,
//                          Mexico IDF, Brazil Sindipecas, Russia Autostat-derived) for the listed years.
//   MODEL_ANCHORED_BACK  = survival-curve model scaled to the real fleet, for years before/between real anchors.
//   MODEL_ANCHORED       = same, after the last real anchor up to 2026 (real/model ratio trend extrapolated).
//   MODEL_RAW            = pure survival-curve model (no real fleet count found): China, India, Korea, Canada,
//                          Australia and the smaller markets. Includes estimated pre-2005 cohorts.
//   MODEL_STOCK_CONSTANT_WITH_FUTURE_REG = 2027-2041 projection: total fleet held at its 2026 level, new
//                          registrations replace vehicles ageing out, BEV share follows a dampened logistic trend.
// Survival curves (table cars_duration_rate): country-specific where real statistics exist (Germany KBA,
// Norway SSB, United Kingdom DfT, Netherlands RDW/CBS, Japan AIRIA, China Zheng 2019, United States NHTSA/Greene &
// Leard), otherwise the region average (North America, West Europe, East Europe, Latin America, Africa, Middle East,
// Oceania, Asia (rest)); East Europe, Middle East, Oceania and Africa are proxies without own data.
// BEV counts are real (Eurostat/DfT) where available, otherwise modelled with the same curve.
"""


def notes_for(c, i, method):
    base = 'Survival curve: %s%s.' % (i['curve'], '' if i['curve'] == c else ' (region average)')
    if method == 'REAL': return base + ' Real fleet count (see asset header).'
    if method.startswith('MODEL_ANCHORED'): return base + ' Model scaled to real fleet counts (%s-%s).' % tuple(i['anchor_years'])
    if method == 'MODEL_RAW': return base + ' No real fleet count found: pure model with estimated pre-2005 cohorts (typical error +/-20%).'
    return base + ' Total fleet held at its 2026 level; BEV-share growth %.3f (own %s).' % (i['g'], i['g_own'])


METHODS = ['REAL', 'MODEL_ANCHORED_BACK', 'MODEL_ANCHORED', 'MODEL_RAW', 'MODEL_STOCK_CONSTANT_WITH_FUTURE_REG']


def country_note(c, i):
    s = 'Survival curve: %s%s.' % (i['curve'], '' if i['curve'] == c else ' (region average)')
    if i['anchored']:
        s += ' Real fleet counts used where available (anchor years %s-%s; REAL rows), model scaled to them elsewhere.' % tuple(i['anchor_years'])
    else:
        s += ' No real fleet count found: pure model with estimated pre-2005 cohorts (typical error +/-20%).'
    s += ' 2027-2041: total held at the 2026 level, BEV-share growth %.3f (own %s).' % (i['g'], i['g_own'])
    return s


def sql_chunks(rows, info, per_chunk=17):
    cs = sorted(rows)
    out = []
    for k in range(0, len(cs), per_chunk):
        part = cs[k:k + per_chunk]
        stmts = ["delete from country_cars_on_road where country in (%s);" % ','.join("'%s'" % c.replace("'", "''") for c in part)]
        for c in part:
            r = rows[c]
            bev = ','.join(str(x['bev']) for x in r); non = ','.join(str(x['nonBev']) for x in r)
            mth = ','.join(str(METHODS.index(x['method'])) for x in r)
            fut = ','.join(str(x.get('futureNewRegProj', 0)) for x in r)
            note = country_note(c, info[c]).replace("'", "''")
            stmts.append("insert into country_cars_on_road (country,year,nb_bev,nb_non_bev,method,notes,future_new_reg_proj) select '%s', y, (array[%s])[y-2004], (array[%s])[y-2004], (array['REAL','MODEL_ANCHORED_BACK','MODEL_ANCHORED','MODEL_RAW','MODEL_STOCK_CONSTANT_WITH_FUTURE_REG'])[(array[%s])[y-2004]+1], '%s', nullif((array[%s])[y-2004],0) from generate_series(2005,2041) y;" % (c.replace("'", "''"), bev, non, mth, note, fut))
        out.append('\n'.join(stmts))
    return out


def main():
    write = '--write' in sys.argv
    rows, info = build()
    oldp = ROOT / '.scratch' / 'cor' / 'old_cor.json'
    old = json.load(open(oldp)) if oldp.exists() else {}
    print('%-20s %-14s %-6s %8s %8s %8s | %8s %8s' % ('country', 'curve', 'anchor', '2018', '2025', '2030', 'old2025', 'old2030'))
    for c in sorted(rows):
        r = {x['year']: x for x in rows[c]}
        o = {x['year']: x for x in old.get(c, [])}
        def tot(y): return (r[y]['bev'] + r[y]['nonBev']) / 1e6
        def otot(y): return (o[y]['bev'] + o[y]['nonBev']) / 1e6 if y in o else float('nan')
        print('%-20s %-14s %-6s %8.2f %8.2f %8.2f | %8.2f %8.2f' % (c, info[c]['curve'], 'real' if info[c]['anchored'] else 'model', tot(2018), tot(2025), tot(2030), otot(2025), otot(2030)))
    s_new = sum(x['bev'] + x['nonBev'] for c in rows for x in rows[c] if x['year'] == 2025) / 1e6
    s_old = sum(x['bev'] + x['nonBev'] for c in old for x in old[c] if x['year'] == 2025) / 1e6 if old else 0
    print('50-country sum 2025: %.0f M (old %.0f M)' % (s_new, s_old))
    if write:
        out = ROOT / 'scripts' / 'out'; out.mkdir(exist_ok=True)
        body = json.dumps({c: rows[c] for c in sorted(rows)}, separators=(',', ':'), ensure_ascii=True)
        (ROOT / 'assets' / 'country-cars-on-road-data.js').write_text(HEADER + '\nconst CARS_ON_ROAD = ' + body + ';\n', encoding='utf-8', newline='\n')
        for n, s in enumerate(sql_chunks(rows, info)):
            (out / ('country_cars_on_road_%d.sql' % (n + 1))).write_text(s, encoding='utf-8')
        json.dump(dict(rows=rows, info=info), open(out / 'cars_on_road_build.json', 'w'))
        print('wrote assets/country-cars-on-road-data.js and scripts/out/*.sql')


if __name__ == '__main__':
    main()
