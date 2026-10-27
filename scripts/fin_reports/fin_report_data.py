"""Worldwide sales per manufacturer as REPORTED BY THE COMPANIES (financial reports, annual reports, 10-K / 20-F / 6-K,
earnings and year-end sales press releases) -- the "real" world totals, as opposed to the sum of the countries tracked on this site.

Single source of truth for:
  * Supabase table  manufacturer_fin_report_sales  (one row per entity x year x period x region x segment)
  * Supabase column sales_manufacturers_year.sales_from_fin_reports  (the world total of each entity-year, CY preferred)
  * assets/manufacturer-fin-report-sales.js  (read by manufacturers.html for the "Unclassified" gap rows)
Run  python scripts/fin_reports/build_fin_reports.py  to regenerate the SQL + JS from this file.

Conventions
  year          calendar year, or for fiscal-year reporters the year the FY STARTS (Toyota/Honda/Suzuki/Subaru "FY2025" =
                Apr 2025 - Mar 2026; Indian "FY26" = Apr 2025 - Mar 2026 -> year 2025). period_type 'CY' | 'FY' | '9M'.
  calendar_aligned  true for CY rows (comparable with the site's calendar-year country data), false for FY / 9M rows.
  additive      false = memo line already contained in another region row (e.g. China inside Asia); never sum these.
  confidence    filing        read in the audited annual report / 10-K / regulatory filing
                press_release read in the company's own results or sales release
                media         figure the company published, as quoted by trade press (not read at the source)
                derived       computed here: a sum of reported rows, or a prior year back-calculated from a reported % change
  basis         what the company counts (deliveries / retail / wholesale / shipments / sales) -- these are NOT interchangeable:
                wholesale = vehicles shipped to dealers (can exceed or trail retail by stock changes); retail/deliveries =
                handed to customers; Chinese groups quote wholesale incl. exports; several include commercial vehicles.
"""

# ---- entities: name -> (parent group, reporting level, home country, home region, site_group names used by manufacturers.html in "Parent group" mode)
# (sites = [] where this site splits the company over several groups -- SAIC, Changan, Dongfeng, Great Wall -- so a tracked-vs-reported gap would mislead)
ENT = {
    'Toyota Motor (Toyota, Lexus, Daihatsu, Hino)': ('Toyota Motor Corporation', 'group', 'Japan', 'Asia', ['Toyota Motor Corporation']),
    'Volkswagen Group': ('Volkswagen Group', 'group', 'Germany', 'Europe', ['Volkswagen Group']),
    'Hyundai Motor Group (Hyundai + Kia)': ('Hyundai Motor Group', 'group', 'South Korea', 'Asia', ['Hyundai Motor Group']),
    'Hyundai Motor (incl. Genesis)': ('Hyundai Motor Group', 'subsidiary', 'South Korea', 'Asia', []),
    'Kia': ('Hyundai Motor Group', 'subsidiary', 'South Korea', 'Asia', []),
    'Stellantis': ('Stellantis N.V.', 'group', 'Netherlands', 'Europe', ['Stellantis N.V.']),
    'General Motors': ('General Motors', 'group', 'United States', 'North America', ['General Motors']),
    'BYD': ('BYD Company Ltd.', 'group', 'China', 'Asia', ['BYD Company Ltd.']),
    'Ford Motor Company': ('Ford Motor Company', 'group', 'United States', 'North America', ['Ford Motor Company']),
    'Honda Motor': ('Honda Motor Co.', 'group', 'Japan', 'Asia', ['Honda Motor Co.']),
    'Nissan Motor': ('Nissan Motor Corporation', 'group', 'Japan', 'Asia', ['Nissan Motor Corporation']),
    'Suzuki Motor': ('Suzuki Motor Corporation', 'group', 'Japan', 'Asia', ['Suzuki Motor Corporation']),
    'Maruti Suzuki India': ('Suzuki Motor Corporation', 'subsidiary', 'India', 'Asia', []),
    'Geely Holding Group': ('Zhejiang Geely Holding Group', 'group', 'China', 'Asia', ['Zhejiang Geely Holding Group']),
    'Geely Automobile Holdings': ('Zhejiang Geely Holding Group', 'subsidiary', 'China', 'Asia', []),
    'Volvo Cars': ('Zhejiang Geely Holding Group', 'subsidiary', 'Sweden', 'Europe', []),
    'Chery Group': ('Chery Automobile Co. / Chery Holding Group', 'group', 'China', 'Asia', ['Chery Automobile Co. / Chery Holding Group']),
    'BMW Group': ('BMW AG', 'group', 'Germany', 'Europe', ['BMW AG']),
    'Mercedes-Benz Group': ('Mercedes-Benz Group AG', 'group', 'Germany', 'Europe', ['Mercedes-Benz Group AG']),
    'Changan Automobile': ('China Changan Automobile Group Co.', 'group', 'China', 'Asia', []),
    'SAIC Motor': ('SAIC Motor', 'group', 'China', 'Asia', []),
    'Renault Group': ('Renault Group', 'group', 'France', 'Europe', ['Renault Group']),
    'Jaguar Land Rover (Tata Motors)': ('Tata Motors', 'subsidiary', 'United Kingdom', 'Europe', ['Tata Motors (Jaguar Land Rover)']),
    'Tata Motors Passenger Vehicles (India)': ('Tata Motors', 'subsidiary', 'India', 'Asia', []),
    'Great Wall Motor': ('Great Wall Motor', 'group', 'China', 'Asia', []),
    'Mazda Motor': ('Mazda Motor Corporation', 'group', 'Japan', 'Asia', ['Mazda Motor Corporation']),
    'Tesla': ('Tesla, Inc.', 'group', 'United States', 'North America', ['Tesla, Inc.']),
    'Dongfeng Motor Group': ('Dongfeng Motor Corporation', 'group', 'China', 'Asia', []),
    'GAC Group': ('GAC Group', 'group', 'China', 'Asia', []),
    'FAW Group': ('FAW Group', 'group', 'China', 'Asia', []),
    'BAIC Group': ('BAIC Group', 'group', 'China', 'Asia', []),
    'Mahindra & Mahindra': ('Mahindra Group', 'group', 'India', 'Asia', ['Mahindra Group']),
    'Subaru Corporation': ('Subaru Corporation (Fuji Heavy Industries)', 'group', 'Japan', 'Asia', ['Subaru Corporation (Fuji Heavy Industries)']),
    'Mitsubishi Motors': ('Mitsubishi Motors', 'group', 'Japan', 'Asia', []),
    'Leapmotor': ('Zhejiang Leapmotor Technology Co.', 'group', 'China', 'Asia', ['Zhejiang Leapmotor Technology Co.']),
    'Li Auto': ('Li Auto', 'group', 'China', 'Asia', ['Li Auto']),
    'Xiaomi (auto)': ('Xiaomi', 'group', 'China', 'Asia', ['Xiaomi']),
    'XPeng': ('XPeng Inc.', 'group', 'China', 'Asia', ['XPeng Inc.']),
    'NIO': ('NIO Inc.', 'group', 'China', 'Asia', ['NIO Inc.']),
    'Seres Group': ('Seres Group Co.', 'group', 'China', 'Asia', ['Seres Group Co.']),
    'Perodua': ('Perodua', 'group', 'Malaysia', 'Asia', []),
    'Proton': ('Proton', 'group', 'Malaysia', 'Asia', []),
}

