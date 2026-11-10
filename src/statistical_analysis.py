"""Statistical analysis of GDP per capita (PPP) and life expectancy.

Input : data/processed/country_year_panel.csv  (from clean_data.py)
Output: reports/tables/*.csv and reports/tables/results.json

Contents
--------
1. Descriptive statistics.
2. Pearson and Spearman correlations with 95% confidence intervals.
3. Cross-sectional OLS for the primary year, all fitted on the SAME sample:
     Model A: LE = b0 + b1 * GDP
     Model B: LE = b0 + b1 * ln(GDP)
     Model C: LE = b0 + b1 * ln(GDP) + b2 * ln(GDP)^2   (curvature check)
   Inference uses HC3 heteroskedasticity-robust standard errors. The
   classical standard errors are also reported for comparison.
4. Diagnostics: Breusch-Pagan, White, Jarque-Bera, Shapiro-Wilk, Ramsey
   RESET, leverage, studentised residuals, Cook's distance and DFBETAS,
   plus refits that drop influential observations and a robust (Huber)
   regression.
5. Over time:
   (a) a separate cross-section for each year 2000-2024, both on all
       available countries and on a constant (balanced) set of countries;
   (b) within-country change: country fixed effects with and without year
       effects, a between-country (country means) regression, and long
       differences. Panel inference clusters standard errors by country,
       because repeated observations of one country are not independent.

Every regression weights each economy equally. Results describe the
"typical country", not the typical person, and are not population-weighted.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan, het_white, linear_reset
from statsmodels.stats.outliers_influence import OLSInfluence
from statsmodels.stats.stattools import jarque_bera

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = PROJECT_ROOT / "data" / "processed" / "country_year_panel.csv"
TABLE_DIR = PROJECT_ROOT / "reports" / "tables"

PRIMARY_YEAR = 2023
COMPARISON_YEARS = (2000, 2010, 2019, 2023)
LONG_DIFF_WINDOWS = ((2000, 2019), (2000, 2023))
COVID_YEARS = (2020, 2021, 2022)


# --------------------------------------------------------------------------
# Data access
# --------------------------------------------------------------------------
def load_panel(path: Path = PANEL_PATH) -> pd.DataFrame:
    p = pd.read_csv(path, keep_default_na=True, na_values=[""])
    p["exclusion_reason"] = p["exclusion_reason"].fillna("")
    return p


def analysis_rows(panel: pd.DataFrame) -> pd.DataFrame:
    return panel[panel["in_analysis"].astype(bool)].copy()


def cross_section(panel: pd.DataFrame, year: int) -> pd.DataFrame:
    d = analysis_rows(panel)
    return d[d["year"] == year].reset_index(drop=True)


# --------------------------------------------------------------------------
# 1. Descriptive statistics
# --------------------------------------------------------------------------
def describe(df: pd.DataFrame, cols=("gdp_pc_ppp", "log_gdp_pc", "life_expectancy")) -> pd.DataFrame:
    rows = {}
    for c in cols:
        s = df[c].dropna()
        rows[c] = {
            "n": int(s.size),
            "mean": s.mean(),
            "sd": s.std(ddof=1),
            "min": s.min(),
            "q1": s.quantile(0.25),
            "median": s.median(),
            "q3": s.quantile(0.75),
            "max": s.max(),
            "skewness": stats.skew(s, bias=False),
            "excess_kurtosis": stats.kurtosis(s, bias=False),
        }
    return pd.DataFrame(rows).T


# --------------------------------------------------------------------------
# 2. Correlations
# --------------------------------------------------------------------------
def _fisher_ci(r: float, n: int, se: float, level: float = 0.95) -> tuple[float, float]:
    if abs(r) >= 1:  # perfect correlation: the Fisher transform is undefined
        return float(r), float(r)
    z = np.arctanh(r)
    q =stats.norm.ppf(0.5 + level / 2)
    return float(np.tanh(z - q * se)), float(np.tanh(z + q * se))


def correlations(x, y) -> dict:
    """Pearson r and Spearman rho with p-values and 95% CIs.

    Pearson CI: Fisher z with SE = 1/sqrt(n-3).
    Spearman CI: Fisher z with the Bonett-Wright (2000) SE
    sqrt((1 + rho^2/2)/(n-3)).
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = x.size
    if n < 4:
        raise ValueError("Need at least 4 complete pairs")
    pr = stats.pearsonr(x, y)
    sr = stats.spearmanr(x, y)
    r, rho = float(pr.statistic), float(sr.statistic)
    return {
        "n": int(n),
        "pearson_r": r,
        "pearson_p": float(pr.pvalue),
        "pearson_ci": _fisher_ci(r, n, 1 / np.sqrt(n - 3)),
        "spearman_rho": rho,
        "spearman_p": float(sr.pvalue),
        "spearman_ci": _fisher_ci(rho, n, np.sqrt((1 + rho**2 / 2) / (n - 3))),
    }


