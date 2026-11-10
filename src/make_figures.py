"""Produce every figure in figures/ from the processed data and tables.

Every figure states the year(s), axis units and data source. Distributions of
GDP per capita are drawn on both a linear axis and a log axis, and the axis
is always labelled, so the scale is never hidden.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.formula.api as smf  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from scipy import stats  # noqa: E402
from statsmodels.nonparametric.smoothers_lowess import lowess  # noqa: E402

import statistical_analysis as sa  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = PROJECT_ROOT / "figures"
TABLE_DIR = PROJECT_ROOT / "reports" / "tables"

SOURCE = ("Source: World Bank, World Development Indicators (NY.GDP.PCAP.PP.KD, SP.DYN.LE00.IN), "
          "retrieved via API {date}. Unit of analysis: economy (equal weights).")
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"   # categorical slots 1-3
INK, INK2, GRID, PT = "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 150, "font.size": 9.5, "axes.titlesize": 11,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "axes.axisbelow": True, "lines.linewidth": 2, "legend.frameon": False,
})
usd = FuncFormatter(lambda v, _: f"${v/1000:,.0f}k" if v >= 1000 else f"${v:,.0f}")


def _source_note(fig, date):
    fig.text(0.01, 0.005, SOURCE.format(date=date), fontsize=7, color=INK2, ha="left", va="bottom")


def _save(fig, name, date):
    _source_note(fig, date)
    fig.savefig(FIG_DIR / name, bbox_inches="tight")
    plt.close(fig)


def main():
    FIG_DIR.mkdir(exist_ok=True)
    manifest = json.loads((PROJECT_ROOT / "data" / "raw" / "download_manifest.json").read_text(encoding="utf-8"))
    date = manifest["retrieved_at_utc"][:10]
    res = json.loads((TABLE_DIR / "results.json").read_text(encoding="utf-8"))
    panel = sa.load_panel()
    Y = res["primary_year"]
    cs = sa.prepare_cs(sa.cross_section(panel, Y))
    full = sa.analysis_rows(panel)

    # 1. Distributions ---------------------------------------------------
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    ax[0].hist(cs["gdp_pc_ppp"], bins=30, color=C1, edgecolor="white", linewidth=0.8)
    ax[0].xaxis.set_major_formatter(usd)
    ax[0].set(title=f"GDP per capita, PPP ({Y}) - linear axis",
              xlabel="GDP per capita (constant 2021 int'l $)", ylabel="Number of economies")
    bins = np.logspace(np.log10(cs["gdp_pc_ppp"].min()), np.log10(cs["gdp_pc_ppp"].max()), 30)
    ax[1].hist(cs["gdp_pc_ppp"], bins=bins, color=C1, edgecolor="white", linewidth=0.8)
    ax[1].set_xscale("log")
    ax[1].xaxis.set_major_formatter(usd)
    ax[1].set(title=f"GDP per capita, PPP ({Y}) - log axis",
              xlabel="GDP per capita (log scale, constant 2021 int'l $)", ylabel="Number of economies")
    ax[2].hist(cs["life_expectancy"], bins=25, color=C3, edgecolor="white", linewidth=0.8)
    ax[2].set(title=f"Life expectancy at birth ({Y})", xlabel="Years", ylabel="Number of economies")
    fig.suptitle(f"Distributions across {len(cs)} economies, {Y}", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    _save(fig, "fig01_distributions.png", date)

    # 2. Coverage -------------------------------------------------------------
    cov_y = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "coverage_by_year.csv")
    cov_c = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "coverage_by_country.csv")
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.2]})
    ax[0].plot(cov_y["year"], cov_y["with_le"], color=C3, label="Life expectancy available")
    ax[0].plot(cov_y["year"], cov_y["with_gdp"], color=C1, label="GDP per capita available")
    ax[0].plot(cov_y["year"], cov_y["usable"], color=C2, ls="--", label="Both (analysis sample)")
    ax[0].set(ylim=(0, 230), title="Economies with data, by year (of 217 economies)",
              xlabel="Year", ylabel="Number of economies")
    ax[0].legend(loc="lower right")
    inc = cov_c[cov_c["usable"] < 25].sort_values("usable", ascending=True)
    missing = 25 - inc["usable"]
    ax[1].barh(inc["name"], missing, color=C1, height=0.7)
    ax[1].set(title="Economies with missing years, 2000-2024 (missing GDP per capita)",
              xlabel="Years without a usable observation (of 25)", xlim=(0, 25))
    ax[1].tick_params(axis="y", labelsize=7)
    ax[1].grid(axis="y", visible=False)
    ax[1].invert_yaxis()
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    _save(fig, "fig02_data_coverage.png", date)

    # 3./4. Scatter: levels vs log ---------------------------------------------
    grid = np.linspace(cs["gdp_pc_ppp"].min(), cs["gdp_pc_ppp"].max(), 400)
    ma = smf.ols("life_expectancy ~ gdp_pc_ppp", data=cs).fit()
    mb = smf.ols("life_expectancy ~ log_gdp_pc", data=cs).fit(cov_type="HC3")
    lo = lowess(cs["life_expectancy"], cs["log_gdp_pc"], frac=0.5)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for a in ax:
        a.scatter(cs["gdp_pc_ppp"], cs["life_expectancy"], s=22, color=PT, alpha=0.75, edgecolor="white", linewidth=0.5)
    ax[0].plot(grid, ma.predict(pd.DataFrame({"gdp_pc_ppp": grid})), color=C2, label=f"Model A: linear in GDP (R² = {ma.rsquared:.2f})")
    ax[0].plot(grid, mb.predict(pd.DataFrame({"log_gdp_pc": np.log(grid)})), color=C1, label=f"Model B: linear in ln(GDP) (R² = {mb.rsquared:.2f})")
    ax[0].xaxis.set_major_formatter(usd)
    ax[0].set(title=f"Linear GDP axis ({Y})", xlabel="GDP per capita, PPP (constant 2021 int'l $)",
              ylabel="Life expectancy at birth (years)")
    ax[0].legend(loc="lower right")
    pred = mb.get_prediction(pd.DataFrame({"log_gdp_pc": np.log(grid)})).summary_frame(alpha=0.05)
    ax[1].fill_between(grid, pred["mean_ci_lower"], pred["mean_ci_upper"], color=C1, alpha=0.18, linewidth=0)
    ax[1].plot(grid, pred["mean"], color=C1, label="Model B fit with 95% CI (HC3)")
    ax[1].plot(np.exp(lo[:, 0]), lo[:, 1], color=C3, ls="--", label="LOWESS smoother (frac = 0.5)")
    ax[1].set_xscale("log")
    ax[1].xaxis.set_major_formatter(usd)
    infl = pd.DataFrame(res["influential_B"])
    for _, r in infl.iterrows():
        ax[1].annotate(r["name"], (r["gdp_pc_ppp"], r["life_expectancy"]), fontsize=7, color=INK2,
                       xytext=(4, -3), textcoords="offset points")
    ax[1].set(title=f"Log GDP axis ({Y}); labelled: influential points", xlabel="GDP per capita, PPP (log scale)")
    ax[1].legend(loc="lower right")
    fig.suptitle(f"Life expectancy vs GDP per capita across {len(cs)} economies, {Y}", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    _save(fig, "fig03_scatter_linear_vs_log.png", date)

    # 5. Selected years, identical axes ----------------------------------------
    yrs = sa.COMPARISON_YEARS
    fig, ax = plt.subplots(1, len(yrs), figsize=(13, 3.8), sharex=True, sharey=True)
    for a, yr in zip(ax, yrs):
        d = sa.prepare_cs(sa.cross_section(panel, yr))
        m = smf.ols("life_expectancy ~ log_gdp_pc", data=d).fit(cov_type="HC3")
        g = np.linspace(d["log_gdp_pc"].min(), d["log_gdp_pc"].max(), 100)
        a.scatter(d["gdp_pc_ppp"], d["life_expectancy"], s=12, color=PT, alpha=0.75, edgecolor="white", linewidth=0.4)
        a.plot(np.exp(g), m.params.iloc[0] + m.params.iloc[1] * g, color=C1)
        a.set_xscale("log")
        a.xaxis.set_major_formatter(usd)
        a.set_title(f"{yr}  (n = {len(d)})")
        a.text(0.03, 0.97, f"slope = {m.params.iloc[1]:.2f}\nr = {np.sqrt(m.rsquared):.2f}", transform=a.transAxes,
               va="top", fontsize=8, color=INK)
        a.set_xlabel("GDP per capita, PPP (log)")
    ax[0].set_ylabel("Life expectancy (years)")
    fig.suptitle("Cross-country relationship in selected years (same axes; slope = years per 1 unit of ln GDP)",
                 x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    _save(fig, "fig04_selected_years.png", date)

    # 6. Diagnostics ---------------------------------------------------------
    fits, d = sa.fit_models(sa.cross_section(panel, Y))
    fa, fb = fits["A_linear"].model.fit(), fits["B_log"].model.fit()
    infl_b = pd.read_csv(TABLE_DIR / f"influence_B_log_{Y}.csv")
    fig, ax = plt.subplots(2, 2, figsize=(11, 8))
    for a, f, name in ((ax[0, 0], fa, "Model A (linear GDP)"), (ax[0, 1], fb, "Model B (ln GDP)")):
        a.scatter(f.fittedvalues, f.resid, s=14, color=PT, alpha=0.8, edgecolor="white", linewidth=0.4)
        lw = lowess(f.resid, f.fittedvalues, frac=0.6)
        a.plot(lw[:, 0], lw[:, 1], color=C2, label="LOWESS of residuals")
        a.axhline(0, color=INK2, lw=1)
        a.set(title=f"Residuals vs fitted: {name}", xlabel="Fitted life expectancy (years)", ylabel="Residual (years)")
        a.legend(loc="lower left")
    (osm, osr), (slope, icpt, _) = stats.probplot(fb.get_influence().resid_studentized_internal)
    ax[1, 0].scatter(osm, osr, s=14, color=PT, edgecolor="white", linewidth=0.4)
    ax[1, 0].plot(osm, icpt + slope * osm, color=C1)
    ax[1, 0].set(title="Normal Q-Q plot: Model B standardised residuals",
                 xlabel="Theoretical normal quantiles", ylabel="Standardised residual")
    ax[1, 1].scatter(infl_b["leverage"], infl_b["cooks_d"], s=16, color=PT, edgecolor="white", linewidth=0.4)
    thr = res["diagnostics"]["B_log"]["thresholds"]["cooks_d"]
    ax[1, 1].axhline(thr, color=C2, ls="--", lw=1.5, label=f"Cook's D = 4/n = {thr:.3f}")
    names = d.set_index("iso3")["name"]
    for _, r in infl_b[infl_b["cooks_d"] > thr].iterrows():
        ax[1, 1].annotate(names[r["iso3"]], (r["leverage"], r["cooks_d"]), fontsize=7, color=INK2,
                          xytext=(4, 0), textcoords="offset points")
    ax[1, 1].set(title="Influence: Model B", xlabel="Leverage (hat value)", ylabel="Cook's distance")
    ax[1, 1].legend(loc="upper right")
    fig.suptitle(f"Regression diagnostics, cross-section {Y} (n = {len(d)})", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    _save(fig, "fig05_regression_diagnostics.png", date)

    # 7. Over time ---------------------------------------------------------------
    yl = pd.DataFrame(res["yearly"])
    yb = pd.DataFrame(res["yearly_balanced"])
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    ax[0].fill_between(yl["year"], yl["slope_B_ci_low"], yl["slope_B_ci_high"], color=C1, alpha=0.18, linewidth=0)
    ax[0].plot(yl["year"], yl["slope_B"], color=C1, marker="o", ms=4, label="All available economies (95% CI, HC3)")
    ax[0].plot(yb["year"], yb["slope_B"], color=C2, ls="--", label=f"Constant set of {res['balanced_n_countries']} economies")
    ax[0].set(title="Model B slope by year", xlabel="Year", ylabel="Years of life expectancy per 1 unit ln(GDP)",
              ylim=(0, 8))
    ax[0].legend(loc="lower left")
    ax[1].plot(yl["year"], yl["spearman"], color=C3, label="Spearman ρ (GDP)")
    ax[1].plot(yl["year"], yl["pearson_log"], color=C1, label="Pearson r (ln GDP)")
    ax[1].plot(yl["year"], yl["pearson_raw"], color=C2, label="Pearson r (GDP level)")
    ax[1].set(title="Correlation by year (all available economies)", xlabel="Year", ylabel="Correlation coefficient",
              ylim=(0, 1))
    ax[1].legend(loc="lower right")
    fig.suptitle("Annual cross-sections, 2000-2024 (each year estimated separately)", x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    _save(fig, "fig06_cross_sections_over_time.png", date)

    # 8. Between vs within ------------------------------------------------------
    pm = pd.DataFrame(res["panel_models"])
    pm = pm[pm["sample"] == "all 2000-2024"].copy()
    lds = res["long_differences"]
    labels = {
        "pooled_ols": "Pooled OLS",
        "pooled_ols_year_fe": "Pooled OLS + year effects",
        "between_country_means": "Between (country means)",
        "country_fe": "Country FE only (no year effects)",
        "twoway_fe": "Country FE + year FE (within)",
    }
    rows = [(labels[r.model], r.slope, r.ci_low, r.ci_high) for r in pm.itertuples()]
    rows += [(f"Long difference {ld['window']}", ld["slope"], ld["ci_low"], ld["ci_high"]) for ld in lds]
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.6), gridspec_kw={"width_ratios": [1.2, 1]})
    for i, (lab, b, l, h) in enumerate(rows):
        col = C1 if i < 3 else C2
        ax[0].plot([l, h], [i, i], color=col, lw=2)
        ax[0].plot(b, i, "o", color=col, ms=7, markeredgecolor="white")
    ax[0].set_yticks(range(len(rows)), [r[0] for r in rows])
    ax[0].invert_yaxis()
    ax[0].axvline(0, color=INK2, lw=1)
    ax[0].plot([], [], color=C1, marker="o", label="Uses between-country variation")
    ax[0].plot([], [], color=C2, marker="o", label="Uses within-country variation")
    ax[0].legend(loc="lower right", fontsize=8)
    ax[0].set(title="Slope on ln(GDP) by estimator, 95% CI", xlabel="Years of life expectancy per 1 unit ln(GDP)")
    ax[0].grid(axis="y", visible=False)
    ld = pd.read_csv(TABLE_DIR / "long_difference_2000-2019.csv")
    ax[1].scatter(ld["d_log_gdp"], ld["d_le"], s=16, color=PT, edgecolor="white", linewidth=0.4)
    m = smf.ols("d_le ~ d_log_gdp", data=ld).fit()
    g = np.linspace(ld["d_log_gdp"].min(), ld["d_log_gdp"].max(), 50)
    ax[1].plot(g, m.params.iloc[0] + m.params.iloc[1] * g, color=C2, label=f"OLS slope = {m.params.iloc[1]:.2f} (R² = {m.rsquared:.2f})")
    ax[1].axhline(0, color=INK2, lw=1)
    ax[1].axvline(0, color=INK2, lw=1)
    ax[1].set(title=f"Within-country change, 2000-2019 (n = {len(ld)})", xlabel="Change in ln(GDP per capita)",
              ylabel="Change in life expectancy (years)")
    ax[1].legend(loc="lower right")
    fig.suptitle("Between-country vs within-country association (SEs clustered by country for panel models)",
                 x=0.01, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    _save(fig, "fig07_between_vs_within.png", date)
    print("Figures written to figures/")


if __name__ == "__main__":
    main()
