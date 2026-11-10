"""Unit tests for clean_data.py (no network)."""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import clean_data as cd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _panel(fake_raw_dir):
    return cd.build_panel(fake_raw_dir, 2000, 2001)


# ---- records / missing values ----------------------------------------------
def test_records_to_frame_keeps_missing_as_nan_not_zero():
    recs = [{"countryiso3code": "AAA", "country": {"id": "AA", "value": "A"}, "date": "2000", "value": None}]
    df = cd.records_to_frame(recs)
    assert np.isnan(df.loc[0, "value"])
    assert df["year"].dtype == "int64"


def test_missing_values_are_never_filled(fake_raw_dir):
    _, panel, _ = _panel(fake_raw_dir)
    row = panel[(panel.iso3 == "BBB") & (panel.year == 2001)].iloc[0]
    assert np.isnan(row.gdp_pc_ppp)
    assert row.exclusion_reason == "missing_gdp"
    assert not row.in_analysis
    assert (panel["gdp_pc_ppp"] == 0).sum() == 1  # only the genuine 0 in the source


# ---- aggregates ----------------------------------------------------------
def test_classify_entities_marks_aggregates():
    from conftest import COUNTRIES

    ent = cd.classify_entities(COUNTRIES)
    assert set(ent.loc[ent.is_aggregate, "iso3"]) == {"WLD", "HIC"}


def test_blank_iso3_aggregate_is_resolved_and_excluded(fake_raw_dir):
    _, panel, log = _panel(fake_raw_dir)
    assert log["gdp_blank_iso3_records"] == 1
    assert set(panel["iso3"]) == {"AAA", "BBB", "CCC"}
    assert not panel["iso3"].isin(["WLD", "HIC", ""]).any()


def test_unknown_entity_code_raises():
    from conftest import COUNTRIES

    ent = cd.classify_entities(COUNTRIES)
    df = pd.DataFrame({"iso3": [""], "iso2": ["ZZ"], "entity_name": ["?"], "year": [2000], "value": [1.0]})
    with pytest.raises(cd.DataIntegrityError):
        cd.resolve_iso3(df, ent)


# ---- duplicates and merge keys -------------------------------------------
def test_exact_duplicate_dropped_and_counted(fake_raw_dir):
    _, panel, log = _panel(fake_raw_dir)
    assert log["gdp_duplicate_rows_dropped"] == 1
    assert not panel.duplicated(["iso3", "year"]).any()


def test_conflicting_duplicates_raise():
    df = pd.DataFrame({"iso3": ["AAA", "AAA"], "year": [2000, 2000], "value": [1.0, 2.0]})
    with pytest.raises(cd.DataIntegrityError):
        cd.deduplicate(df)


def test_merge_is_one_to_one_on_country_year():
    g = pd.DataFrame({"iso3": ["A", "A", "B"], "year": [2000, 2001, 2000], "value": [1.0, 2.0, 3.0]})
    l = pd.DataFrame({"iso3": ["A", "B", "C"], "year": [2000, 2000, 2000], "value": [70.0, 60.0, 50.0]})
    m = cd.merge_indicators(g, l)
    assert len(m) == 4  # outer join keeps every key
    assert m.set_index(["iso3", "year"]).loc[("B", 2000), "gdp_pc_ppp"] == 3.0
    assert m.set_index(["iso3", "year"]).loc[("B", 2000), "life_expectancy"] == 60.0
    assert np.isnan(m.set_index(["iso3", "year"]).loc[("C", 2000), "gdp_pc_ppp"])


def test_merge_rejects_duplicate_keys():
    g = pd.DataFrame({"iso3": ["A", "A"], "year": [2000, 2000], "value": [1.0, 2.0]})
    l = pd.DataFrame({"iso3": ["A"], "year": [2000], "value": [70.0]})
    with pytest.raises(cd.DataIntegrityError):
        cd.merge_indicators(g, l)


def test_panel_is_full_grid_and_window_respected(fake_raw_dir):
    _, panel, log = _panel(fake_raw_dir)
    assert len(panel) == 3 * 2  # 3 economies x 2 years
    assert panel["year"].between(2000, 2001).all()
    assert log["gdp_nonmissing_outside_window"] == 1


# ---- log transform and validity -------------------------------------------
def test_safe_log_handles_nonpositive_and_missing():
    out = cd.safe_log(pd.Series([np.e, 1.0, 0.0, -5.0, np.nan]))
    assert out.iloc[0] == pytest.approx(1.0)
    assert out.iloc[1] == 0.0
    assert out.iloc[2:].isna().all()
    assert not np.isinf(out).any()


def test_nonpositive_gdp_excluded_not_logged(fake_raw_dir):
    _, panel, _ = _panel(fake_raw_dir)
    row = panel[(panel.iso3 == "CCC") & (panel.year == 2000)].iloc[0]
    assert row.exclusion_reason == "nonpositive_gdp"
    assert np.isnan(row.log_gdp_pc)


def test_invalid_life_expectancy_excluded(fake_raw_dir):
    _, panel, _ = _panel(fake_raw_dir)
    row = panel[(panel.iso3 == "CCC") & (panel.year == 2001)].iloc[0]
    assert row.exclusion_reason == "invalid_le"


def test_analysis_rows_are_complete(fake_raw_dir):
    _, panel, log = _panel(fake_raw_dir)
    a = panel[panel.in_analysis]
    assert a[["gdp_pc_ppp", "log_gdp_pc", "life_expectancy"]].notna().all().all()
    assert (a["gdp_pc_ppp"] > 0).all()
    assert log["analysis_rows"] == 3  # AAA 2000, AAA 2001, BBB 2000


def test_transient_shock_flag():
    p = pd.DataFrame({"iso3": ["X"] * 5, "year": range(2000, 2005), "gdp_pc_ppp": [1000.0] * 5,
                      "life_expectancy": [60.0, 61.0, 30.0, 62.0, 63.0]})
    f = cd.add_flags(p)
    assert f["le_transient_shock"].tolist() == [False, False, True, False, False]
    assert f["le_extreme_low"].tolist() == [False, False, True, False, False]
    assert f["in_analysis"].all()  # flagged, not removed


# ---- reproducibility -----------------------------------------------------
def test_cleaning_is_deterministic(fake_raw_dir, tmp_path):
    hashes = []
    for i in range(2):
        out = tmp_path / f"out{i}"
        cd.main(fake_raw_dir, out)
        hashes.append({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*"))})
    assert hashes[0] == hashes[1]


# ---- checks against the real downloaded data (skipped if absent) --------------
REAL_RAW = PROJECT_ROOT / "data" / "raw"


@pytest.mark.skipif(not (REAL_RAW / "countries.json").exists(), reason="raw data not downloaded")
def test_real_data_contains_no_aggregates():
    ent, panel, _ = cd.build_panel(REAL_RAW)
    aggregates = set(ent.loc[ent.is_aggregate, "iso3"])
    assert len(aggregates) > 0
    assert not panel["iso3"].isin(aggregates).any()
    for code in ("WLD", "OED", "HIC", "LIC", "EUU", "SSF"):
        assert code in aggregates
        assert code not in set(panel["iso3"])