# --------------------------------------------------------------------------
# 3. Cross-sectional regression
# --------------------------------------------------------------------------
MODEL_FORMULAS = {
    "A_linear": "life_expectancy ~ gdp_k",
    "B_log": "life_expectancy ~ log_gdp_pc",
    "C_log_quadratic": "life_expectancy ~ log_gdp_c + I(log_gdp_c**2)",
}


def prepare_cs(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["gdp_pc_ppp", "log_gdp_pc", "life_expectancy"]).copy()
    d = d[d["gdp_pc_ppp"] > 0]
    d["gdp_k"] = d["gdp_pc_ppp"] / 1000.0          # thousands of 2021 int'l $
    d["log_gdp_c"] = d["log_gdp_pc"] - d["log_gdp_pc"].mean()  # centred for Model C
    return d.reset_index(drop=True)


def fit_models(df: pd.DataFrame, cov_type: str = "HC3") -> dict:
    """Fit Models A, B and C on one common sample. Returns the fitted results."""
    d = prepare_cs(df)
    return {name: smf.ols(f, data=d).fit(cov_type=cov_type) for name, f in MODEL_FORMULAS.items()}, d


def summarise_fit(res, name: str) -> dict:
    ci = res.conf_int()
    nonrobust = res.model.fit()  # same model with classical standard errors
    out = {
        "model": name,
        "n": int(res.nobs),
        "r2": res.rsquared,
        "adj_r2": res.rsquared_adj,
        "aic": res.aic,
        "bic": res.bic,
        "rmse": float(np.sqrt(res.mse_resid)),
        "cov_type": res.cov_type,
        "params": {},
    }
    for k in res.params.index:
        out["params"][k] = {
            "coef": res.params[k],
            "se_robust": res.bse[k],
            "ci_low": ci.loc[k, 0],
            "ci_high": ci.loc[k, 1],
            "p_robust": res.pvalues[k],
            "se_classical": nonrobust.bse[k],
            "p_classical": nonrobust.pvalues[k],
        }
    return out


def diagnostics(res, data: pd.DataFrame, label_col: str = "iso3") -> dict:
    """Residual and influence diagnostics for an OLS fit."""
    model = res.model
    resid = model.fit().resid
    exog = model.exog
    bp = het_breuschpagan(resid, exog)
    try:
        wh = het_white(resid, exog)
    except Exception:  # White needs extra columns; may fail on tiny samples
        wh = (np.nan, np.nan, np.nan, np.nan)
    jb, jb_p, skew, kurt = jarque_bera(resid)
    sw = stats.shapiro(resid)
    plain = model.fit()
    reset2 = linear_reset(plain, power=2, use_f=True)
    reset3 = linear_reset(plain, power=3, use_f=True)
    infl = OLSInfluence(plain)
    n, k = exog.shape
    cooks = infl.cooks_distance[0]
    lev = infl.hat_matrix_diag
    stud = infl.resid_studentized_external
    dfb = infl.dfbetas
    table = pd.DataFrame(
        {
            label_col: data[label_col].values,
            "cooks_d": cooks,
            "leverage": lev,
            "student_resid": stud,
            "max_abs_dfbeta": np.abs(dfb).max(axis=1),
        }
    )
    thr_cook = 4 / n
    flagged = table[(table["cooks_d"] > thr_cook) | (np.abs(table["student_resid"]) > 3)]
    return {
        "breusch_pagan": {"lm": bp[0], "p": bp[1]},
        "white": {"lm": wh[0], "p": wh[1]},
        "jarque_bera": {"stat": float(jb), "p": float(jb_p), "skew": float(skew), "kurtosis": float(kurt)},
        "shapiro_wilk": {"W": float(sw.statistic), "p": float(sw.pvalue)},
        "reset_power2": {"F": float(reset2.fvalue), "p": float(reset2.pvalue)},
        "reset_power3": {"F": float(reset3.fvalue), "p": float(reset3.pvalue)},
        "thresholds": {"cooks_d": thr_cook, "leverage": 2 * k / n, "student_resid": 3, "dfbetas": 2 / np.sqrt(n)},
        "influence_table": table,
        "flagged": flagged.sort_values("cooks_d", ascending=False),
    }


