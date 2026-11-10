"""Tests for statistical_analysis.py against hand-computed reference values."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import statistical_analysis as sa


# ---- correlations ------------------------------------------------------------
def test_pearson_known_example():
    # x = 1..5, y = (2,4,5,4,5): SST = 6, b = 0.6, SSR = 0.36*10 = 3.6, r^2 = 0.6
    r = sa.correlations([1, 2, 3, 4, 5], [2, 4, 5, 4, 5])
    assert r["pearson_r"] == pytest.approx(np.sqrt(0.6))
    assert r["n"] == 5


def test_spearman_known_example():
    # ranks y = (2,1,4,3,5): sum d^2 = 4, rho = 1 - 6*4/(5*24) = 0.8
    r = sa.correlations([1, 2, 3, 4, 5], [2, 1, 4, 3, 5])
    assert r["spearman_rho"] == pytest.approx(0.8)


def test_spearman_invariant_to_monotone_transform_pearson_not():
    x = np.arange(1, 21, dtype=float)
    y = x**3
    r = sa.correlations(x, y)
    assert r["spearman_rho"] == pytest.approx(1.0)
    assert r["pearson_r"] < 1.0
    assert sa.correlations(np.log(x), y)["spearman_rho"] == pytest.approx(1.0)


def test_correlation_ci_contains_estimate_and_drops_nan():
    rng = np.random.default_rng(1)
    x = rng.normal(size=60)
    y = 0.5 * x + rng.normal(size=60)
    x[3] = np.nan
    r = sa.correlations(x, y)
    assert r["n"] == 59
    lo, hi = r["pearson_ci"]
    assert lo < r["pearson_r"] < hi
    # Fisher CI reference computed independently
    z = np.arctanh(r["pearson_r"])
    se = 1 / np.sqrt(59 - 3)
    assert lo == pytest.approx(np.tanh(z - stats.norm.ppf(0.975) * se))


def test_correlations_requires_enough_pairs():
    with pytest.raises(ValueError):
        sa.correlations([1, 2, 3], [1, 2, 3])


# ---- regression -------------------------------------------------------------
def _toy_cs():
    gdp = np.array([1000, 2000, 4000, 8000, 16000, 32000, 64000], dtype=float)
    le = 20 + 5 * np.log(gdp) + np.array([0.3, -0.2, 0.1, -0.4, 0.2, 0.0, 0.1])
    return pd.DataFrame({"iso3": list("ABCDEFG"), "gdp_pc_ppp": gdp, "log_gdp_pc": np.log(gdp),
                         "life_expectancy": le})


def test_ols_matches_closed_form():
    d = _toy_cs()
    fits, used = sa.fit_models(d)
    x, y = used["log_gdp_pc"].values, used["life_expectancy"].values
    b1 = np.sum((x - x.mean()) * (y - y.mean())) / np.sum((x - x.mean()) ** 2)
    b0 = y.mean() - b1 * x.mean()
    assert fits["B_log"].params["log_gdp_pc"] == pytest.approx(b1)
    assert fits["B_log"].params["Intercept"] == pytest.approx(b0)
    # R^2 equals squared Pearson r for simple regression
    assert fits["B_log"].rsquared == pytest.approx(np.corrcoef(x, y)[0, 1] ** 2)
    # Model A slope is per $1,000
    xa = used["gdp_pc_ppp"].values / 1000
    b1a = np.sum((xa - xa.mean()) * (y - y.mean())) / np.sum((xa - xa.mean()) ** 2)
    assert fits["A_linear"].params["gdp_k"] == pytest.approx(b1a)


def test_models_use_same_sample():
    d = _toy_cs()
    d.loc[0, "gdp_pc_ppp"] = np.nan
    d.loc[1, "life_expectancy"] = np.nan
    fits, used = sa.fit_models(d)
    assert {int(f.nobs) for f in fits.values()} == {5}


def test_ols_recovers_known_slope_and_hc3_ci():
    rng = np.random.default_rng(42)
    gdp = np.exp(rng.uniform(7, 11.5, 400))
    le = 20 + 5.0 * np.log(gdp) + rng.normal(0, 3, 400)
    d = pd.DataFrame({"iso3": [f"C{i}" for i in range(400)], "gdp_pc_ppp": gdp, "log_gdp_pc": np.log(gdp),
                      "life_expectancy": le})
    fits, _ = sa.fit_models(d)
    s = sa.summarise_fit(fits["B_log"], "B")
    p = s["params"]["log_gdp_pc"]
    assert p["ci_low"] < 5.0 < p["ci_high"]
    assert s["cov_type"] == "HC3"


def test_log_model_interpretation():
    assert sa.marginal_effect_log_model(5.0, 10) == pytest.approx(5.0 * np.log(1.1))
    assert sa.marginal_effect_log_model(5.0, 100) == pytest.approx(5.0 * np.log(2))


def test_diagnostics_flag_planted_outlier():
    rng = np.random.default_rng(0)
    n = 100
    gdp = np.exp(rng.uniform(7, 11, n))
    le = 20 + 5 * np.log(gdp) + rng.normal(0, 1, n)
    le[0] -= 25  # planted outlier
    d = pd.DataFrame({"iso3": [f"C{i}" for i in range(n)], "gdp_pc_ppp": gdp, "log_gdp_pc": np.log(gdp),
                      "life_expectancy": le})
    fits, used = sa.fit_models(d)
    diag = sa.diagnostics(fits["B_log"], used)
    assert "C0" in set(diag["flagged"]["iso3"])
    assert diag["thresholds"]["cooks_d"] == pytest.approx(4 / n)


def test_twoway_fe_removes_common_trend():
    # Every country's GDP and LE rise together over time (a common trend),
    # but within a year, country-specific GDP deviations have no effect on
    # LE. Country FE alone picks up a spurious slope; two-way FE does not.
    rng = np.random.default_rng(3)
    rows = []
    for c in range(40):
        a = rng.normal(0, 1)
        for t in range(10):
            lg = 8 + a + 0.05 * t + rng.normal(0, 0.05)
            le = 60 + 4 * a + 0.4 * t + rng.normal(0, 0.3)
            rows.append({"iso3": f"C{c}", "year": 2000 + t, "log_gdp_pc": lg, "gdp_pc_ppp": np.exp(lg),
                         "life_expectancy": le, "in_analysis": True, "le_extreme_low": False,
                         "le_transient_shock": False})
    pm = sa.panel_models(pd.DataFrame(rows)).set_index("model")
    assert pm.loc["country_fe", "slope"] > 3
    assert pm.loc["twoway_fe", "ci_low"] < 0 < pm.loc["twoway_fe", "ci_high"]
    assert pm.loc["twoway_fe", "n_countries"] == 40


def test_describe_matches_pandas():
    d = _toy_cs()
    t = sa.describe(d, cols=("life_expectancy",)).loc["life_expectancy"]
    s = d["life_expectancy"]
    assert t["mean"] == pytest.approx(s.mean())
    assert t["sd"] == pytest.approx(s.std(ddof=1))
    assert t["median"] == pytest.approx(s.median())
    assert t["n"] == len(s)