ROWS = []   # (entity, year, period_type, start, end, region, segment, units, basis, scope, confidence, source_doc, source_url, notes, additive)


def add(ent, year, ptype, units, basis, conf, src, url='', region='World', segment='All', scope='', notes='', additive=True, start=None, end=None):
    assert ent in ENT, ent
    if start is None:
        start, end = {'CY': (f'{year}-01-01', f'{year}-12-31'), 'FY': (f'{year}-04-01', f'{year + 1}-03-31'), '9M': (f'{year}-01-01', f'{year}-09-30')}[ptype]
    ROWS.append((ent, year, ptype, start, end, region, segment, int(units), basis, scope, conf, src, url, notes, additive))


# =====================================================================================================================
# Toyota group -- CY, retail sales (consolidated group incl. Daihatsu + Hino), Toyota's calendar-year release (Jan 2026)
T = 'Toyota Motor (Toyota, Lexus, Daihatsu, Hino)'
U_T = 'https://www.just-auto.com/?p=185922'
add(T, 2025, 'CY', 11322575, 'retail', 'media', 'Toyota CY2025 sales release (29 Jan 2026), via Jiji/just-auto', 'https://english.adnkronos.com/2026/01/29/toyota-tops-global-auto-sales-for-6th-straight-year/', scope='Toyota + Lexus + Daihatsu + Hino', notes='Toyota + Lexus alone: 10,536,807')
add(T, 2024, 'CY', 10820000, 'retail', 'media', 'CLS table of company reports (carnewschina 2026-02-26)', 'https://carnewschina.com/2026/02/26/three-chinese-automakers-enter-global-top-10-as-2025-sales-rankings-finalized/', scope='Toyota + Lexus + Daihatsu + Hino', notes='rounded to 10k (10.82 M); 2025 = +4.6% on 2024')
for reg, v, nt, addv in [('Japan', 2071254, '', True), ('North America', 2929660, '', True), ('Europe', 1182551, '', True),
                         ('Asia (excl. Japan)', 3285605, 'includes China 1,780,396', True), ('China (memo)', 1780396, 'included in Asia (excl. Japan)', False),
                         ('Other regions', 1853505, 'Latin America, Middle East, Africa, Oceania; = world - the four regions above', True)]:
    add(T, 2025, 'CY', v, 'retail', 'derived' if reg == 'Other regions' else 'media', 'Toyota CY2025 release regional table, as compiled by inovev', 'https://inovev.com/index.php/en/market-analyses/category-blog/21811-2026-05-2', region=reg, notes=nt, additive=addv)

# Volkswagen Group -- deliveries to customers incl. equity-accounted Chinese JVs; Annual Report 2025
V = 'Volkswagen Group'
VU = 'https://annualreport2025.volkswagen-group.com/group-management-report/business-development/deliveries.html'
add(V, 2025, 'CY', 8983900, 'deliveries', 'filing', 'Volkswagen Group Annual Report 2025 - Deliveries', VU, scope='passenger cars + LCV + commercial vehicles (incl. Chinese JVs)')
add(V, 2024, 'CY', 9026681, 'deliveries', 'filing', 'Volkswagen Group Annual Report 2025 - Deliveries (prior year)', VU, scope='passenger cars + LCV + commercial vehicles (incl. Chinese JVs)')
for y, pc, cv in [(2025, 8678334, 305566), (2024, 8692465, 334216)]:
    add(V, y, 'CY', pc, 'deliveries', 'filing', 'Volkswagen Group Annual Report 2025 - Deliveries', VU, segment='Passenger cars + LCV')
    add(V, y, 'CY', cv, 'deliveries', 'filing', 'Volkswagen Group Annual Report 2025 - Deliveries', VU, segment='Commercial vehicles (Traton)')
for y, rows in [(2025, [('Europe / Other markets', 4196403, 163447), ('North America', 880634, 66201), ('South America', 596352, 66688), ('Asia-Pacific', 3004945, 9230)]),
                (2024, [('Europe / Other markets', 3992611, 159529), ('North America', 961916, 95073), ('South America', 524121, 70156), ('Asia-Pacific', 3213817, 9458)])]:
    for reg, a, b in rows:
        add(V, y, 'CY', a + b, 'deliveries', 'derived', 'Volkswagen Group Annual Report 2025 - Deliveries (PC+LCV plus CV regional tables summed)', VU, region=reg, notes=f'PC+LCV {a:,} + commercial vehicles {b:,}; Europe/Other markets includes Turkey and South Africa')
add(V, 2025, 'CY', 2692191, 'deliveries', 'filing', 'Volkswagen Group Annual Report 2025 - Deliveries', VU, region='China (memo)', segment='Passenger cars + LCV', notes='included in Asia-Pacific', additive=False)
add(V, 2024, 'CY', 2926763, 'deliveries', 'filing', 'Volkswagen Group Annual Report 2025 - Deliveries', VU, region='China (memo)', segment='Passenger cars + LCV', notes='included in Asia-Pacific', additive=False)

