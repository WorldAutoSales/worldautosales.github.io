"""SQL emission for the charging tables (called by build_charging.py).
Files: out/charging_0_ddl.sql, charging_1_year.sql, charging_2_snapshot.sql, charging_3_brand.sql (git-excluded)."""
import os

DDL = """create table if not exists public.charging_country_year (
  country text not null, iso2 text not null, year integer not null,
  points_slow integer, points_fast integer, points_ultra integer,
  ev_stock_bev bigint, ev_stock_phev bigint,
  source text not null default 'IEA Global EV Data Explorer / Global EV Outlook 2026 (CC BY 4.0); slow <=22 kW, fast 22-150 kW, ultra-fast >150 kW; values rounded by the IEA',
  primary key (country, year));
create table if not exists public.charging_country_snapshot (
  country text not null, iso2 text not null, snapshot_date date not null,
  ocm_stations integer, ocm_ports integer, ocm_ports_lt12 integer, ocm_ports_12_49 integer, ocm_ports_50_149 integer, ocm_ports_150_349 integer, ocm_ports_350plus integer, ocm_fast_stations integer, ocm_fast_ports integer,
  tesla_sites integer, tesla_stalls integer, official_stations integer, official_ports integer, official_ports_dc_fast integer, official_stations_dc_fast integer, workpop_15_64 bigint, share_12_22_of_le22 numeric, share_22_49_of_22_149 numeric,
  notes text default 'OCM = Open Charge Map (crowd-sourced registry, coverage varies by country: compare ocm_ports with the IEA points); Tesla = supercharge.info open sites; official = US DOE AFDC',
  primary key (country, snapshot_date));
create table if not exists public.charging_country_brand (
  country text not null, iso2 text not null, snapshot_date date not null, brand text not null,
  stations integer, ports integer, ports_lt12 integer, ports_12_49 integer, ports_50_149 integer, ports_150_349 integer, ports_350plus integer,
  source text not null default 'Open Charge Map',
  primary key (country, snapshot_date, brand));
comment on table public.charging_country_year is 'Public EV charging points per country and year (IEA Global EV Data Explorer), slow / fast / ultra-fast, plus IEA EV stock for 2024-2025. Built by scripts/charging/build_charging.py.';
comment on table public.charging_country_snapshot is 'Charging stations and ports per country from Open Charge Map (snapshot), Tesla Supercharger sites (supercharge.info) and official national counts (US DOE AFDC). Built by scripts/charging/build_charging.py.';
comment on table public.charging_country_brand is 'Charging stations / ports per country and brand (operator) with ports by power band, from Open Charge Map; at most 14 brands plus Other brands per country.';
alter table public.charging_country_year enable row level security;
alter table public.charging_country_snapshot enable row level security;
alter table public.charging_country_brand enable row level security;
"""


def q(v):
    if v is None:
        return 'null'
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def write_sql(countries, snapshot, out):
    os.makedirs(out, exist_ok=True)
    w = lambda n, t: open(os.path.join(out, n), 'w', encoding='utf8').write(t)
    w('charging_0_ddl.sql', DDL)
    yr = []
    for c in countries:
        for y, a in (c.get('iea') or {}).items():
            ev = (c.get('ev') or {}).get(y) or [None, None]
            yr.append('(%s,%s,%s,%s,%s,%s,%s,%s)' % (q(c['n']), q(c['iso']), y, q(a[0]), q(a[1]), q(a[2]), q(ev[0]), q(ev[1])))
    w('charging_1_year.sql', 'insert into public.charging_country_year (country,iso2,year,points_slow,points_fast,points_ultra,ev_stock_bev,ev_stock_phev) values\n' + ',\n'.join(yr) +
      '\non conflict (country, year) do update set points_slow=excluded.points_slow, points_fast=excluded.points_fast, points_ultra=excluded.points_ultra, ev_stock_bev=excluded.ev_stock_bev, ev_stock_phev=excluded.ev_stock_phev;\n')
    sn, br = [], []
    for c in countries:
        o = c.get('ocm') or {}
        b = o.get('bands') or [None] * 5
        fs = o.get('fs') or [None, None]
        sh = (c.get('sh') or [None, None])[:2]
        t = c.get('tesla') or {}
        of = c.get('off') or {}
        sn.append('(%s)' % ','.join(q(v) for v in (c['n'], c['iso'], snapshot, o.get('st'), o.get('po'), b[0], b[1], b[2], b[3], b[4], fs[0], fs[1],
                                                   t.get('sites'), t.get('stalls'), of.get('stations'), of.get('ports'), of.get('ports_dc_fast'), of.get('stations_dc_fast'), c.get('w'), sh[0], sh[1])))
        for r in o.get('brands') or []:
            br.append('(%s)' % ','.join(q(v) for v in (c['n'], c['iso'], snapshot, r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7])))
    w('charging_2_snapshot.sql', 'insert into public.charging_country_snapshot (country,iso2,snapshot_date,ocm_stations,ocm_ports,ocm_ports_lt12,ocm_ports_12_49,ocm_ports_50_149,ocm_ports_150_349,ocm_ports_350plus,ocm_fast_stations,ocm_fast_ports,tesla_sites,tesla_stalls,official_stations,official_ports,official_ports_dc_fast,official_stations_dc_fast,workpop_15_64,share_12_22_of_le22,share_22_49_of_22_149) values\n' +
      ',\n'.join(sn) + '\non conflict (country, snapshot_date) do nothing;\n')
    w('charging_3_brand.sql', 'insert into public.charging_country_brand (country,iso2,snapshot_date,brand,stations,ports,ports_lt12,ports_12_49,ports_50_149,ports_150_349,ports_350plus) values\n' + ',\n'.join(br) + '\non conflict (country, snapshot_date, brand) do nothing;\n')
    return len(yr), len(sn), len(br)
