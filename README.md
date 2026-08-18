# World Auto Sales

Worldwide car sales stats — powertrain mix (EV/hybrid/petrol/diesel) and country comparisons, updated monthly.

Live site: https://francoissavard88.github.io/World_auto_sales/

## Pages

- `index.html` — home / catalog
- `powertrain-mix-by-country.html` — BEV/PHEV/HEV/Petrol/Diesel mix across 31 European markets, ranked by electrified share

## Data

Sourced from the `World_auto_sales` Supabase project (`vehicle_sales_by_powertrain`, `vehicle_sales_totals`), itself populated from:

- **ACEA** (European Automobile Manufacturers' Association) — monthly press releases, by-country by-powertrain registrations for EU + EFTA + UK (~31 markets). The richest free source found: monthly cadence, full BEV/PHEV/HEV/Petrol/Diesel/Others breakdown.

Coverage is currently Europe-only. No free source combines monthly cadence + full powertrain breakdown + near-global country coverage — broader markets (China, USA, etc.) will be added incrementally as sources are identified, at whatever granularity is available for each.
