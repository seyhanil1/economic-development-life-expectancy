"""Shared pytest fixtures.

``fake_raw_dir`` writes a small synthetic copy of the raw API files. It
contains the awkward cases the real data has, plus some that cannot be
reproduced with the real data:
* an aggregate with a blank ISO3 code (the real API does this for income groups)
* a regional aggregate with a normal ISO3 code
* a missing (null) value
* a non-positive GDP value
* an exact duplicate record
* an invalid life-expectancy value
"""

import json
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))


def _rec(iso3, iso2, name, year, value, ind):
    return {
        "indicator": {"id": ind, "value": ind},
        "country": {"id": iso2, "value": name},
        "countryiso3code": iso3,
        "date": str(year),
        "value": value,
        "unit": "",
        "obs_status": "",
        "decimal": 0,
    }


COUNTRIES = [
    {"id": "AAA", "iso2Code": "AA", "name": "Alpha", "region": {"value": "Europe & Central Asia "}, "incomeLevel": {"value": "High income"}},
    {"id": "BBB", "iso2Code": "BB", "name": "Beta", "region": {"value": "Sub-Saharan Africa "}, "incomeLevel": {"value": "Low income"}},
    {"id": "CCC", "iso2Code": "CC", "name": "Gamma", "region": {"value": "South Asia"}, "incomeLevel": {"value": "Lower middle income"}},
    {"id": "WLD", "iso2Code": "1W", "name": "World", "region": {"value": "Aggregates"}, "incomeLevel": {"value": "Aggregates"}},
    {"id": "HIC", "iso2Code": "XD", "name": "High income", "region": {"value": "Aggregates"}, "incomeLevel": {"value": "Aggregates"}},
]


def make_raw(tmp: Path) -> Path:
    G, L = "NY.GDP.PCAP.PP.KD", "SP.DYN.LE00.IN"
    gdp = [
        _rec("AAA", "AA", "Alpha", 2000, 40000.0, G),
        _rec("AAA", "AA", "Alpha", 2001, 41000.0, G),
        _rec("AAA", "AA", "Alpha", 2001, 41000.0, G),  # exact duplicate
        _rec("BBB", "BB", "Beta", 2000, 1000.0, G),
        _rec("BBB", "BB", "Beta", 2001, None, G),  # missing
        _rec("CCC", "CC", "Gamma", 2000, 0.0, G),  # non-positive
        _rec("CCC", "CC", "Gamma", 2001, 3000.0, G),
        _rec("WLD", "1W", "World", 2000, 15000.0, G),
        _rec("", "XD", "High income", 2000, 45000.0, G),  # blank ISO3 aggregate
        _rec("AAA", "AA", "Alpha", 2025, 50000.0, G),  # outside the window
    ]
    le = [
        _rec("AAA", "AA", "Alpha", 2000, 80.0, L),
        _rec("AAA", "AA", "Alpha", 2001, 80.5, L),
        _rec("BBB", "BB", "Beta", 2000, 55.0, L),
        _rec("BBB", "BB", "Beta", 2001, 56.0, L),
        _rec("CCC", "CC", "Gamma", 2000, 65.0, L),
        _rec("CCC", "CC", "Gamma", 2001, 150.0, L),  # invalid life expectancy
        _rec("WLD", "1W", "World", 2000, 70.0, L),
        _rec("", "XD", "High income", 2000, 81.0, L),
    ]
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / f"{G}.json").write_text(json.dumps({"records": gdp}), encoding="utf-8")
    (tmp / f"{L}.json").write_text(json.dumps({"records": le}), encoding="utf-8")
    (tmp / "countries.json").write_text(json.dumps({"records": COUNTRIES}), encoding="utf-8")
    return tmp


@pytest.fixture
def fake_raw_dir(tmp_path):
    return make_raw(tmp_path / "raw")


def pytest_collection_modifyitems(config, items):
    """Skip tests marked ``network`` unless ``--run-network`` is given."""
    if config.getoption("--run-network"):
        return
    skip = pytest.mark.skip(reason="needs internet; run with --run-network")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip)


def pytest_addoption(parser):
    parser.addoption("--run-network", action="store_true", default=False, help="run live World Bank API tests")
