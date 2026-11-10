# Data Dictionary

## Raw files (`data/raw/`, unmodified API output)

| File | Content |
|---|---|
| `NY.GDP.PCAP.PP.KD.json` | All records returned by `GET /v2/country/all/indicator/NY.GDP.PCAP.PP.KD?date=2000:2025`, with the API header from the first page. Includes aggregates. |
| `SP.DYN.LE00.IN.json` | Same structure for life expectancy. |
| `countries.json` | `GET /v2/country`: all 296 API entities (217 economies + 79 aggregates), with region and income group. |
| `indicator_metadata.json` | Official WDI metadata for both indicators (definition, unit, source, licence). |
| `archive/SP.DYN.LE00.IN_v{202503,202504}.json.gz` | Life expectancy from archived WDI releases (WDI Database Archives, API source 57), March and April 2025. Complete API responses (all entities, 1960 onward), stored as lossless deterministic gzip. Used only by `audit/run_audit.py`. |
| `archive/ARCHIVE_MANIFEST.json` | SHA-256 and size of each original download and each `.gz` file. Also lists the unpublished, value-identical 2024-12 release under `not_published`. |
| `download_manifest.json` | UTC retrieval time, request URLs, record counts, API `lastupdated` stamp and SHA-256 checksums. |

## Source indicators

| Code | Official name | Unit | Licence | Original source |
|---|---|---|---|---|
| `NY.GDP.PCAP.PP.KD` | GDP per capita, PPP (constant 2021 international $) | Constant 2021 international $ per person | CC BY-4.0 | World Bank, International Comparison Program (ICP); national accounts |
| `SP.DYN.LE00.IN` | Life expectancy at birth, total (years) | Years | CC BY-4.0 | UN World Population Prospects; national statistical offices; Eurostat |

Definitions, units and licence were read from the API metadata endpoint (`/v2/sources/2/series/<code>/metadata`) and are stored in `data/raw/indicator_metadata.json`.

## `data/processed/country_year_panel.csv`

One row per **economy × year** for 217 economies × 2000–2024 = 5,425 rows. Aggregates are excluded. Rows with missing data are **kept** and labelled.

| Column | Type | Unit / values | Description |
|---|---|---|---|
| `iso3` | string | ISO 3166-1 alpha-3 (World Bank variant, e.g. `XKX` Kosovo, `CHI` Channel Islands) | Economy code |
| `name` | string | – | World Bank economy name |
| `region` | string | WB region | Geographic region (descriptive only) |
| `income_level` | string | WB income group (current classification) | Descriptive only; not used in models |
| `year` | int | 2000–2024 | Calendar year |
| `gdp_pc_ppp` | float | constant 2021 international $ | GDP per capita, PPP. NaN if missing |
| `log_gdp_pc` | float | natural log of int'l $ | ln(`gdp_pc_ppp`). Computed only when `gdp_pc_ppp` > 0, otherwise NaN |
| `life_expectancy` | float | years | Life expectancy at birth, both sexes |
| `missing_gdp` | bool | – | GDP value absent in the API |
| `missing_le` | bool | – | Life expectancy absent in the API |
| `nonpositive_gdp` | bool | – | GDP ≤ 0 (none in the current data) |
| `invalid_le` | bool | – | Life expectancy outside (0, 120] (none in the current data) |
| `le_extreme_low` | bool | – | Life expectancy < 40 years. **Flagged but kept** |
| `le_transient_shock` | bool | – | Value differs by > 5 years from **both** adjacent years. **Flagged but kept** |
| `exclusion_reason` | string | `""`, `missing_gdp`, `missing_le`, `missing_both`, `nonpositive_gdp`, `invalid_le` | Why the row is not in the analysis sample (first rule that applies) |
| `in_analysis` | bool | – | True when both indicators are present and valid |

## `data/processed/analysis_sample.csv`

The rows of the panel where `in_analysis` is true: 4,916 economy-years, 199 economies. Same columns, minus `exclusion_reason` and `in_analysis`.

## Other processed files

| File | Description |
|---|---|
| `entity_classification.csv` | Every API entity with `is_aggregate` (true when `region == "Aggregates"`). |
| `coverage_by_year.csv` | Economies with GDP, with life expectancy, and with both, per year. |
| `coverage_by_country.csv` | Usable years per economy, with first and last usable year. |
| `cleaning_log.json` | Counts for each cleaning step and the list of flagged observations. |

## Derived analysis variables (created in `src/statistical_analysis.py`, not stored)

| Variable | Definition |
|---|---|
| `gdp_k` | `gdp_pc_ppp / 1000` (thousands of 2021 int'l $), the regressor in Model A |
| `log_gdp_c` | `log_gdp_pc` minus its sample mean, used in the quadratic Model C |
| `d_le`, `d_log_gdp` | Change in life expectancy and in ln GDP between two years (long-difference tables) |
