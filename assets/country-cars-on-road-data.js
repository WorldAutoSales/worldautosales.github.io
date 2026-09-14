// On-road passenger-car fleet estimates (BEV vs non-BEV), by country and year, 2005-2041.
// Source: Supabase `country_cars_on_road` (project rtmlxvjpjxcvjdykrkvm), built by convolving
// world_auto_sales_annual new-registration counts with cars_duration_rate survival curves,
// anchored to real observed stock-by-fuel data (KBA FZ13 for Germany, SSB table 11823 for
// Norway) wherever it exists. See that table's column comments for full methodology.
//
// method per row:
//   REAL                            = directly observed official stock-by-fuel-type figure.
//   MODEL_RAW_PREREAL               = pure survival-curve convolution, used only before any real
//                                     stock-by-fuel data exists for that country (BEV is
//                                     negligible in this era regardless).
//   MODEL_ANCHORED                  = survival-curve convolution projected forward from the last
//                                     REAL year, rescaled to match it, assuming NO new
//                                     registrations after the last known registration year.
//   MODEL_ANCHORED_WITH_FUTURE_REG  = as above, but for 2027-2041 also adds newly-registered
//                                     cohorts each year, sized by `futureNewRegProj` (see below)
//                                     and its implied BEV count (constant total minus that),
//                                     each aged by the same survival curve from its own
//                                     registration year forward.
// futureNewRegProj: projected NEW non-BEV registrations for that year (2027-2041 rows only).
//   Germany: nonbev_2026 * (1+CAGR)^(year-2026), CAGR = compound annual growth rate of non-BEV
//   registrations from 2024 to 2026 (ACEA annual/projected figures) = -3.49%/yr.
//   Norway: same CAGR formula for 2027 only (CAGR -46.4%/yr, reflecting its near-total EV
//   transition); 2028 onward is floored to exactly 0 rather than left to asymptotically decay,
//   since Norway's BEV share is already 98%+ and treating the last sliver of non-BEV sales as
//   fully gone by 2028 is a reasonable simplification at that point.
//   Total registrations are held CONSTANT at the 2026 level; projected BEV registrations for
//   that year = constant total - futureNewRegProj.
const CARS_ON_ROAD = {
"Germany": [
  {"year":2005,"bev":0,"nonBev":3614886,"method":"MODEL_RAW_PREREAL"},
  {"year":2006,"bev":0,"nonBev":7387280,"method":"MODEL_RAW_PREREAL"},
  {"year":2007,"bev":0,"nonBev":10869559,"method":"MODEL_RAW_PREREAL"},
  {"year":2008,"bev":0,"nonBev":14294598,"method":"MODEL_RAW_PREREAL"},
  {"year":2009,"bev":0,"nonBev":18202970,"method":"MODEL_RAW_PREREAL"},
  {"year":2010,"bev":541,"nonBev":21224803,"method":"MODEL_RAW_PREREAL"},
  {"year":2011,"bev":2695,"nonBev":24543426,"method":"MODEL_RAW_PREREAL"},
  {"year":2012,"bev":7236,"nonBev":27690979,"method":"MODEL_RAW_PREREAL"},
  {"year":2013,"bev":13287,"nonBev":30589312,"method":"MODEL_RAW_PREREAL"},
  {"year":2014,"bev":18948,"nonBev":44384176,"method":"REAL"},
  {"year":2015,"bev":25502,"nonBev":45045707,"method":"REAL"},
  {"year":2016,"bev":34022,"nonBev":45769538,"method":"REAL"},
  {"year":2017,"bev":53861,"nonBev":46420733,"method":"REAL"},
  {"year":2018,"bev":83175,"nonBev":47012609,"method":"REAL"},
  {"year":2019,"bev":136617,"nonBev":47579360,"method":"REAL"},
  {"year":2020,"bev":309083,"nonBev":47939501,"method":"REAL"},
  {"year":2021,"bev":618460,"nonBev":47922418,"method":"REAL"},
  {"year":2022,"bev":1013009,"nonBev":47750027,"method":"REAL"},
  {"year":2023,"bev":1408681,"nonBev":47690004,"method":"REAL"},
  {"year":2024,"bev":1714922,"nonBev":48087691,"method":"MODEL_ANCHORED"},
  {"year":2025,"bev":2150143,"nonBev":48165196,"method":"MODEL_ANCHORED"},
  {"year":2026,"bev":2776675,"nonBev":47775819,"method":"MODEL_ANCHORED"},
  {"year":2027,"bev":3611619,"nonBev":47327132,"futureNewRegProj":2190407,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2028,"bev":4519939,"nonBev":46735560,"futureNewRegProj":2113964,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2029,"bev":5487217,"nonBev":46000522,"futureNewRegProj":2040190,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2030,"bev":6504370,"nonBev":45188967,"futureNewRegProj":1968990,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2031,"bev":7565416,"nonBev":43951174,"futureNewRegProj":1900275,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2032,"bev":8670135,"nonBev":42667606,"futureNewRegProj":1833958,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2033,"bev":9812654,"nonBev":41366785,"futureNewRegProj":1769955,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2034,"bev":10984680,"nonBev":40058370,"futureNewRegProj":1708186,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2035,"bev":12176737,"nonBev":38683315,"futureNewRegProj":1648572,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2036,"bev":13377765,"nonBev":37420493,"futureNewRegProj":1591039,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2037,"bev":14578198,"nonBev":36150475,"futureNewRegProj":1535514,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2038,"bev":15776472,"nonBev":34926604,"futureNewRegProj":1481927,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2039,"bev":16966470,"nonBev":33734940,"futureNewRegProj":1430210,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2040,"bev":18146690,"nonBev":32567848,"futureNewRegProj":1380297,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2041,"bev":19305710,"nonBev":31407946,"futureNewRegProj":1332127,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"}
],
"Norway": [
  {"year":2005,"bev":5,"nonBev":119297,"method":"MODEL_RAW_PREREAL"},
  {"year":2006,"bev":18,"nonBev":240106,"method":"MODEL_RAW_PREREAL"},
  {"year":2007,"bev":23,"nonBev":377961,"method":"MODEL_RAW_PREREAL"},
  {"year":2008,"bev":188,"nonBev":494638,"method":"MODEL_RAW_PREREAL"},
  {"year":2009,"bev":298,"nonBev":596742,"method":"MODEL_RAW_PREREAL"},
  {"year":2010,"bev":636,"nonBev":728392,"method":"MODEL_RAW_PREREAL"},
  {"year":2011,"bev":2515,"nonBev":869526,"method":"MODEL_RAW_PREREAL"},
  {"year":2012,"bev":6274,"nonBev":1007821,"method":"MODEL_RAW_PREREAL"},
  {"year":2013,"bev":13854,"nonBev":1145583,"method":"MODEL_RAW_PREREAL"},
  {"year":2014,"bev":31403,"nonBev":1272917,"method":"MODEL_RAW_PREREAL"},
  {"year":2015,"bev":56816,"nonBev":1398399,"method":"MODEL_RAW_PREREAL"},
  {"year":2016,"bev":97532,"nonBev":2564274,"method":"REAL"},
  {"year":2017,"bev":138983,"nonBev":2631663,"method":"REAL"},
  {"year":2018,"bev":195351,"nonBev":2700433,"method":"REAL"},
  {"year":2019,"bev":260692,"nonBev":2769974,"method":"REAL"},
  {"year":2020,"bev":340002,"nonBev":2829417,"method":"REAL"},
  {"year":2021,"bev":460734,"nonBev":2884061,"method":"REAL"},
  {"year":2022,"bev":599169,"nonBev":2842922,"method":"REAL"},
  {"year":2023,"bev":689169,"nonBev":2706062,"method":"REAL"},
  {"year":2024,"bev":788750,"nonBev":2592281,"method":"REAL"},
  {"year":2025,"bev":945182,"nonBev":1990556,"method":"REAL"},
  {"year":2026,"bev":1106478,"nonBev":1862182,"method":"MODEL_ANCHORED"},
  {"year":2027,"bev":1267063,"nonBev":1722905,"futureNewRegProj":2204,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2028,"bev":1427851,"nonBev":1575535,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2029,"bev":1585779,"nonBev":1424328,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2030,"bev":1739858,"nonBev":1271483,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2031,"bev":1889057,"nonBev":1116141,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2032,"bev":2032326,"nonBev":964529,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2033,"bev":2168270,"nonBev":818600,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2034,"bev":2295199,"nonBev":682094,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2035,"bev":2411532,"nonBev":557122,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2036,"bev":2515695,"nonBev":444461,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2037,"bev":2606732,"nonBev":346192,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2038,"bev":2684681,"nonBev":263184,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2039,"bev":2749955,"nonBev":195072,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2040,"bev":2803128,"nonBev":141122,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"},
  {"year":2041,"bev":2845124,"nonBev":99403,"futureNewRegProj":0,"method":"MODEL_ANCHORED_WITH_FUTURE_REG"}
]
};