# General Motors -- total vehicle sales incl. unconsolidated JVs (SAIC-GM, SAIC-GM-Wuling), Form 10-K FY2025, thousands
G = 'General Motors'
GU = 'https://www.sec.gov/Archives/edgar/data/1467858/000146785826000013/gm-20251231.htm'
GM = {  # region: (2025, 2024, 2023) thousand units
    'World': (6184, 6003, 6189), 'North America': (3361, 3215, 3055), 'Asia/Pacific, Middle East, Africa': (2418, 2360, 2676),
    'South America': (403, 424, 456), 'Europe': (2, 2, 2),
    'United States (memo)': (2853, 2705, 2595), 'China (memo)': (1880, 1839, 2099), 'Brazil (memo)': (276, 315, 328),
}
for reg, vals in GM.items():
    for y, v in zip((2025, 2024, 2023), vals):
        add(G, y, 'CY', v * 1000, 'retail', 'filing', 'GM Form 10-K FY2025 - Total vehicle sales (thousands)', GU, region=reg,
            scope='total vehicle sales incl. China JVs', notes='rounded to thousands' + ('; included in its continental region' if 'memo' in reg else ''), additive='memo' not in reg)
for y, a, b in [(2025, 3296, 503), (2024, 3464, 547), (2023, 3147, 621)]:
    add(G, y, 'CY', (a + b) * 1000, 'wholesale', 'filing', 'GM Form 10-K FY2025 - Wholesale vehicle sales (excl. JVs)', GU, segment='Wholesale (GMNA + GMI, excl. JVs)', notes=f'GMNA {a}k + GMI {b}k; not the headline total (excludes unconsolidated Chinese JVs)', additive=False)

# Ford -- wholesales (Ford + Lincoln, incl. vehicles built and sold in China by unconsolidated affiliates), Q4 2025 release
F = 'Ford Motor Company'
FU = 'https://s205.q4cdn.com/882619693/files/doc_financials/2025/q4/Ford-Q4-2025-Earnings-Press-Release.pdf'
add(F, 2025, 'CY', 4395000, 'wholesale', 'press_release', 'Ford Q4 2025 earnings release - Total company wholesales', FU, scope='Ford + Lincoln, incl. China unconsolidated affiliates', notes='thousands: 4,395; Ford Blue 2,728 / Model e 178 / Ford Pro 1,488')
add(F, 2024, 'CY', 4470000, 'wholesale', 'press_release', 'Ford Q4 2025 earnings release - Total company wholesales (prior year)', FU, scope='Ford + Lincoln, incl. China unconsolidated affiliates', notes='thousands: 4,470; Ford Blue 2,862 / Model e 105 / Ford Pro 1,503')

# Hyundai + Kia
H = 'Hyundai Motor (incl. Genesis)'
add(H, 2025, 'CY', 4138389, 'wholesale', 'press_release', 'Hyundai Motor 2025 annual and Q4 business results', 'https://www.hyundaimotorgroup.com/en/news/hyundai-motor-announces-2025-annual-and-q4-business-results', scope='Hyundai + Genesis, global wholesale')
add(H, 2024, 'CY', 4141791, 'wholesale', 'media', 'Hyundai Motor 2024 sales (KED Global / inovev)', 'https://www.kedglobal.com/newsView/ked202501030008', scope='Hyundai + Genesis, global wholesale')
add(H, 2025, 'CY', 3425435, 'wholesale', 'media', 'Hyundai Motor 2025 results table: sales outside Korea (via search summary)', 'https://www.hyundai.com/worldwide/en/newsroom/detail/0000001116', region='Outside Korea', notes='full-year result table')
add(H, 2025, 'CY', 4138389 - 3425435, 'wholesale', 'derived', 'Hyundai Motor 2025: world minus outside Korea', 'https://www.hyundai.com/worldwide/en/newsroom/detail/0000001116', region='Korea (domestic)')
K = 'Kia'
add(K, 2025, 'CY', 3135873, 'wholesale', 'media', 'Kia 2025 annual results (28 Jan 2026); the 5 Jan 2026 sales release says 3,135,803', 'https://worldwide.kia.com/en/newsroom/view/?id=161055', scope='Kia, global wholesale')
add(K, 2024, 'CY', 3089457, 'wholesale', 'media', 'Kia 2024 global sales (just-auto / Kia release)', 'https://just-auto.com/news/kia-vehicle-sales-in-2024', scope='Kia, global wholesale')
HG = 'Hyundai Motor Group (Hyundai + Kia)'
add(HG, 2025, 'CY', 4138389 + 3135873, 'wholesale', 'derived', 'Hyundai Motor + Kia', '', scope='Hyundai + Genesis + Kia')
add(HG, 2024, 'CY', 4141791 + 3089457, 'wholesale', 'derived', 'Hyundai Motor + Kia', '', scope='Hyundai + Genesis + Kia')

# Stellantis -- consolidated shipments; 9M from the Q3 2025 6-K, full year from 9M + Q4 estimate
S = 'Stellantis'
SU = 'https://www.sec.gov/Archives/edgar/data/1605484/000160548425000087/stellantisnvq32025pressrel.htm'
add(S, 2025, 'CY', 5484000, 'shipments', 'derived', 'Stellantis 9M 2025 shipments (3,964k, Form 6-K) + Q4 2025 estimate (~1.52M, +9% y/y)', SU, scope='consolidated shipments, Maserati included', notes='full-year 2025 headline "about 5.5 M"; CLS table 5.48 M; unaudited estimate')
add(S, 2024, 'CY', 5415000, 'shipments', 'derived', 'Stellantis 9M 2024 shipments (4,020k, Form 6-K) + Q4 2024 (~1,395k)', SU, scope='consolidated shipments, Maserati included', notes='CLS table 5.42 M')
for reg, a, b in [('North America', 1050, 1137), ('Enlarged Europe', 1823, 1883), ('Middle East & Africa', 319, 292), ('South America', 723, 653), ('China, India & Asia Pacific', 43, 46), ('Maserati (global)', 5.9, 8.6)]:
    add(S, 2025, '9M', round(a * 1000), 'shipments', 'filing', 'Stellantis Q3 2025 press release (Form 6-K) - 9M shipments', SU, region=reg)
    add(S, 2024, '9M', round(b * 1000), 'shipments', 'filing', 'Stellantis Q3 2025 press release (Form 6-K) - 9M 2024 comparative', SU, region=reg)
