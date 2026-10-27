// Central catalog of every stat page on the site.
// Add a new entry here whenever a new stat page is published — the
// Home page search box and browse grid are both driven from this list.
const STATS_CATALOG = [
  {
    title: "Auto Markets by Country",
    subject: "World · Market Size",
    keywords: ["market size", "total", "registrations", "volume", "country", "world", "biggest", "largest", "smallest", "growth", "momentum", "1999", "2005", "2026"],
    description: "Total new vehicle registrations by country and year, 147 markets back to 1999 — market size, not powertrain mix.",
    tag: "1999–2026",
    url: "auto-markets-by-country.html"
  },
  {
    title: "Powertrain Mix by Country",
    subject: "Europe · Powertrain",
    keywords: ["ev", "electric", "bev", "phev", "hev", "hybrid", "petrol", "diesel", "powertrain", "fuel type", "europe", "eu", "country", "market share", "may 2026"],
    description: "How EV, hybrid, petrol and diesel registrations compare across 31 European markets — ranked by electrified share, May 2026.",
    tag: "May 2026",
    url: "powertrain-mix-by-country.html"
  },
  {
    title: "EV Charging",
    subject: "World · Charging infrastructure",
    keywords: ["charging", "charger", "stations", "ports", "ev charging", "supercharger", "tesla", "ionity", "fast charging", "kw", "operators", "brands", "per capita", "per ev"],
    description: "Public charging points, stations and ports in 58 countries: slow / fast / ultra-fast, per 100k people aged 15-64 and per EV, with brands and power bands, on a map that zooms to street level.",
    tag: "2019–2026",
    url: "charging-stations.html"
  }
];
