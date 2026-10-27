"""Country table and hand-entered official counts for the charging stations page (build_charging.py reads this).

COUNTRIES: iso2 -> (name as used by the site / population-energy data, IEA region name or None, supercharge.info country name or None)
OFFICIAL: national statistics read from the official publisher (stations and ports), where one exists and is free.
"""

COUNTRIES = {
    'CN': ('China', 'China', 'China'), 'US': ('United States', 'USA', 'USA'), 'DE': ('Germany', 'Germany', 'Germany'),
    'GB': ('United Kingdom', 'United Kingdom', 'United Kingdom'), 'FR': ('France', 'France', 'France'), 'NO': ('Norway', 'Norway', 'Norway'),
    'NL': ('Netherlands', 'Netherlands', 'Netherlands'), 'SE': ('Sweden', 'Sweden', 'Sweden'), 'IT': ('Italy', 'Italy', 'Italy'),
    'ES': ('Spain', 'Spain', 'Spain'), 'CA': ('Canada', 'Canada', 'Canada'), 'JP': ('Japan', 'Japan', 'Japan'),
    'KR': ('South Korea', 'Korea', 'South Korea'), 'AU': ('Australia', 'Australia', 'Australia'), 'BE': ('Belgium', 'Belgium', 'Belgium'),
    'CH': ('Switzerland', 'Switzerland', 'Switzerland'), 'AT': ('Austria', 'Austria', 'Austria'), 'DK': ('Denmark', 'Denmark', 'Denmark'),
    'TR': ('Turkey', 'Turkiye', 'Turkey'), 'BR': ('Brazil', 'Brazil', None), 'IN': ('India', 'India', 'India'), 'TH': ('Thailand', 'Thailand', 'Thailand'),
    'PL': ('Poland', 'Poland', 'Poland'), 'PT': ('Portugal', 'Portugal', 'Portugal'), 'FI': ('Finland', 'Finland', 'Finland'),
    'MX': ('Mexico', 'Mexico', 'Mexico'), 'ID': ('Indonesia', 'Indonesia', None), 'VN': ('Vietnam', 'Viet Nam', None),
    'NZ': ('New Zealand', 'New Zealand', 'New Zealand'), 'IE': ('Ireland', None, 'Ireland'), 'AE': ('UAE', None, 'United Arab Emirates'),
    'IL': ('Israel', 'Israel', 'Israel'), 'MY': ('Malaysia', 'Malaysia', 'Malaysia'), 'SG': ('Singapore', 'Singapore', 'Singapore'),
    'CZ': ('Czechia', None, 'Czech Republic'), 'GR': ('Greece', 'Greece', 'Greece'), 'IS': ('Iceland', 'Iceland', 'Iceland'),
    'LU': ('Luxembourg', None, 'Luxembourg'), 'HU': ('Hungary', None, 'Hungary'), 'RO': ('Romania', None, 'Romania'),
    'SK': ('Slovakia', None, 'Slovakia'), 'SI': ('Slovenia', None, 'Slovenia'), 'HR': ('Croatia', None, 'Croatia'),
    'BG': ('Bulgaria', None, 'Bulgaria'), 'EE': ('Estonia', None, 'Estonia'), 'LV': ('Latvia', None, 'Latvia'), 'LT': ('Lithuania', None, None),
    'CL': ('Chile', 'Chile', 'Chile'), 'CO': ('Colombia', 'Colombia', 'Colombia'), 'CR': ('Costa Rica', 'Costa Rica', None),
    'PH': ('Philippines', 'Philippines', 'Philippines'), 'ZA': ('South Africa', 'South Africa', None), 'HK': ('Hong Kong', None, None),
    'TW': ('Taiwan', None, 'Taiwan'), 'SA': ('Saudi Arabia', None, 'Saudi Arabia'), 'UY': ('Uruguay', None, None),
    'RU': ('Russian Federation', 'Russia', None), 'JO': ('Jordan', 'Jordan', 'Jordan'),
}