add(S, 2025, '9M', 3964000, 'shipments', 'filing', 'Stellantis Q3 2025 press release (Form 6-K)', SU, notes='9M only; regional rows sum to this')
add(S, 2024, '9M', 4020000, 'shipments', 'filing', 'Stellantis Q3 2025 press release (Form 6-K)', SU, notes='9M only; regional rows sum to this')

# BYD
B = 'BYD'
BU = 'https://cnevpost.com/2026/01/01/byd-nev-sales-dec-2025/'
for y, v in [(2025, 4602436), (2024, 4272145), (2023, 3024417), (2022, 1863494)]:
    add(B, y, 'CY', v, 'wholesale', 'media', 'BYD monthly/annual sales releases (HKEX filings) via CnEVPost', BU, scope='NEV passenger + commercial, incl. exports')
add(B, 2025, 'CY', 1046083, 'wholesale', 'media', 'BYD overseas sales (CnEVPost)', 'https://cnevpost.com/2026/01/24/byd-aims-for-1-3-million-overseas-sales-2026/', region='Overseas', notes='passenger + commercial')
add(B, 2025, 'CY', 4602436 - 1046083, 'wholesale', 'derived', 'BYD total minus overseas', BU, region='China (domestic)')

# Honda / Nissan / Suzuki / Mazda / Mitsubishi / Subaru
add('Honda Motor', 2025, 'CY', 3520000, 'retail', 'media', 'CLS table of company reports (carnewschina 2026-02-26)', 'https://carnewschina.com/2026/02/26/three-chinese-automakers-enter-global-top-10-as-2025-sales-rankings-finalized/', scope='Honda + Acura, automobiles', notes='rounded to 10k; -7.5% on 2024')
add('Honda Motor', 2024, 'CY', 3810000, 'retail', 'media', 'CLS table of company reports (carnewschina 2026-02-26)', 'https://carnewschina.com/2026/02/26/three-chinese-automakers-enter-global-top-10-as-2025-sales-rankings-finalized/', scope='Honda + Acura, automobiles', notes='rounded to 10k')
N = 'Nissan Motor'
NU = 'https://global.nissannews.com/en/releases/nissan-production-sales-exports-dec-2025'
add(N, 2025, 'CY', 3202137, 'retail', 'press_release', 'Nissan production, sales and exports Dec 2025 (Jan-Dec)', NU, scope='Nissan, Infiniti, Datsun, retail')
add(N, 2024, 'CY', 3348692, 'retail', 'press_release', 'Nissan production, sales and exports Dec 2025 (prior-year column)', NU, scope='Nissan, Infiniti, Datsun, retail')
for reg, a, b, conf, nt in [('Japan', 402977, None, 'press_release', ''), ('China', 653024, 696631, 'press_release', ''), ('Europe', 329557, 354939, 'press_release', ''),
                            ('North America', 1313000, None, 'media', '1.313 M (+2.2%), rounded to thousands')]:
    add(N, 2025, 'CY', a, 'retail', conf, 'Nissan production, sales and exports Dec 2025', NU, region=reg, notes=nt)
    if b: add(N, 2024, 'CY', b, 'retail', conf, 'Nissan production, sales and exports Dec 2025', NU, region=reg, notes='partial: only China and Europe quoted for 2024', additive=False)
add(N, 2025, 'CY', 3202137 - 402977 - 653024 - 329557 - 1313000, 'retail', 'derived', 'Nissan 2025: world minus Japan, China, Europe, North America', NU, region='Other markets', notes='Latin America, Middle East, Asia, Africa, Oceania')
add('Suzuki Motor', 2025, 'CY', 3290000, 'retail', 'media', 'Suzuki CY2025 global sales (Jiji / CLS), +1.4% on 2024', 'https://mreport.co.th/en/news/industry-movement/105-japan-automakers-global-production-2025', scope='Suzuki automobiles, global', notes='rounded to 10k')
add('Suzuki Motor', 2024, 'CY', 3245000, 'retail', 'derived', 'Suzuki CY2025 back-calculated from the reported +1.4%', 'https://mreport.co.th/en/news/industry-movement/105-japan-automakers-global-production-2025', scope='Suzuki automobiles, global', notes='approximate')
add('Suzuki Motor', 2025, 'FY', 3320000, 'retail', 'media', 'Suzuki FY2025 (Apr 2025-Mar 2026) global automobile sales, +2.4%', 'https://www.globalsuzuki.com/globalnews/2026/0427a.html', scope='Suzuki automobiles, global', notes='about 3.32 M; India about 56%')
add('Maruti Suzuki India', 2025, 'FY', 2422713, 'wholesale', 'media', 'Maruti Suzuki FY2025-26 results (domestic incl. OEM sales 1,974,939 + exports 447,774)', 'https://www.marutisuzuki.com/corporate/media/press-releases/2026/april/maruti-suzuki-announces-financial-results-for-fy2025-26', scope='subset of Suzuki global (India only, incl. exports)')
add('Maruti Suzuki India', 2025, 'FY', 447774, 'wholesale', 'media', 'Maruti Suzuki FY2025-26 results', 'https://www.marutisuzuki.com/corporate/media/press-releases/2026/april/maruti-suzuki-announces-financial-results-for-fy2025-26', region='Exports')
add('Mazda Motor', 2025, 'CY', 1256215, 'retail', 'media', 'Mazda CY2025 global sales (-1.7%)', 'https://www.just-auto.com/?p=189501')
add('Mazda Motor', 2024, 'CY', 1277578, 'retail', 'press_release', 'Mazda production and sales results, Jan 2025 release', 'https://newsroom.mazda.com/en/publicity/release/2025/202501/250130a.html')
add('Mitsubishi Motors', 2025, 'CY', 810000, 'retail', 'media', 'Jiji: Mitsubishi Motors CY2025 global sales -5.8%', 'https://english.adnkronos.com/2026/01/29/toyota-tops-global-auto-sales-for-6th-straight-year-2/', notes='rounded to 10k')
add('Mitsubishi Motors', 2024, 'CY', 860000, 'retail', 'derived', 'Mitsubishi 2025 back-calculated from -5.8%', '', notes='approximate')
add('Subaru Corporation', 2024, 'FY', 936000, 'retail', 'press_release', 'Subaru FYE March 2025 results (consolidated unit sales)', 'https://www.subaru.co.jp/news-en/2025_05_14_154757/', scope='Apr 2024-Mar 2025; consolidated unit sales', notes='FY label 2024 = Apr 2024 - Mar 2025')
add('Subaru Corporation', 2025, 'FY', 896000, 'retail', 'media', 'Subaru FYE March 2026 results as reported by trade press (-4.3%)', 'https://english.news18a.com/news/english_257670.html', scope='Apr 2025-Mar 2026; consolidated unit sales')