def influence_sensitivity(d: pd.DataFrame, flagged_ids, formula: str = MODEL_FORMULAS["B_log"]) -> dict:
    """Refit Model B (1) without flagged influential observations and (2)
    as a Huber robust regression on the full sample."""
    full = smf.ols(formula, data=d).fit(cov_type="HC3")
    trimmed_df = d[~d["iso3"].isin(flagged_ids)]
    trimmed = smf.ols(formula, data=trimmed_df).fit(cov_type="HC3")
    huber = smf.rlm(formula, data=d, M=sm.robust.norms.HuberT()).fit()
    key = "log_gdp_pc"
    return {
        "full": {"n": int(full.nobs), "slope": full.params[key], "ci": tuple(full.conf_int().loc[key]), "r2": full.rsquared},
        "without_influential": {
            "n": int(trimmed.nobs),
            "dropped": list(flagged_ids),
            "slope": trimmed.params[key],
            "ci": tuple(trimmed.conf_int().loc[key]),
            "r2": trimmed.rsquared,
        },
        "huber_rlm": {"n": int(huber.nobs), "slope": huber.params[key], "ci": tuple(huber.conf_int().loc[key])},
    }


def marginal_effect_log_model(b1: float, pct: float = 10.0) -> float:
    """Model B: change in LE for a pct% higher GDP per capita = b1*ln(1+pct/100)."""
    return b1 * np.log1p(pct / 100.0)


