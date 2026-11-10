# Data Licence and Attribution

The MIT licence in `LICENSE` covers **the source code only**. The CC BY 4.0 licence in `LICENSE-DOCS.md` covers the project's **original written text**. Neither of them covers the World Bank data. The data are governed only by the World Bank terms below.

## Source data

| Files | Origin | Licence |
|---|---|---|
| `data/raw/*.json` | World Bank, *World Development Indicators*, API v2 (retrieved 2026-11-10; release 2026-10-08) | [CC BY 4.0](https://datacatalog.worldbank.org/public-licenses#cc-by) |
| `data/raw/archive/*.json.gz` | World Bank, *WDI Database Archives* (API source 57), releases 2025-03 and 2025-04. Unmodified API responses, gzip-compressed losslessly | CC BY 4.0 (same terms as WDI) |

The licence of both indicators (`NY.GDP.PCAP.PP.KD`, `SP.DYN.LE00.IN`) was read from the API metadata ("License_Type: CC BY-4.0"). It is stored in `data/raw/indicator_metadata.json`. The archive licence is **assumed** to match the WDI licence. It was not read separately from the archive API.

## Derived files

The following are **adaptations** of the World Bank data: `data/processed/*`, `reports/tables/*`, `reports/audit/*.csv|json`, `figures/*.png`, and the outputs stored in `notebooks/01_analysis.ipynb`. They remain subject to CC BY 4.0 attribution.

**What was changed:** aggregates were removed, the two indicators were merged by country-year, the natural log of GDP was added, quality flags were added, and statistics were computed. No values were imputed or edited. Full details are in `reports/data_quality_report.md`.

## Required attribution

> World Bank (2026). *World Development Indicators*: GDP per capita, PPP (constant 2021 international $) [NY.GDP.PCAP.PP.KD]; Life expectancy at birth, total (years) [SP.DYN.LE00.IN]. Retrieved 10 November 2026 from https://data.worldbank.org/. Licensed under CC BY 4.0. Modified by the author of this repository as described in `reports/data_quality_report.md`.

The underlying life-expectancy figures are compiled by the World Bank from the UN Population Division (*World Population Prospects*), national statistical offices and Eurostat. The PPP figures come from the International Comparison Program (ICP).

*This file is a good-faith summary, not legal advice. The authoritative terms are the World Bank's.*