# Europe premium + Renault
BM = 'BMW Group'
add(BM, 2025, 'CY', 2463715, 'deliveries', 'press_release', 'BMW Group vehicle sales 2025 press release', 'https://www.press.bmwgroup.com/global/article/detail/T0454859EN/bmw-group-vehicle-sales-grew-in-2025', scope='BMW + MINI + Rolls-Royce (BMW 2,169,761, MINI 288,290, RR 5,664)')
add(BM, 2024, 'CY', 2450804, 'deliveries', 'press_release', 'BMW Group 2024 deliveries press release', 'https://www.press.bmwgroup.com/global/article/detail/T0447427EN/bmw-group-maintains-bev-growth-path-in-challenging-market-situation-in-2024', scope='BMW + MINI + Rolls-Royce')
for reg, v in [('Europe', 1016360), ('Americas', 508221), ('Asia', 871550)]:
    add(BM, 2025, 'CY', v, 'deliveries', 'press_release', 'BMW Group vehicle sales 2025 press release - regional table (BMW + MINI)', 'https://www.press.bmwgroup.com/global/article/detail/T0454859EN/bmw-group-vehicle-sales-grew-in-2025', region=reg, scope='BMW + MINI (Rolls-Royce not split)')
add(BM, 2025, 'CY', 625527, 'deliveries', 'press_release', 'BMW Group vehicle sales 2025 press release', 'https://www.press.bmwgroup.com/global/article/detail/T0454859EN/bmw-group-vehicle-sales-grew-in-2025', region='China (memo)', notes='included in Asia', additive=False)
add(BM, 2025, 'CY', 2463715 - 1016360 - 508221 - 871550, 'deliveries', 'derived', 'BMW 2025: group total minus Europe, Americas, Asia', '', region='Rest of world (incl. Rolls-Royce)', notes='Africa, Oceania and the Rolls-Royce units')
M = 'Mercedes-Benz Group'
MU = 'https://media.mercedes-benz.it/download/e40ca32d-2bd0-45d5-b8dd-5ee11a0eda77/20260112_mbgroup_pressinformation_sales_2025.pdf'
add(M, 2025, 'CY', 2160000, 'retail', 'press_release', 'Mercedes-Benz Group sales release 12 Jan 2026', MU, scope='Mercedes-Benz Cars 1,800,800 + Vans 359,100 (rounded to 100)')
add(M, 2024, 'CY', 2389000, 'retail', 'press_release', 'Mercedes-Benz Group sales release 10 Jan 2025', 'https://media.mercedes-benz.it/download/24df53d9-8466-4835-930f-12f02d6ed572/20250110-mbgroup-pressinformation-sales-2024.docx', scope='Cars 1,983,400 + Vans 405,600 (rounded to 100)')
add(M, 2025, 'CY', 1800800, 'retail', 'press_release', 'Mercedes-Benz Group sales release 12 Jan 2026', MU, segment='Cars')
add(M, 2025, 'CY', 359100, 'retail', 'press_release', 'Mercedes-Benz Group sales release 12 Jan 2026', MU, segment='Vans')
add(M, 2024, 'CY', 1983400, 'retail', 'press_release', 'Mercedes-Benz Group sales release 10 Jan 2025', 'https://media.mercedes-benz.it/download/24df53d9-8466-4835-930f-12f02d6ed572/20250110-mbgroup-pressinformation-sales-2024.docx', segment='Cars')
add(M, 2024, 'CY', 405600, 'retail', 'press_release', 'Mercedes-Benz Group sales release 10 Jan 2025', 'https://media.mercedes-benz.it/download/24df53d9-8466-4835-930f-12f02d6ed572/20250110-mbgroup-pressinformation-sales-2024.docx', segment='Vans')
for reg, c, v in [('Europe', 634600, 248700), ('Asia', 747000, 28300), ('North America', 320600, 43400), ('Rest of world', 98700, 38700)]:
    add(M, 2025, 'CY', c + v, 'retail', 'derived', 'Mercedes-Benz Group sales release 12 Jan 2026 - cars + vans regional tables summed', MU, region=reg, notes=f'cars {c:,} + vans {v:,}; Europe = EU+UK+CH+NO, North America = US+CA+MX')
add(M, 2025, 'CY', 551900 + 20000, 'retail', 'derived', 'Mercedes-Benz Group sales release 12 Jan 2026 (China cars 551,900 + vans 20,000)', MU, region='China (memo)', notes='included in Asia', additive=False)
R = 'Renault Group'
RU = 'https://live.euronext.com/en/products/equities/company-news/2026-01-20-renault-group-2025-fy-sales-results-renault-group-and-its'
add(R, 2025, 'CY', 2336807, 'retail', 'media', 'Renault Group 2025 FY sales results (20 Jan 2026), via press', RU, scope='Renault + Dacia + Alpine (+ Mobilize), global registrations', notes='Renault 1,628,030; Dacia 697,408; Alpine 10,970')
add(R, 2024, 'CY', 2264000, 'retail', 'derived', 'Renault Group 2025 back-calculated from the reported +3.2%', RU, notes='approximate')
add(R, 2025, 'CY', 1607848, 'retail', 'media', 'Renault Group 2025 FY sales results', RU, region='Europe')
add(R, 2025, 'CY', 2336807 - 1607848, 'retail', 'derived', 'Renault Group 2025: group total minus Europe', RU, region='International (outside Europe)')

