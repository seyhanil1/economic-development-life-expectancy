"""Clean and merge the raw World Bank API files into an analysis panel.

Input : data/raw/*.json  (written by download_data.py, never modified)
Output: data/processed/
    entity_classification.csv  every API entity, economy vs aggregate
    country_year_panel.csv     every economy x year in the study window,
                               with flags and exclusion reasons
    analysis_sample.csv        rows usable for analysis (both indicators
                               present and valid)
    coverage_by_year.csv       usable observations per year
    coverage_by_country.csv    usable observations per economy
    cleaning_log.json          counts for every cleaning step

Rules (documented in reports/data_quality_report.md):
* Aggregates (World, regions, income groups, IDA/IBRD, ...) come from the
  World Bank country list (``region.value == "Aggregates"``) and are
  removed before any country-level analysis.
* Some aggregate records have an empty ``countryiso3code``. Codes are
  resolved through the 2-letter ``country.id`` so these records cannot
  slip through as unnamed "countries".
* Missing values stay missing (NaN). Nothing is filled with zero or
  imputed.
* The log of GDP is computed only for strictly positive values. A
  non-positive GDP is flagged and excluded, never logged.
* Life expectancy outside (0, 120] is logically invalid and excluded.
  Values that are extreme but possible, such as crisis years, are flagged
  and kept. Sensitivity analyses then drop them.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

GDP_CODE = "NY.GDP.PCAP.PP.KD"
LE_CODE = "SP.DYN.LE00.IN"
YEAR_MIN, YEAR_MAX = 2000, 2024

LE_VALID_RANGE = (0.0, 120.0)        # logical bounds (exclusive low, inclusive high)
LE_EXTREME_LOW = 40.0                # below this: flagged as extreme
LE_JUMP_THRESHOLD = 5.0              # |year-on-year change| above this: flagged


class DataIntegrityError(ValueError):
    """Raised when the raw data violates an assumption we rely on."""


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def _read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def records_to_frame(records: list[dict]) -> pd.DataFrame:
    """Flatten WB API indicator records into a tidy frame."""
    if not records:
        return pd.DataFrame(columns=["iso3", "iso2", "entity_name", "year", "value"])
    df = pd.DataFrame(
        {
            "iso3": [r.get("countryiso3code") or "" for r in records],
            "iso2": [(r.get("country") or {}).get("id", "") for r in records],
            "entity_name": [(r.get("country") or {}).get("value", "") for r in records],
            "year": [r.get("date") for r in records],
            "value": [r.get("value") for r in records],
        }
    )
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype("int64")
    # None becomes NaN. Missing values stay missing and are never set to 0.
    df["value"] = pd.to_numeric(df["value"], errors="coerce").astype("float64")
    return df


def classify_entities(country_records: list[dict]) -> pd.DataFrame:
    """Return one row per API entity with an ``is_aggregate`` flag."""
    rows = []
    for c in country_records:
        region = (c.get("region") or {}).get("value", "").strip()
        rows.append(
            {
                "iso3": c["id"],
                "iso2": c.get("iso2Code", ""),
                "name": c.get("name", ""),
                "region": region,
                "income_level": (c.get("incomeLevel") or {}).get("value", "").strip(),
                "is_aggregate": region == "Aggregates",
            }
        )
    ent = pd.DataFrame(rows)
    if ent["iso3"].duplicated().any():
        raise DataIntegrityError("Duplicate ISO3 codes in the country list")
    return ent


def resolve_iso3(df: pd.DataFrame, entities: pd.DataFrame) -> pd.DataFrame:
    """Fill empty ISO3 codes using the 2-letter API id. Raise if a code is
    still unresolved or is unknown to the country list."""
    out = df.copy()
    iso2_map = dict(zip(entities["iso2"], entities["iso3"]))
    blank = out["iso3"].eq("")
    out.loc[blank, "iso3"] = out.loc[blank, "iso2"].map(iso2_map)
    unknown = out["iso3"].isna() | ~out["iso3"].isin(entities["iso3"])
    if unknown.any():
        bad = out.loc[unknown, ["iso2", "entity_name"]].drop_duplicates().to_dict("records")
        raise DataIntegrityError(f"Unresolvable entity codes: {bad}")
    return out


def find_duplicates(df: pd.DataFrame, keys=("iso3", "year")) -> pd.DataFrame:
    """Rows whose (iso3, year) key appears more than once."""
    return df[df.duplicated(list(keys), keep=False)].sort_values(list(keys))


def deduplicate(df: pd.DataFrame, keys=("iso3", "year")) -> tuple[pd.DataFrame, int]:
    """Drop exact duplicates of the same key and value. Raise if one key
    has conflicting values, because we have no principled way to choose."""
    keys = list(keys)
    dups = find_duplicates(df, keys)
    if dups.empty:
        return df, 0
    conflicting = dups.groupby(keys)["value"].nunique(dropna=False) > 1
    if conflicting.any():
        raise DataIntegrityError(f"Conflicting duplicate values for keys: {list(conflicting[conflicting].index)[:10]}")
    out = df.drop_duplicates(keys, keep="first")
    return out, len(df) - len(out)


def safe_log(x: pd.Series) -> pd.Series:
    """Natural log of strictly positive values. Zero, negative and missing
    values become NaN instead of -inf or an error."""
    x = pd.to_numeric(x, errors="coerce").astype("float64")
    out = pd.Series(np.nan, index=x.index, dtype="float64")
    pos = x > 0
    out[pos] = np.log(x[pos])
    return out


def merge_indicators(gdp: pd.DataFrame, le: pd.DataFrame) -> pd.DataFrame:
    """Outer-merge the two indicators on (iso3, year). Keys must be unique."""
    for name, d in (("gdp", gdp), ("le", le)):
        if d.duplicated(["iso3", "year"]).any():
            raise DataIntegrityError(f"{name} has duplicate country-year keys")
    m = pd.merge(
        gdp[["iso3", "year", "value"]].rename(columns={"value": "gdp_pc_ppp"}),
        le[["iso3", "year", "value"]].rename(columns={"value": "life_expectancy"}),
        on=["iso3", "year"],
        how="outer",
        validate="one_to_one",
    )
    return m.sort_values(["iso3", "year"]).reset_index(drop=True)


def add_flags(panel: pd.DataFrame) -> pd.DataFrame:
    """Add validity flags, the exclusion reason and the ``in_analysis`` flag."""
    p = panel.copy()
    lo, hi = LE_VALID_RANGE
    p["missing_gdp"] = p["gdp_pc_ppp"].isna()
    p["missing_le"] = p["life_expectancy"].isna()
    p["nonpositive_gdp"] = p["gdp_pc_ppp"].le(0) & ~p["missing_gdp"]
    p["invalid_le"] = ~p["missing_le"] & ~(p["life_expectancy"].gt(lo) & p["life_expectancy"].le(hi))
    p["log_gdp_pc"] = safe_log(p["gdp_pc_ppp"])

    # Values that are possible but unusual. They are kept and flagged so
    # sensitivity analyses can drop them.
    p = p.sort_values(["iso3", "year"])
    prev = p.groupby("iso3")["life_expectancy"].shift(1)
    nxt = p.groupby("iso3")["life_expectancy"].shift(-1)
    jump = ((p["life_expectancy"] - prev).abs() > LE_JUMP_THRESHOLD) & ((p["life_expectancy"] - nxt).abs() > LE_JUMP_THRESHOLD)
    p["le_extreme_low"] = p["life_expectancy"].lt(LE_EXTREME_LOW)
    p["le_transient_shock"] = jump.fillna(False)

    reason = np.select(
        [
            p["missing_gdp"] & p["missing_le"],
            p["missing_gdp"],
            p["missing_le"],
            p["nonpositive_gdp"],
            p["invalid_le"],
        ],
        ["missing_both", "missing_gdp", "missing_le", "nonpositive_gdp", "invalid_le"],
        default="",
    )
    p["exclusion_reason"] = reason
    p["in_analysis"] = p["exclusion_reason"].eq("")
    return p.reset_index(drop=True)


def coverage_tables(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_year = (
        panel.groupby("year")
        .agg(
            economies=("iso3", "nunique"),
            with_gdp=("missing_gdp", lambda s: int((~s).sum())),
            with_le=("missing_le", lambda s: int((~s).sum())),
            usable=("in_analysis", "sum"),
        )
        .reset_index()
    )
    by_country = (
        panel.groupby(["iso3", "name"])
        .agg(
            years_in_window=("year", "nunique"),
            with_gdp=("missing_gdp", lambda s: int((~s).sum())),
            with_le=("missing_le", lambda s: int((~s).sum())),
            usable=("in_analysis", "sum"),
            first_usable=("year", lambda s: np.nan),
        )
        .reset_index()
    )
    usable = panel[panel["in_analysis"]].groupby("iso3")["year"]
    by_country["first_usable"] = by_country["iso3"].map(usable.min())
    by_country["last_usable"] = by_country["iso3"].map(usable.max())
    return by_year, by_country.sort_values(["usable", "iso3"])


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------
def build_panel(raw_dir: Path = RAW_DIR, year_min: int = YEAR_MIN, year_max: int = YEAR_MAX):
    """Return ``(entities, panel, log)``. ``panel`` holds only economies,
    with one row for every economy x year in the window."""
    log: dict = {"year_window": [year_min, year_max]}
    entities = classify_entities(_read_json(raw_dir / "countries.json")["records"])
    log["entities_total"] = int(len(entities))
    log["aggregates"] = int(entities["is_aggregate"].sum())
    log["economies"] = int((~entities["is_aggregate"]).sum())

    frames = {}
    for code, short in ((GDP_CODE, "gdp"), (LE_CODE, "le")):
        df = records_to_frame(_read_json(raw_dir / f"{code}.json")["records"])
        log[f"{short}_raw_records"] = int(len(df))
        log[f"{short}_blank_iso3_records"] = int(df["iso3"].eq("").sum())
        df = resolve_iso3(df, entities)
        df, n_dup = deduplicate(df)
        log[f"{short}_duplicate_rows_dropped"] = int(n_dup)
        is_agg = df["iso3"].isin(entities.loc[entities["is_aggregate"], "iso3"])
        log[f"{short}_aggregate_records_removed"] = int(is_agg.sum())
        df = df[~is_agg]
        out_window = ~df["year"].between(year_min, year_max)
        log[f"{short}_records_outside_window"] = int(out_window.sum())
        log[f"{short}_nonmissing_outside_window"] = int((out_window & df["value"].notna()).sum())
        frames[short] = df[~out_window]

    merged = merge_indicators(frames["gdp"], frames["le"])
    # Build the full economy x year grid so that economies missing from a
    # response are still counted as missing.
    econ = entities.loc[~entities["is_aggregate"], ["iso3", "name", "region", "income_level"]]
    grid = pd.MultiIndex.from_product([econ["iso3"], range(year_min, year_max + 1)], names=["iso3", "year"]).to_frame(index=False)
    panel = grid.merge(merged, on=["iso3", "year"], how="left", validate="one_to_one")
    panel = panel.merge(econ, on="iso3", how="left", validate="many_to_one")
    panel = add_flags(panel)
    cols = ["iso3", "name", "region", "income_level", "year", "gdp_pc_ppp", "log_gdp_pc", "life_expectancy",
            "missing_gdp", "missing_le", "nonpositive_gdp", "invalid_le", "le_extreme_low", "le_transient_shock",
            "exclusion_reason", "in_analysis"]
    panel = panel[cols]

    log["panel_rows"] = int(len(panel))
    log["exclusion_counts"] = {k: int(v) for k, v in panel["exclusion_reason"].replace("", "included").value_counts().items()}
    log["analysis_rows"] = int(panel["in_analysis"].sum())
    log["analysis_economies"] = int(panel.loc[panel["in_analysis"], "iso3"].nunique())
    log["economies_never_usable"] = sorted(
        panel.groupby("name")["in_analysis"].sum().loc[lambda s: s == 0].index.tolist()
    )
    log["flag_le_extreme_low"] = panel.loc[panel["le_extreme_low"], ["iso3", "year", "life_expectancy"]].to_dict("records")
    log["flag_le_transient_shock"] = panel.loc[panel["le_transient_shock"], ["iso3", "year", "life_expectancy"]].to_dict("records")
    return entities, panel, log


def main(raw_dir: Path = RAW_DIR, out_dir: Path = PROCESSED_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    entities, panel, log = build_panel(raw_dir)
    by_year, by_country = coverage_tables(panel)
    entities.to_csv(out_dir / "entity_classification.csv", index=False)
    panel.to_csv(out_dir / "country_year_panel.csv", index=False)
    panel[panel["in_analysis"]].drop(columns=["exclusion_reason", "in_analysis"]).to_csv(
        out_dir / "analysis_sample.csv", index=False
    )
    by_year.to_csv(out_dir / "coverage_by_year.csv", index=False)
    by_country.to_csv(out_dir / "coverage_by_country.csv", index=False)
    (out_dir / "cleaning_log.json").write_text(json.dumps(log, indent=1, default=float), encoding="utf-8")
    print(json.dumps({k: v for k, v in log.items() if not k.startswith("flag_")}, indent=1))
    return log


if __name__ == "__main__":
    main()