# US: Alternative Fuels Data Center (US DOE), "Electric Charging Stations and Ports by State", data last updated 2026-10-27
OFFICIAL = {
    'CA': dict(stations=14743, ports=39654, ports_dc_fast=8431, ports_l2=31172, year=2026, as_of='2026-03-25',
               source='Natural Resources Canada charging stations locator (public ports and locations, some networks not listed), as reported in the 2026 Electric Autonomy network report',
               url='https://electricautonomy.ca/data-trackers/public-charging-networks/2026-04-01/2026-ev-charging-network-report-steady-progress/'),
    'US': dict(stations=83559, ports=262578, ports_dc_fast=79200, ports_l2=182673, ports_l1=693, year=2026, as_of='2026-10-27',
               source='US DOE Alternative Fuels Data Center (public + legacy chargers, excl. residential)', url='https://afdc.energy.gov/stations/states'),
}

# AFDC "Charging networks" page (ports; networks marked NA operate in the US and Canada, the AFDC does not split them), imported 2026-10-13..27
AFDC_NETWORKS_NA = [
    ('ChargePoint', 92700), ('Tesla Supercharger', 43469), ('Blink', 22326), ('Tesla Destination', 16243), ('FLO', 12835), ('Loop', 10035),
    ('Circuit électrique', 8197), ('Electrify America', 6219), ('EVgo', 5324), ('Red E Charge', 4830), ('ViaLynk', 4936), ('EV Connect', 4647),
    ('SWTCH Energy', 4002), ('AmpUp', 3513), ('PowerFlex', 3000), ('EvGateway', 2788), ('ChargeLab', 2573), ('EVoke Systems', 2538),
    ('OpConnect', 2066), ('Noodoe', 2001), ('IONNA', 1688), ('EVCS', 1589), ('Ford Charge', 1364), ('FLASH', 1259), ('QuickCharge', 1249),
    ('EnviroSpark', 1203), ('Rivian Adventure Network', 1172), ('EVOLV Charging', 1181), ('ChargeUP', 1146), ('synergEV', 1050),
    ('Francis Energy', 1013), ('BC Hydro', 924), ('Walmart', 916), ('CircleK/Couche-Tard Recharge (Canada)', 246), ('CircleK Charge (US)', 140), ('bp pulse', 850), ('Mercedes-Benz High-Power Charging', 810),
    ('ZEF Network', 795), ('Shell Recharge', 684), ('Rivian Waypoints', 539), ('Electrify Canada', 272), ('Non-Networked', 18008),
]
AFDC_NETWORKS_SOURCE = 'US DOE Alternative Fuels Data Center, charging networks (ports; US and Canada combined for multi-country networks)'
AFDC_NETWORKS_URL = 'https://afdc.energy.gov/stations/charging-networks'

# China: public charging piles by operator, China Charging Alliance (EVCIPA) statistics for July 2025 as tabulated by CarNewsChina
# (https://carnewschina.com/?p=236276). The top 15 hold 84.1% of the public piles, which implies about 4.29 M public piles in total.
CHINA_OPERATORS = [('TELD', 807000), ('Star Charge', 703000), ('YKC (Yunkuaichong)', 656000), ('Orange Charge', 268000), ('EV King', 238000), ('State Grid', 196000),
                   ('Lv C-Chong', 142000), ('Car Energy Net', 109000), ('Hoo Energy', 95000), ('China Southern Power Grid', 90000), ('EV Power', 79000),
                   ('Kunlun', 64000), ('Wancheng Wanchong', 55000), ('Winlands', 53000), ('Hard Hitter', 49000)]
CHINA_TOP15_SHARE = 0.841
CHINA_NOTE = 'Public charging piles by operator, China Charging Alliance (EVCIPA), July 2025, as tabulated by CarNewsChina. No station count or speed split; "Other operators" = the 15.9% outside the top 15.'
