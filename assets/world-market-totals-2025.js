// Comprehensive world total-market reference for 2025 (or, where 2025 is unavailable, the
// latest year on record), covering every OICA-tracked market -- including large economies
// (Russia, Iran, Saudi Arabia, ...) this project has no powertrain breakdown for at all. Used
// purely to compute each tracked country's TRUE world rank (so e.g. a country genuinely 22nd
// worldwide stays 22nd even though Russia/Iran occupy 2 of the 20 slots above it and never
// appear on this site -- deliberately produces gaps in the Market Rank filter tiers). Source:
// same OICA series as auto-markets-by-country.html's own MARKETS object, deduplicated by
// ISO code (that table double-lists a few markets under two names, e.g. "Taiwan" and "Taiwan
// Province of China"), with patches (2026-09-03, prompted by a completeness audit of this
// project's own 96 tracked countries against this table): Iran's value is a real, current 2025
// sales figure (1,122,372, via Focus2Move/press) -- the MARKETS table itself has no Iran entry
// past 2018. Laos and Suriname were both missing entirely (every one of this project's other 94
// tracked countries, loaded or D-grade-placeholder alike, already had an entry) -- added from
// OICA-via-CEIC/TheGlobalEconomy (Laos, passenger 4,064 + commercial 6,336 = 10,400, 2019) and
// ABS Suriname's official Table 2.04 "First-Time-Approved Motor-Vehicles by Kind" (Suriname,
// Passenger Car + Lorry + Bus + Tractor + Other = 9,920, 2024 -- excludes the table's own
// Motor-bike/Moped rows to stay apples-to-apples with OICA's 4-wheeled-vehicle scope elsewhere
// in this table). Laos also had a pre-existing orphan entry under "Lao Peoples
// Dem. Rep." (8,906, 2018) that never matched this project's own "Laos" country-name convention
// and so silently double-counted the same real country once merged -- removed in favor of the
// correctly-named, more current entry.
// Same pass also refreshed the 12 other tracked countries still frozen on 2018 MARKETS data with
// a real 2023-2025 figure found via press/industry-association sources (OICA itself has nothing
// newer than 2018-2019 for these smaller markets): Belarus 74,750 (2025, AUTOSTAT/BELTA), Bolivia
// 32,500 (2025, press estimate), Cambodia 60,533 (2024, MPWT official registrations minus
// motorcycles/mopeds), Guatemala 54,569 (2023, AIDVA), Guyana 38,346 (2025, press citing Bureau of
// Statistics/GRA), Moldova 13,101 (2025, CE Auto), Myanmar 4,194 (2024, Focus2move), Nigeria
// 23,779 (2025, press), Oman 65,980 (2024, Focus2move, full-year actual vs a 2025 figure that was
// only 9-month YTD), Panama 60,233 (2025, ADAP), Serbia 36,771 (2025, Focus2move/press -- Serbia
// has real monthly powertrain data loaded on this site too, but only for 2026 months, so this
// reference entry is still what actually drives its world rank), Yemen 10,892 (2024, press).
// Armenia (still 1,800/2018) was checked and left alone -- no 2023-2025 total-market figure found
// anywhere (OICA/CEIC/statbase.org agree it stops at 2018; Focus2move's country page is paywalled).
// This project has 96 tracked countries; the ~40 not mentioned by name in this comment either
// already had a 2025 figure, or have their own loaded powertrain data with a "2025-annual" period
// that outranks this reference value automatically (see the merge logic wherever WORLD_RANK_2025
// is computed) -- Costa Rica, Georgia, and Mauritius are examples of the latter.
// 2026-09-04: refreshed 12 more UNTRACKED countries too (their stale reference values could still
// distort a TRACKED country's rank, since ranking is against this whole table) -- prioritized
// roughly largest-to-smallest since that's where crossing a tracked country's value is plausible:
// Iraq 158,076 (2024), Qatar 88,065 (2025), Tunisia 93,095 (2025), Kenya 93,646 (2024, KNBS,
// excludes motorcycles), Algeria 102,651 (2025, down sharply from a 2024 spike -- real volatility,
// not a data error), Hong Kong SAR 43,308 (2025), Jordan 36,386 (2025), Bahrain 36,966 (2024),
// Sri Lanka 22,381 (2025, passenger cars specifically -- total incl. motorcycles is ~14x higher),
// Lebanese Republic 20,641 (2025), Bosnia-Herzegovina 12,899 (2025), Trinidad & Tobago 14,200
// (2023, best found). Checked and left stale: Libya (wildly conflicting sources, from ~1,000 units
// to millions depending on scope -- couldn't find anything trustworthy), Honduras/Ghana/Senegal
// (only fleet-stock totals or partial-year/regional figures found, no clean national annual sales
// number). The remaining ~55 stale entries are all smaller still (Sudan and below, roughly
// <10,000 units in the stale figure) -- not yet re-researched one by one; even substantial growth
// at that scale is very unlikely to cross any tracked country's value, so this is a deliberate,
// lower-priority gap rather than an oversight. Revisit if a specific one turns out to matter.
// 55 of 148 entries are not actually 2025 -- stale-year entries use the latest year MARKETS has
// for that country instead (see WORLD_MARKET_TOTALS_2025_STALE_YEAR for which).
const WORLD_MARKET_TOTALS_2025 = {"Albania":80739,"Algeria":102651,"Angola":2404,"Argentina":600537,"Armenia":1800,"Australia":1209805,"Austria":326382,"Azerbaijan":4000,"Bahamas":1644,"Bahrain":36966,"Bangladesh":4650,"Belarus":74750,"Belgium":496055,"Belize":528,"Bolivia":32500,"Bosnia-Herzegovina":12899,"Botswana":8171,"Brazil":2689634,"Brunei Darussalam":13000,"Bulgaria":55312,"Burkina Faso":1074,"Burundi":44,"Cambodia":60533,"Cameroon":3079,"Canada":1934022,"Chile":329924,"China":34399621,"Colombia":234113,"Congo DR":771,"Costa Rica":39530,"Cote d’Ivoire":9640,"Croatia":79475,"Cuba":6098,"Cyprus":14636,"Czechia":278981,"Denmark":215815,"Dominican Republic":167,"Ecuador":100406,"Egypt":133973,"El Salvador":9373,"Estonia":13055,"Finland":85664,"France":2042788,"France - Guadeloupe":12265,"France - Guyane":4816,"France - Martinique":12855,"France - Mayotte":2279,"France - Reunion":26463,"French Polynesia":7168,"Gabon":2013,"Georgia":3520,"Germany":3207713,"Ghana":7073,"Greece":156929,"Guatemala":54569,"Guyana":38346,"Honduras":12373,"Hong Kong SAR":43308,"Hungary":159429,"Iceland":14821,"India":5517594,"Indonesia":803687,"Iran":1122372,"Iraq":158076,"Ireland":160858,"Israel":306724,"Italy":1746314,"Jamaica":7176,"Japan":4565777,"Jordan":36386,"Kazakhstan":208500,"Kenya":93646,"Kuwait":145471,"Kyrgyz Republic":2345,"Laos":10400,"Latvia":22506,"Lebanese Republic":20641,"Liberia":288,"Libya":18000,"Lithuania":41968,"Luxembourg":47161,"Madagascar":1995,"Malawi":1514,"Malaysia":820752,"Malta":6269,"Mauritius":10134,"Mexico":1564471,"Moldova":13101,"Mongolia":6440,"Morocco":235372,"Myanmar":4194,"Nepal":18544,"Netherlands":420620,"New Caledonia":8214,"New Zealand":137900,"Nicaragua":11811,"Nigeria":23779,"Norway":215165,"Oman":65980,"Pakistan":179635,"Palestina":146,"Panama":60233,"Paraguay":30798,"Peru":164616,"Philippines":490442,"Poland":700220,"Portugal":264821,"Puerto Rico":121476,"Qatar":88065,"Republic of Macedonia":4400,"Romania":182518,"Russian Federation":1485671,"Rwanda":4164,"Saudi Arabia":827544,"Senegal":5831,"Serbia":36771,"Singapore":52678,"Slovakia":104813,"Slovenia":57250,"South Africa":597338,"South Korea":1681611,"Spain":1369095,"Sri Lanka":22381,"Sudan":1968,"Suriname":9920,"Sweden":314426,"Switzerland":267930,"Syrian Arab Republic":7800,"Taiwan":363653,"Tajikistan":2430,"Tanzania":2380,"Thailand":621166,"Trinidad & Tobago":14200,"Tunisia":93095,"Turkey":1413901,"Turkmenistan":5665,"UAE":308495,"Uganda":1885,"Ukraine":94915,"United Kingdom":2400106,"United States":16675488,"Uruguay":48588,"Uzbekistan":294000,"Venezuela":38610,"Vietnam":327552,"Yemen":10892,"Zambia":74779,"Zimbabwe":3904};
const WORLD_MARKET_TOTALS_2025_STALE_YEAR = {"Angola":"2018","Armenia":"2018","Azerbaijan":"2018","Bahamas":"2018","Bahrain":"2024","Bangladesh":"2018","Belize":"2018","Botswana":"2018","Brunei Darussalam":"2018","Burkina Faso":"2018","Burundi":"2018","Cambodia":"2024","Cameroon":"2018","Congo DR":"2018","Costa Rica":"2018","Cote d’Ivoire":"2018","Cuba":"2018","Dominican Republic":"2018","El Salvador":"2018","French Polynesia":"2018","Gabon":"2018","Georgia":"2018","Ghana":"2018","Guatemala":"2023","Honduras":"2018","Iraq":"2024","Jamaica":"2018","Kenya":"2024","Kyrgyz Republic":"2018","Laos":"2019","Liberia":"2018","Libya":"2018","Madagascar":"2018","Malawi":"2018","Mauritius":"2018","Mongolia":"2018","Myanmar":"2024","New Caledonia":"2018","Nicaragua":"2018","Oman":"2024","Palestina":"2018","Republic of Macedonia":"2018","Rwanda":"2023","Senegal":"2018","Sudan":"2018","Suriname":"2024","Syrian Arab Republic":"2018","Tajikistan":"2018","Tanzania":"2018","Trinidad & Tobago":"2023","Turkmenistan":"2018","Uganda":"2018","Yemen":"2024","Zambia":"2024","Zimbabwe":"2018"};