# Geely, Volvo, Chery, Changan, SAIC, GWM and Chinese groups
add('Geely Holding Group', 2025, 'CY', 4120000, 'wholesale', 'media', 'Geely Holding 2025 sales (CnEVPost / Caixin)', 'https://cnevpost.com/2026/01/22/geely-holding-targets-6-5-million-sales-2030/', scope='Geely Auto + Volvo Cars + Lotus + Polestar etc.', notes='about 4.12 M (+26%); rounded to 10k')
add('Geely Holding Group', 2024, 'CY', 3270000, 'wholesale', 'media', 'CLS table of company reports (carnewschina 2026-02-26)', 'https://carnewschina.com/2026/02/26/three-chinese-automakers-enter-global-top-10-as-2025-sales-rankings-finalized/', notes='rounded to 10k')
add('Geely Automobile Holdings', 2025, 'CY', 3024567, 'wholesale', 'media', 'Geely Auto 2025 sales (HKEX monthly filing via CnEVPost)', 'https://cnevpost.com/2026/03/18/geely-2025-profit-beats-estimates/', scope='listed Geely Auto (Geely, Galaxy, Zeekr, Lynk & Co); excludes Volvo Cars')
add('Geely Automobile Holdings', 2024, 'CY', 2176567, 'wholesale', 'media', 'Geely Auto 2024 sales (HKEX monthly filing)', 'https://carnewschina.com/2025/01/06/geely-achieves-2-1-million-car-sales-in-2024-aims-for-2-71-million-in-2025/', scope='listed Geely Auto; excludes Volvo Cars')
add('Geely Automobile Holdings', 2025, 'CY', 420097, 'wholesale', 'media', 'Geely Auto 2025 exports (Gasgoo)', 'https://autonews.gasgoo.com/articles/news/geely-autos-2025-cumulative-sales-exceed-302-million-targets-345-million-total-sales-in-2026-2007841500895645696', region='Exports', notes='CnEVPost gives 418,904')
V2 = 'Volvo Cars'
add(V2, 2025, 'CY', 710042, 'retail', 'press_release', 'Volvo Cars sales volumes December 2025', 'https://www.volvocars.com/intl/media/corporate/sales-volumes/', scope='Volvo cars, global retail')
add(V2, 2024, 'CY', 763389, 'retail', 'press_release', 'Volvo Cars sales volumes December 2025 (prior year)', 'https://www.volvocars.com/intl/media/corporate/sales-volumes/')
add(V2, 2023, 'CY', 708716, 'retail', 'media', 'Volvo Cars 2023 retail sales', 'https://www.volvocars.com/intl/media/corporate/sales-volumes/')
add(V2, 2025, 'CY', 332667, 'retail', 'press_release', 'Volvo Cars sales volumes December 2025', 'https://www.volvocars.com/intl/media/corporate/sales-volumes/', region='Europe')
add(V2, 2025, 'CY', 121607, 'retail', 'press_release', 'Volvo Cars sales volumes December 2025', 'https://www.volvocars.com/intl/media/corporate/sales-volumes/', region='United States')
add(V2, 2025, 'CY', 710042 - 332667 - 121607, 'retail', 'derived', 'Volvo Cars 2025: world minus Europe and US', 'https://www.volvocars.com/intl/media/corporate/sales-volumes/', region='Rest of world (incl. China)')
C = 'Chery Group'
add(C, 2025, 'CY', 2806393, 'wholesale', 'media', 'Chery Group 2025 sales release (1 Jan 2026), via Gasgoo', 'https://autonews.gasgoo.com/articles/news/gasgoo-daily-chery-group-sells-over-28-million-vehicles-in-2025-2007745520300986369', scope='Chery, Exeed, Jetour, iCar, Luxeed; incl. exports')
add(C, 2024, 'CY', 2603916, 'wholesale', 'derived', 'Chery Group 2025 back-calculated from the reported +7.8%', 'https://carz.com.my/2026/01/chery-group-crowned-as-best-selling-chinese-suv-brand-globally-in-2025', scope='incl. exports', notes='approximate (reported 2024 figure 2.60 M)')
add(C, 2025, 'CY', 1344020, 'wholesale', 'media', 'Chery Group 2025 exports', 'https://carnewschina.com/2026/01/02/one-chery-vehicle-was-exported-every-23-seconds-in-2025-maintaining-its-lead-position-for-23-years', region='Exports')
add(C, 2025, 'CY', 2806393 - 1344020, 'wholesale', 'derived', 'Chery Group 2025: total minus exports', '', region='China (domestic)')
CH = 'Changan Automobile'
add(CH, 2025, 'CY', 2913000, 'wholesale', 'media', 'Changan Automobile 2025 sales (Thairath / Gasgoo)', 'https://en.thairath.co.th/news/auto/2906199', scope='Changan group brands incl. Avatr, Deepal; incl. JVs', notes='about 2.913 M, +8.5%')
add(CH, 2024, 'CY', 2684000, 'wholesale', 'media', 'Changan Automobile 2024 sales (36Kr)', 'https://eu.36kr.com/en/p/3765016521523712')
add(CH, 2025, 'CY', 637000, 'wholesale', 'media', 'Changan Automobile 2025 exports (News18)', 'https://english.news18a.com/news/english_247026.html', region='Exports')
SA = 'SAIC Motor'
add(SA, 2025, 'CY', 4507000, 'wholesale', 'media', 'SAIC Motor 2025 sales (Gasgoo)', 'https://autonews.gasgoo.com/articles/news/saic-motor-full-year-sales-reach-4507-million-vehicles-2008175553880559616', scope='incl. SAIC-GM, SAIC-GM-Wuling, SAIC-VW, MG, IM, Maxus', notes='4.507 M (+12.3%); retail 4.67 M')
add(SA, 2024, 'CY', 4012000, 'wholesale', 'derived', 'SAIC Motor 2025 back-calculated from the reported +12.3% (CLS table: 4.01 M)', 'https://carnewschina.com/2026/02/26/three-chinese-automakers-enter-global-top-10-as-2025-sales-rankings-finalized/', notes='approximate')
add(SA, 2025, 'CY', 1071000, 'wholesale', 'media', 'SAIC Motor 2025 overseas sales (emobilityplus)', 'https://emobilityplus.com/2026/01/07/saic-motor-posts-record-2025-sales-as-ev-push-and-global-expansion-drive-growth/amp/', region='Overseas')
GW = 'Great Wall Motor'
add(GW, 2025, 'CY', 1323672, 'wholesale', 'media', 'Great Wall Motor 2025 sales (Gasgoo)', 'https://autonews.gasgoo.com/articles/market-industry/great-wall-motor-posts-record-full-year-sales-in-2025-despite-dec-slowdown-2007721483185168384', scope='Haval, Wey, Tank, Ora, pickups; incl. exports')
add(GW, 2024, 'CY', 1233000, 'wholesale', 'derived', 'GWM 2025 back-calculated from the reported +7.33%', '', notes='approximate')
add(GW, 2025, 'CY', 506066, 'wholesale', 'media', 'Great Wall Motor 2025 overseas sales (Gasgoo)', 'https://autonews.gasgoo.com/articles/market-industry/great-wall-motor-posts-record-full-year-sales-in-2025-despite-dec-slowdown-2007721483185168384', region='Overseas')
add('Dongfeng Motor Group', 2025, 'CY', 1896185, 'wholesale', 'media', 'Dongfeng Motor Group HKEX unaudited sales results Dec 2025 (via TipRanks)', 'https://www.tipranks.com/news/company-announcements/dongfeng-motor-group-reports-mixed-sales-results-for-2025-2', scope='listed Dongfeng Motor Group (excludes some parent-company units)')
add('Dongfeng Motor Group', 2024, 'CY', 1895934, 'wholesale', 'media', 'Dongfeng Motor Group HKEX unaudited sales results Dec 2025 (prior-year column)', 'https://www.tipranks.com/news/company-announcements/dongfeng-motor-group-reports-mixed-sales-results-for-2025-2', scope='listed Dongfeng Motor Group')
add('GAC Group', 2025, 'CY', 1721489, 'wholesale', 'media', 'GAC Group 2025 sales (-14.06%)', 'https://english.news18a.com/m/news/english_242991.html', scope='incl. GAC Honda, GAC Toyota, Aion, Trumpchi')
add('GAC Group', 2024, 'CY', 2003000, 'wholesale', 'derived', 'GAC 2025 back-calculated from the reported -14.06%', '', notes='approximate')
add('FAW Group', 2025, 'CY', 3302000, 'wholesale', 'media', 'FAW Group 2025 sales (Gasgoo)', 'https://autonews.gasgoo.com/articles/other/faw-hongqi-2025-sales-reach-460063-vehicles-up-117-year-on-year-2007836925610430465', scope='incl. FAW-VW, FAW Toyota, Hongqi, commercial vehicles')
add('BAIC Group', 2025, 'CY', 1752000, 'wholesale', 'media', 'BAIC Group 2025 sales (News18 / BAIC)', 'https://english.news18a.com/news/english_244695.html', scope='incl. Beijing Benz, Beijing Hyundai, BAIC BluePark')
add('BAIC Group', 2024, 'CY', 1710000, 'wholesale', 'media', 'BAIC Group 2024 sales (Gasgoo via SMM: "over 1.71 million")', 'https://news.metal.com/newscontent/103135208')

