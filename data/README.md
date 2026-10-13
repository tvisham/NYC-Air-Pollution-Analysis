# Data

| File | What it is | Source | License |
|---|---|---|---|
| `air_quality.csv` | Pollutant levels, emission sources, and estimated health impacts for NYC, 2005–2024. 19,827 rows. | [NYC Open Data: Air Quality](https://data.cityofnewyork.us/Environment/Air-Quality/c3uy-2p5r) (NYC Department of Health and Mental Hygiene, New York City Community Air Survey). Also listed on [data.gov](https://catalog.data.gov/dataset/air-quality). | NYC Open Data terms of use (public) |
| `uhf42.geojson` | Boundaries of the 42 United Hospital Fund (UHF42) neighborhoods. | [NYC DOHMH Environment & Health Data Portal, EHDP-data repo](https://github.com/nychealth/EHDP-data/tree/production/geography) | Apache License 2.0 |

The CSV snapshot was downloaded in October 2026. Run `python scripts/download_data.py` to get the latest release.

## How the CSV is organized

Each row is one indicator, for one place, for one time period. The same indicator is published at five geography levels: Citywide, Borough, UHF34, UHF42, and community district (CD). **Never mix levels in one comparison.** A borough row and the neighborhoods inside it describe the same air, so mixing them double-counts areas. This analysis uses:

- **Citywide** rows for trends over time
- **UHF42** rows for comparing neighborhoods

Key columns: `Name` (indicator), `Measure` (e.g. "Annual mean", "Summer mean"), `Geo Type Name`, `Geo Join ID` (matches `GEOCODE` in the GeoJSON), `Geo Place Name`, `Time Period`, `Data Value`.

Pollution levels are modeled estimates from the city's street-level monitoring network, not raw readings from single monitors. Health indicators are the city's estimates of ER visits, hospitalizations, and deaths attributable to pollution, not counts of observed cases.