def quadratic_slope_at(res_c, log_gdp_mean: float, gdp_values) -> pd.DataFrame:
    """Model C: slope dLE/dln(GDP) = b1 + 2*b2*(ln GDP - mean), at chosen GDP levels."""
    b1 = res_c.params["log_gdp_c"]
    b2 = res_c.params["I(log_gdp_c ** 2)"]
    rows = []
    for g in gdp_values:
        c = np.log(g) - log_gdp_mean
        rows.append({"gdp_pc_ppp": g, "slope_per_log_unit": b1 + 2 * b2 * c,
                     "years_per_10pct": (b1 + 2 * b2 * c) * np.log(1.1)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 4. Over time
# --------------------------------------------------------------------------
def yearly_cross_sections(panel: pd.DataFrame, iso_subset=None) -> pd.DataFrame:
    d = analysis_rows(panel)
    if iso_subset is not None:
        d = d[d["iso3"].isin(iso_subset)]
    rows = []
    for yr, g in d.groupby("year"):
        g = prepare_cs(g)
        if len(g) < 10:
            continue
        cr = correlations(g["log_gdp_pc"], g["life_expectancy"])
        cr_raw = correlations(g["gdp_pc_ppp"], g["life_expectancy"])
        mb = smf.ols(MODEL_FORMULAS["B_log"], data=g).fit(cov_type="HC3")
        ma = smf.ols(MODEL_FORMULAS["A_linear"], data=g).fit(cov_type="HC3")
        ci = mb.conf_int().loc["log_gdp_pc"]
        rows.append(
            {
                "year": int(yr),
                "n": int(len(g)),
                "pearson_raw": cr_raw["pearson_r"],
                "pearson_log": cr["pearson_r"],
                "spearman": cr["spearman_rho"],
                "slope_B": mb.params["log_gdp_pc"],
                "slope_B_ci_low": ci[0],
                "slope_B_ci_high": ci[1],
                "r2_A": ma.rsquared,
                "r2_B": mb.rsquared,
                "mean_le": g["life_expectancy"].mean(),
                "median_gdp": g["gdp_pc_ppp"].median(),
            }
        )
    return pd.DataFrame(rows)


def balanced_countries(panel: pd.DataFrame, years) -> list[str]:
    d = analysis_rows(panel)
    d = d[d["year"].isin(years)]
    counts = d.groupby("iso3")["year"].nunique()
    return sorted(counts[counts == len(set(years))].index)


def _clustered(formula: str, d: pd.DataFrame):
    d = d.reset_index(drop=True)
    groups = pd.factorize(d["iso3"])[0]
    return smf.ols(formula, data=d).fit(cov_type="cluster", cov_kwds={"groups": groups})


def panel_models(panel: pd.DataFrame, exclude_years=(), exclude_flagged: bool = False) -> pd.DataFrame:
    """Pooled, between and fixed-effects estimates of the slope on ln(GDP).
    Standard errors are clustered by country (except the between model,
    which has one observation per country and uses HC3)."""
    d = analysis_rows(panel)
    if exclude_years:
        d = d[~d["year"].isin(exclude_years)]
    if exclude_flagged:
        d = d[~(d["le_extreme_low"].astype(bool) | d["le_transient_shock"].astype(bool))]
    d = d.reset_index(drop=True)
    out = []

    def rec(name, res, note, n_countries):
        ci = res.conf_int().loc["log_gdp_pc"]
        out.append({"model": name, "slope": res.params["log_gdp_pc"], "se": res.bse["log_gdp_pc"],
                    "ci_low": ci[0], "ci_high": ci[1], "p": res.pvalues["log_gdp_pc"],
                    "n_obs": int(res.nobs), "n_countries": int(n_countries), "inference": note})

    nc = d["iso3"].nunique()
    rec("pooled_ols", _clustered("life_expectancy ~ log_gdp_pc", d), "cluster(country)", nc)
    rec("pooled_ols_year_fe", _clustered("life_expectancy ~ log_gdp_pc + C(year)", d), "cluster(country)", nc)
    means = d.groupby("iso3")[["life_expectancy", "log_gdp_pc"]].mean().reset_index()
    rec("between_country_means", smf.ols("life_expectancy ~ log_gdp_pc", data=means).fit(cov_type="HC3"), "HC3", nc)
    rec("country_fe", _clustered("life_expectancy ~ log_gdp_pc + C(iso3)", d), "cluster(country)", nc)
    rec("twoway_fe", _clustered("life_expectancy ~ log_gdp_pc + C(iso3) + C(year)", d), "cluster(country)", nc)
    return pd.DataFrame(out)


def slope_trend_test(panel: pd.DataFrame, iso_subset=None) -> dict:
    """Does the cross-sectional slope on ln(GDP) change over time?

    Fits LE = a_t + (b + c*(year-2000)) * lnGDP + e on the pooled panel,
    with year intercepts and standard errors clustered by country. A test of
    c = 0 is valid even though the yearly samples overlap. Comparing the
    yearly confidence intervals is not, because the same countries appear
    in every year.
    """
    d = analysis_rows(panel)
    if iso_subset is not None:
        d = d[d["iso3"].isin(iso_subset)]
    d = d.assign(t=d["year"] - 2000)
    res = _clustered("life_expectancy ~ log_gdp_pc + log_gdp_pc:t + C(year)", d)
    k = "log_gdp_pc:t"
    ci = res.conf_int().loc[k]
    return {"slope_2000": res.params["log_gdp_pc"], "change_per_year": res.params[k], "ci_low": ci[0],
            "ci_high": ci[1], "p": res.pvalues[k], "n_obs": int(res.nobs), "n_countries": int(d["iso3"].nunique())}


def long_differences(panel: pd.DataFrame, start: int, end: int) -> dict:
    d = analysis_rows(panel)
    a = d[d["year"] == start].set_index("iso3")
    b = d[d["year"] == end].set_index("iso3")
    common = a.index.intersection(b.index)
    ld = pd.DataFrame(
        {
            "iso3": common,
            "d_le": (b.loc[common, "life_expectancy"] - a.loc[common, "life_expectancy"]).values,
            "d_log_gdp": (b.loc[common, "log_gdp_pc"] - a.loc[common, "log_gdp_pc"]).values,
            "le_start": a.loc[common, "life_expectancy"].values,
            "log_gdp_start": a.loc[common, "log_gdp_pc"].values,
        }
    )
    res = smf.ols("d_le ~ d_log_gdp", data=ld).fit(cov_type="HC3")
    # Convergence control: countries that started with low life expectancy
    # have more room to gain
    res2 = smf.ols("d_le ~ d_log_gdp + le_start", data=ld).fit(cov_type="HC3")
    cr = correlations(ld["d_log_gdp"], ld["d_le"])
    ci = res.conf_int().loc["d_log_gdp"]
    ci2 = res2.conf_int().loc["d_log_gdp"]
    return {
        "window": f"{start}-{end}",
        "n": int(len(ld)),
        "mean_d_le": ld["d_le"].mean(),
        "mean_d_log_gdp": ld["d_log_gdp"].mean(),
        "share_le_increased": float((ld["d_le"] > 0).mean()),
        "slope": res.params["d_log_gdp"], "ci_low": ci[0], "ci_high": ci[1], "p": res.pvalues["d_log_gdp"],
        "intercept": res.params["Intercept"], "r2": res.rsquared,
        "pearson_r": cr["pearson_r"], "spearman_rho": cr["spearman_rho"], "spearman_p": cr["spearman_p"],
        "slope_ctrl_le_start": res2.params["d_log_gdp"], "ci_ctrl_low": ci2[0], "ci_ctrl_high": ci2[1],
        "p_ctrl": res2.pvalues["d_log_gdp"], "coef_le_start": res2.params["le_start"],
        "data": ld,
    }


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, pd.DataFrame):
        return o.to_dict("records")
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def run_all(panel_path: Path = PANEL_PATH, out_dir: Path = TABLE_DIR, primary_year: int = PRIMARY_YEAR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    panel = load_panel(panel_path)
    results: dict = {"primary_year": primary_year}

    # Descriptives: primary year, comparison years, full pooled sample
    cs = cross_section(panel, primary_year)
    desc_rows = []
    for yr in COMPARISON_YEARS:
        dsc = describe(cross_section(panel, yr)).reset_index(names="variable")
        dsc.insert(0, "year", yr)
        desc_rows.append(dsc)
    pooled = describe(analysis_rows(panel)).reset_index(names="variable")
    pooled.insert(0, "year", "2000-2024 pooled")
    desc = pd.concat(desc_rows + [pooled], ignore_index=True)
    desc.to_csv(out_dir / "descriptive_statistics.csv", index=False)
    results["descriptives"] = desc

    # Correlations for the primary year
    results["correlations"] = {
        "gdp_level": correlations(cs["gdp_pc_ppp"], cs["life_expectancy"]),
        "log_gdp": correlations(cs["log_gdp_pc"], cs["life_expectancy"]),
    }

    # Models on one common sample
    fits, d = fit_models(cs)
    summaries = {k: summarise_fit(v, k) for k, v in fits.items()}
    results["models"] = summaries
    mt = pd.DataFrame([
        {"model": s["model"], "n": s["n"], "r2": s["r2"], "adj_r2": s["adj_r2"], "aic": s["aic"],
         "bic": s["bic"], "rmse": s["rmse"],
         **{f"{p}_coef": v["coef"] for p, v in s["params"].items()},
         **{f"{p}_ci_low": v["ci_low"] for p, v in s["params"].items()},
         **{f"{p}_ci_high": v["ci_high"] for p, v in s["params"].items()},
         **{f"{p}_se_hc3": v["se_robust"] for p, v in s["params"].items()},
         **{f"{p}_se_classical": v["se_classical"] for p, v in s["params"].items()},
         **{f"{p}_p_hc3": v["p_robust"] for p, v in s["params"].items()}}
        for s in summaries.values()
    ])
    mt.to_csv(out_dir / f"regression_models_{primary_year}.csv", index=False)

    b1 = fits["B_log"].params["log_gdp_pc"]
    results["interpretation_B"] = {
        "years_per_10pct_gdp": marginal_effect_log_model(b1, 10),
        "years_per_doubling_gdp": b1 * np.log(2),
    }
    qs = quadratic_slope_at(fits["C_log_quadratic"], d["log_gdp_pc"].mean(), [2000, 5000, 10000, 20000, 50000, 100000])
    qs.to_csv(out_dir / f"model_C_local_slopes_{primary_year}.csv", index=False)
    results["model_C_local_slopes"] = qs
    # Model A implied gain from +$1,000 at the same levels (constant by construction)
    results["model_A_years_per_1000usd"] = fits["A_linear"].params["gdp_k"]

    diag = {k: diagnostics(fits[k], d) for k in ("A_linear", "B_log")}
    for k, v in diag.items():
        v["influence_table"].to_csv(out_dir / f"influence_{k}_{primary_year}.csv", index=False)
    results["diagnostics"] = {k: {kk: vv for kk, vv in v.items() if kk != "influence_table"} for k, v in diag.items()}
    flagged = diag["B_log"]["flagged"]
    flagged = flagged.merge(d[["iso3", "name", "gdp_pc_ppp", "life_expectancy"]], on="iso3")
    flagged.to_csv(out_dir / f"influential_B_{primary_year}.csv", index=False)
    results["influential_B"] = flagged
    results["influence_sensitivity"] = influence_sensitivity(d, flagged["iso3"].tolist())

    # Over time: cross-sections
    yearly = yearly_cross_sections(panel)
    yearly.to_csv(out_dir / "yearly_cross_sections.csv", index=False)
    bal = balanced_countries(panel, range(2000, 2025))
    yearly_bal = yearly_cross_sections(panel, bal)
    yearly_bal.to_csv(out_dir / "yearly_cross_sections_balanced.csv", index=False)
    results["yearly"] = yearly
    results["yearly_balanced"] = yearly_bal
    results["balanced_n_countries"] = len(bal)
    results["slope_trend"] = {"all": slope_trend_test(panel), "balanced": slope_trend_test(panel, bal)}

    # Over time: within vs between
    pm = panel_models(panel)
    pm_nocovid = panel_models(panel, exclude_years=COVID_YEARS)
    pm_noflag = panel_models(panel, exclude_flagged=True)
    pm["sample"] = "all 2000-2024"
    pm_nocovid["sample"] = "excl. 2020-2022"
    pm_noflag["sample"] = "excl. flagged LE values"
    panel_tab = pd.concat([pm, pm_nocovid, pm_noflag], ignore_index=True)
    panel_tab.to_csv(out_dir / "panel_models.csv", index=False)
    results["panel_models"] = panel_tab

    lds = [long_differences(panel, a, b) for a, b in LONG_DIFF_WINDOWS]
    for ld in lds:
        ld["data"].to_csv(out_dir / f"long_difference_{ld['window']}.csv", index=False)
    results["long_differences"] = [{k: v for k, v in ld.items() if k != "data"} for ld in lds]

    # Sample-flag sensitivity for the primary-year cross-section
    flagged_obs = cs[cs["le_extreme_low"].astype(bool) | cs["le_transient_shock"].astype(bool)]
    results["primary_year_flagged_obs"] = flagged_obs[["iso3", "name", "life_expectancy"]]

    (out_dir / "results.json").write_text(json.dumps(_jsonable(results), indent=1, default=str), encoding="utf-8")
    return results


if __name__ == "__main__":
    r = run_all()
    print(json.dumps(_jsonable({k: r[k] for k in ("correlations", "interpretation_B", "influence_sensitivity", "long_differences")}), indent=1, default=str))
    print(r["panel_models"].to_string())
    print(pd.DataFrame([{k: v for k, v in s.items() if k != "params"} for s in r["models"].values()]).to_string())
    print(r["yearly"].round(3).to_string())