# EV start-ups and others
for ent, y, v, conf, src, url, nt in [
    ('Leapmotor', 2025, 596555, 'media', 'Yicai Global: 2025 delivery results', 'https://www.yicaiglobal.com/news/leapmotor-xpeng-xiaomi-are-only-chinese-ev-startups-to-achieve-2025-delivery-target', ''),
    ('Leapmotor', 2024, 293724, 'media', 'Leapmotor 2024 deliveries', 'https://www.yicaiglobal.com/news/leapmotor-xpeng-xiaomi-are-only-chinese-ev-startups-to-achieve-2025-delivery-target', 'prior year; 2025 reported +103%'),
    ('Li Auto', 2025, 406343, 'media', 'Yicai Global: 2025 delivery results', 'https://www.yicaiglobal.com/news/leapmotor-xpeng-xiaomi-are-only-chinese-ev-startups-to-achieve-2025-delivery-target', ''),
    ('Li Auto', 2024, 500508, 'media', 'Li Auto 2024 deliveries (2025 reported -19%)', 'https://www.yicaiglobal.com/news/leapmotor-xpeng-xiaomi-are-only-chinese-ev-startups-to-achieve-2025-delivery-target', ''),
    ('Xiaomi (auto)', 2025, 410000, 'media', 'Xiaomi: over 410,000 vehicles delivered in 2025 (Lei Jun)', 'https://www.yicaiglobal.com/news/leapmotor-xpeng-xiaomi-are-only-chinese-ev-startups-to-achieve-2025-delivery-target', 'rounded ("over 410,000")'),
    ('Xiaomi (auto)', 2024, 135000, 'media', 'Xiaomi 2024 deliveries ("over 135,000")', 'https://carnewschina.com/2025/11/03/xpeng-achieves-2025-sales-target-two-months-early-only-three-nev-brands-on-track/', 'rounded'),
    ('XPeng', 2025, 429445, 'media', 'Yicai Global: 2025 delivery results', 'https://www.yicaiglobal.com/news/leapmotor-xpeng-xiaomi-are-only-chinese-ev-startups-to-achieve-2025-delivery-target', ''),
    ('XPeng', 2024, 190068, 'media', 'XPeng 2024 deliveries', 'https://www.yicaiglobal.com/news/leapmotor-xpeng-xiaomi-are-only-chinese-ev-startups-to-achieve-2025-delivery-target', ''),
    ('NIO', 2025, 326028, 'media', 'Yicai Global: 2025 delivery results', 'https://www.yicaiglobal.com/news/leapmotor-xpeng-xiaomi-are-only-chinese-ev-startups-to-achieve-2025-delivery-target', 'NIO + onvo + firefly'),
    ('NIO', 2024, 221970, 'media', 'NIO 2024 deliveries (2025 reported +47%)', 'https://www.yicaiglobal.com/news/leapmotor-xpeng-xiaomi-are-only-chinese-ev-startups-to-achieve-2025-delivery-target', ''),
    ('Seres Group', 2025, 472269, 'media', 'Seres Group 2025 NEV sales (+10.63%), AITO about 426,000', 'https://kyodonewsprwire.jp/index.php/release/202602033498', 'NEV sales'),
    ('Seres Group', 2024, 426900, 'derived', 'Seres 2025 back-calculated from the reported +10.63%', 'https://kyodonewsprwire.jp/index.php/release/202602033498', 'approximate'),
    ('Perodua', 2025, 359904, 'media', 'Perodua 2025 sales (paultan / carz)', 'https://carz.com.my/2026/01/perodua-shifted-359904-units-in-2025-bezza-remains-its-best-seller', 'Malaysia'),
    ('Perodua', 2024, 358102, 'media', 'Perodua 2024 sales (paultan / carz)', 'https://carz.com.my/2026/01/perodua-shifted-359904-units-in-2025-bezza-remains-its-best-seller', 'Malaysia'),
    ('Proton', 2025, 151561, 'media', 'Proton 2025 total sales (paultan)', 'https://paultan.org/cn/2026/01/12/top-20-brands-in-2025-perodua-sold-over-double-proton-toyota-3rd-honda-4th-jaecoo-5th-byd-6th', 'Malaysia + exports'),
]:
    add(ent, y, 'CY', v, 'deliveries' if ent in ('Leapmotor', 'Li Auto', 'Xiaomi (auto)', 'XPeng', 'NIO') else 'wholesale', conf, src, url, notes=nt)
