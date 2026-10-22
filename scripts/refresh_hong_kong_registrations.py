#!/usr/bin/env python3
"""
Hong Kong monthly private-car first registrations by make x fuel type, from the Transport Department's
Monthly Traffic and Transport Digest, Table 4.1(e) ("First Registration of Private Cars by Make, First
Registration Vehicle Status, Fuel Type and Body Type").

Each month has its own digest page:
  https://www.td.gov.hk/en/transport_in_hong_kong/transport_figures/monthly_traffic_and_transport_digest/YYYY/YYYYMM/index.html
which links to table41e.xls under a month-specific /filemanager/en/content_NNNN/ folder. This script downloads
every month in the requested range, parses the xls, and writes scripts/data/hk_private_car_first_reg.json:
  {"YYYY-MM": {"<make>": {"new": {"petrol":n,"diesel":n,"electric":n,"others":n,"total":n},
                          "all": {...}}}}
"new" = vehicle status A + B (never registered outside Hong Kong before import: genuinely new cars);
"all" additionally counts C1 / C2 / Others (previously registered abroad, i.e. used/parallel imports, or
owner-imported). The site uses "new".
Usage: python scripts/refresh_hong_kong_registrations.py [--from 2025-01] [--to 2026-09]
"""
import json, re, subprocess, sys, tempfile
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'scripts' / 'data' / 'hk_private_car_first_reg.json'
BASE = 'https://www.td.gov.hk'
PAGE = BASE + '/en/transport_in_hong_kong/transport_figures/monthly_traffic_and_transport_digest/{y}/{y}{m:02d}/index.html'
FUELS = ['petrol', 'diesel', 'electric', 'others']
STATUS_NEW = {'A', 'B'}


def curl(url, dest=None):
    cmd = ['curl', '-sL', '-m', '90', '-w', '%{http_code}']
    cmd += ['-o', str(dest)] if dest else []
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout if not dest else r.stdout[-3:]


def months(a, b):
    y, m = map(int, a.split('-')); y2, m2 = map(int, b.split('-'))
    while (y, m) <= (y2, m2):
        yield y, m
        m += 1
        if m == 13: y, m = y + 1, 1


def xls_url(y, m):
    html = curl(PAGE.format(y=y, m=m))
    mm = re.search(r'href="([^"]*/table41e\.xls)"', html)
    return BASE + mm.group(1) if mm else None


def parse(path):
    wb = xlrd.open_workbook(path)
    title = wb.sheet_by_index(0).row_values(1)[1]
    ym = re.search(r'\((\w+) (\d{4})\)', title)
    out, cur = {}, None
    for s in wb.sheets():
        for r in range(6, s.nrows):
            v = s.row_values(r)
            name = str(v[0]).replace('\n', ' ').strip()
            status = str(v[1]).split('\n')[0].strip()
            if name and status in ('A', 'B', 'C1', 'C2', 'Others', '其他'):
                cur = re.sub(r'^[^\x00-\x7f]+\s*', '', name).replace('^', '').strip().rstrip('#*').strip()
            if cur is None or status not in ('A', 'B', 'C1', 'C2', 'Others', '其他') or len(v) < 19:
                continue
            try:
                cells = [float(x or 0) for x in v[2:18]]
            except ValueError:
                continue
            d = out.setdefault(cur, {'new': dict.fromkeys(FUELS + ['total'], 0), 'all': dict.fromkeys(FUELS + ['total'], 0)})
            for i, f in enumerate(FUELS):
                n = int(sum(cells[i * 4:(i + 1) * 4]))
                d['all'][f] += n; d['all']['total'] += n
                if status in STATUS_NEW:
                    d['new'][f] += n; d['new']['total'] += n
    return ym.group(0) if ym else title, out


def main():
    a = sys.argv[sys.argv.index('--from') + 1] if '--from' in sys.argv else '2025-01'
    b = sys.argv[sys.argv.index('--to') + 1] if '--to' in sys.argv else '2026-09'
    data = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    tmp = Path(tempfile.mkdtemp())
    for y, m in months(a, b):
        key = f'{y}-{m:02d}'
        url = xls_url(y, m)
        if not url:
            print(key, 'no digest page / table41e link'); continue
        f = tmp / f'{key}.xls'
        if curl(url, f) != '200': print(key, 'download failed', url); continue
        label, rows = parse(f)
        new = sum(r['new']['total'] for r in rows.values()); allv = sum(r['all']['total'] for r in rows.values())
        ev = sum(r['new']['electric'] for r in rows.values())
        print(key, label, 'makes', len(rows), 'new', new, 'all', allv, 'EV(new)', ev, f'{100 * ev / max(new, 1):.1f}%')
        data[key] = rows
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
