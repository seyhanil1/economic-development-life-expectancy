# Data Quality Report

Retrieved: **2026-11-10 13:46:55 UTC** · WDI database `lastupdated`: **2026-10-08** · Requested years: 2000–2025 · Analysis window: **2000–2024**

All numbers below come from `data/processed/cleaning_log.json` and the coverage tables. They are reproduced by `python src/clean_data.py`.

## 1. Completeness of the download

| Check | GDP per capita | Life expectancy |
|---|---|---|
| Records the API reports (`total`) | 6,916 | 6,916 |
| Records received across all pages | 6,916 | 6,916 |
| Entities × years (296 × 26 = 7,696)? | No: 6,916 = 266 entities × 26 years | same |

The API returns 266 of the 296 entities in its country list for these indicators. All 217 economies are present. The 30 entities that are absent are aggregates.

## 2. Entity codes and aggregates

* The country list contains **217 economies** and **79 aggregates** (`region.value == "Aggregates"`). Aggregates include World (`WLD`), OECD members (`OED`), the European Union (`EUU`), income groups, IDA/IBRD lending groups, demographic-dividend groups and regions.
* **Quirk found:** 130 records per indicator (5 entities × 26 years) have an **empty `countryiso3code`**. They belong to the income-group aggregates High income, Low income, Lower middle income, Upper middle income and "Not classified". The pipeline resolves the code through the 2-letter `country.id` (for example `XD` → `HIC`) and then removes these records as aggregates. If they were not resolved, they could have entered the data as unnamed "countries" or as duplicates of the key `("", year)`. 104 apparent duplicate keys in the raw data come from this quirk alone.
* After the codes are resolved, there are **no duplicate (iso3, year) keys** in either indicator, so 0 duplicate rows were dropped. A duplicate key with conflicting values would stop the pipeline with an error.
* 1,274 aggregate records per indicator were removed before any analysis. A unit test checks that no aggregate code reaches the panel.

## 3. Time coverage and choice of window

| | GDP per capita | Life expectancy |
|---|---|---|
| Latest year with data | 2025 (189 economies) | 2024 (all 217) |
| Values for 2025 | 185 non-missing (outside the window, not used) | 0 |

The requested 2000–2024 window can be used in full. 2025 is excluded because life expectancy is not yet published for it.

**Note on 2024 life expectancy (nature not verifiable from the API).** What could be verified is limited:

* The WDI April 2026 release note says the demographic indicators were "updated with 2024 data". It does not say whether these are estimates or projections, and it names no WPP edition.
* API footnotes and `obs_status` are empty for these values.
* WDI metadata states that annual WPP series are interpolated and "may not reflect real events as much as observed data".

A numeric pattern also distinguishes two kinds of values. For 52 economies the 2024 value is derived from male and female values, as in national-office or Eurostat data (non-terminating decimals, e.g. DEU 80.79268…). For 165 economies it is a 3-decimal WPP-style value. The 2023→2024 changes are very smooth: SD 0.35 years, against 2.82 for 2022→2023, and 91% of changes fall between 0 and 0.6. This suggests, but does not prove, that most 2024 values are model-based and close to projections.

For this reason the primary cross-section uses **2023**. Results for 2024 are almost identical (slope 5.26 vs 5.27).

## 4. Missing data

| Category | Economy-years | Share of 5,425 |
|---|---|---|
| Included (both indicators valid) | 4,916 | 90.6% |
| Missing GDP only | 509 | 9.4% |
| Missing life expectancy | 0 | 0% |
| Non-positive GDP | 0 | 0% |
| Invalid life expectancy (≤ 0 or > 120) | 0 | 0% |

* All missingness comes from GDP per capita (PPP). Life expectancy is complete for all 217 economies, 2000–2024.
* **18 economies have no GDP value in the whole window** and are excluded completely: American Samoa, British Virgin Islands, Channel Islands, Cuba, Eritrea, French Polynesia, Gibraltar, Guam, Isle of Man, North Korea, Liechtenstein, Monaco, New Caledonia, Northern Mariana Islands, South Sudan, St. Martin (French part), Venezuela, Yemen.
* Partially covered economies include Djibouti (12 of 25 years), Sint Maarten (16), Faroe Islands (17), Kosovo (17), Turks & Caicos (18) and Cayman Islands (19). See `figures/fig02_data_coverage.png`.
* Economies per year in the analysis sample: 192 (2000) → 199 (2013–2022) → 197 (2023) → 195 (2024).

**The data are not missing at random.** The excluded economies are mostly (a) small territories and microstates, often with high income, and (b) economies in conflict, under sanctions or closed (Yemen, South Sudan, Eritrea, Venezuela, North Korea, Cuba). Group (b) probably has lower life expectancy for its income than other economies, or very uncertain income data. Excluding it may make the fitted relationship look tighter than it is. Missing values were **not imputed**: imputing GDP for exactly these economies would require strong, untestable assumptions.

## 5. Plausibility checks

* GDP per capita in the window ranges from \$703 to \$174,570 (constant 2021 int'l $). There are no zero or negative values, so the log transform is defined for every analysed row. The code still guards against non-positive values (`safe_log`) and has tests for that guard.
* Life expectancy ranges from 14.7 to 85.7 years.

### Flagged (kept) observations

| Rule | Observations |
|---|---|
| Life expectancy < 40 years | CAF 2009 (14.7), CAF 2019 (31.5), CAF 2022 (18.8), SOM 2011 (32.5), SSD 2015–2017 (35.4–39.8) |
| Differs by > 5 years from both adjacent years | CAF 2009, 2014, 2017, 2018, 2019, 2020, 2021, 2022; HTI 2010 (earthquake); MMR 2008 (Cyclone Nargis); SOM 2011 (famine); SSD 2014, 2018 |

These are the values published in the current WDI release. The Central African Republic series is unusually volatile, moving between 14.7 and 57.7 years.

**Revision history (checked in the audit through the WDI Database Archives API, source 57; see `reports/final_scientific_audit_tr.md`).** In the WDI releases of July 2024, December 2024 and March 2025, the CAF series was **smooth**: 48.6 in 2009, 55.0 in 2019, 54.5 in 2022. The drops (14.7 / 31.5 / 18.8) first appear in the **April 2025** release and have been unchanged since. The March and April 2025 releases are stored in `data/raw/archive/`. The July and December 2024 releases were checked through direct API queries. That release revised life expectancy for 196 of the 212 economies compared (mean absolute change 0.60 years, 2000–2022). The WDI April 2025 release note does not mention life expectancy. The cause (most likely a new UN WPP edition) **could not be verified**. Whether the drops reflect real mortality or the UN's crisis-mortality modelling cannot be decided from WDI.

The values are therefore **kept**, and the panel models are re-estimated **without them** and **without CAF**. Note that the "transient shock" rule also flags CAF 2014–2021 values that lie *between* two drops (e.g. 2018 = 52.3). It is a crude volatility flag, not an identification of crisis years. South Sudan has no GDP data, so its flags do not affect any model. The 2023 primary cross-section contains no flagged observations.

## 6. Revisions

WDI is revised several times a year. New ICP PPP benchmarks re-base the whole GDP-PPP series, and each new edition of the UN World Population Prospects revises the full history of life expectancy. Re-running `download_data.py` later may therefore change every number in this project. The manifest stores the API `lastupdated` stamp (2026-10-08) and SHA-256 checksums so that a result can be traced to the exact data it was computed from.