add('Tesla', 2025, 'CY', 1636129, 'deliveries', 'media', 'Tesla Q4 2025 production and deliveries report', 'https://driveteslacanada.ca/news/tesla-misses-q4-delivery-consensus-by-narrow-margin-as-energy-outperforms/', scope='Model 3/Y/S/X/Cybertruck/Semi')
add('Tesla', 2024, 'CY', 1789226, 'deliveries', 'media', 'Tesla Q4 2024 production and deliveries report', 'https://electrek.co/2026/01/02/tesla-tsla-releases-q4-delivery-results/', scope='Model 3/Y/S/X/Cybertruck/Semi')
add('Tesla', 2023, 'CY', 1808581, 'deliveries', 'media', 'Tesla Q4 2023 production and deliveries report', 'https://electrek.co/2026/01/02/tesla-tsla-releases-q4-delivery-results/', scope='Model 3/Y/S/X/Cybertruck/Semi')

# India (fiscal years, April-March)
add('Mahindra & Mahindra', 2025, 'FY', 1117698, 'wholesale', 'media', 'Mahindra FY2025-26 auto sales (domestic + exports; excludes SML Isuzu)', 'https://www.mahindra.com/sites/default/files/2026-04/SEIntimationApril2026PR.pdf', scope='SUVs 660,276 + LCV <3.5t 289,597 + other segments incl. three-wheelers; FY label 2025 = Apr 2025-Mar 2026')
add('Mahindra & Mahindra', 2025, 'FY', 40990, 'wholesale', 'media', 'Mahindra FY2025-26 total exports', 'https://www.mahindra.com/sites/default/files/2026-04/SEIntimationApril2026PR.pdf', region='Exports')
add('Jaguar Land Rover (Tata Motors)', 2025, 'FY', 307900, 'wholesale', 'press_release', 'JLR FY26 sales release (2 Apr 2026)', 'https://media.jaguarlandrover.com/news/2026/04/jlr-q4-sales-bounce-back-after-cyber-incident', scope='Apr 2025-Mar 2026; wholesales excl. CJLR', notes='-23.2% vs FY25; retail 352,300 (-17.8%) incl. CJLR')
add('Jaguar Land Rover (Tata Motors)', 2025, 'FY', 352300, 'retail', 'press_release', 'JLR FY26 sales release (2 Apr 2026)', 'https://media.jaguarlandrover.com/news/2026/04/jlr-q4-sales-bounce-back-after-cyber-incident', segment='Retail (incl. CJLR)', additive=False)
add('Tata Motors Passenger Vehicles (India)', 2025, 'FY', 642000, 'wholesale', 'media', 'Tata Motors PV FY26 domestic wholesales (record 6.42 lakh, +15%)', 'https://blog.gaadikey.com/tata-motors-fy26-results-6-4-lakh-record-pv-sales-105-4k-cr-q4-revenue/', scope='India domestic PV; rounded to 1,000')

# ---- domestic complements of the "exports / overseas" lines above, so each region set sums to its world total
for ent, y, pt, world, part, label, partlabel, src in [
    ('Changan Automobile', 2025, 'CY', 2913000, 637000, 'China (domestic)', 'Exports', 'Changan 2025: total minus exports'),
    ('Geely Automobile Holdings', 2025, 'CY', 3024567, 420097, 'China (domestic)', 'Exports', 'Geely Auto 2025: total minus exports (domestic incl. small other markets)'),
    ('Great Wall Motor', 2025, 'CY', 1323672, 506066, 'China (domestic)', 'Overseas', 'GWM 2025: total minus overseas'),
    ('SAIC Motor', 2025, 'CY', 4507000, 1071000, 'China (domestic)', 'Overseas', 'SAIC 2025: total minus overseas'),
    ('Mahindra & Mahindra', 2025, 'FY', 1117698, 40990, 'India (domestic)', 'Exports', 'Mahindra FY2025-26: total minus exports'),
    ('Maruti Suzuki India', 2025, 'FY', 2422713, 447774, 'India (domestic, incl. sales to other OEMs)', 'Exports', 'Maruti Suzuki FY2025-26: total minus exports'),
]:
    add(ent, y, pt, world - part, 'wholesale', 'derived', src, '', region=label)
