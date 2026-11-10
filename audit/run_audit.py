"""Independent scientific audit of the analysis.

Run from the project root:
    python audit/run_audit.py            # uses data/raw/archive/*.json.gz (SHA-256 checked)
    python audit/run_audit.py --refetch  # re-download releases 202503/202504 and compare
                                         # them with the stored originals (no overwrite)

The audit only CHECKS the main pipeline. It does not change any result.
Outputs go to reports/audit/. The WDI archive releases it needs are stored as
deterministic gzip files in data/raw/archive/, listed with the SHA-256 of
the original download in ARCHIVE_MANIFEST.json (see audit/archive_io.py).

Sections
  A  data checks: Central African Republic series and WDI vintages,
     classification, economy lists, missing-data arithmetic
  B  statistical checks: common sample, HC3 by hand, test variants, FE
     design matrix, clustered SEs by hand, slope-trend p-value, long
     differences, 2024 data
  C  independent recomputation: numpy-only formulas and a small example
     that can be checked by hand
  D  sensitivity analyses
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan, het_white, linear_reset

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "audit"))
import archive_io  # noqa: E402
import clean_data as cd  # noqa: E402
import statistical_analysis as sa  # noqa: E402

OUT = ROOT / "reports" / "audit"
ARCH = ROOT / "data" / "raw" / "archive"
R: dict = {}  # every audit result, written to audit_results.json


def section(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


# --------------------------------------------------------------------------
# WDI archive (source 57) helper
# --------------------------------------------------------------------------
# Versions stored in the repository (data/raw/archive/*.json.gz) and needed for every result.
REQUIRED_VERSIONS = ("202503", "202504")
# Versions used only if a copy happens to be present in data/raw/archive/. 202412 is
# value-identical to 202503 for all economies (see ARCHIVE_MANIFEST.json), so no
# result depends on it.
OPTIONAL_VERSIONS = ("202412",)


def _download_archive_bytes(version: str, series: str) -> bytes:
    s = requests.Session()
    rows, page = [], 1
    while True:
        u = (f"https://api.worldbank.org/v2/sources/57/country/all/series/{series}/version/{version}"
             f"/time/all?format=json&per_page=10000&page={page}")
        j = s.get(u, timeout=180).json()
        rows.extend(j["source"]["data"])
        if int(j["page"]) >= int(j["pages"]):
            break
        page += 1
    if len(rows) != int(j["total"]):
        raise RuntimeError("archive record count mismatch")
    # same serialisation as the original download (no newlines, so platform-independent)
    return json.dumps({"version": version, "series": series, "records": rows}).encode("utf-8")


def fetch_archive(version: str, series: str, refetch: bool) -> pd.DataFrame:
    """Load an archived WDI release.

    By default the stored file is read through ``archive_io.read_archive_bytes``,
    which checks the SHA-256 of the decompressed bytes against
    ARCHIVE_MANIFEST.json. With ``refetch=True`` the release is downloaded
    again and compared with the stored original. The stored files are never
    overwritten. If no stored file exists, the download is compressed and
    recorded.
    """
    ARCH.mkdir(parents=True, exist_ok=True)
    if refetch or not archive_io.available(version, ARCH):
        raw = _download_archive_bytes(version, series)
        entry = (archive_io.load_manifest(ARCH / archive_io.MANIFEST.name)["versions"].get(version))
        if entry is None and not archive_io.available(version, ARCH):
            archive_io.store_bytes(version, raw, ARCH, retrieved=pd.Timestamp.now("UTC").strftime("%Y-%m-%d"))
            print(f"archive {version}: downloaded and stored")
        else:
            same = entry is not None and archive_io.sha256(raw) == entry["original_sha256"]
            R.setdefault("refetch_check", {})[version] = "identical to stored original" if same else \
                "DIFFERS from stored original (World Bank changed the archive or its serialisation)"
            print(f"archive {version}: re-downloaded; {R['refetch_check'][version]}")
    else:
        raw = archive_io.read_archive_bytes(version, ARCH)
    recs = json.loads(raw.decode("utf-8"))["records"]
    out = []
    for x in recs:
        d = {v["concept"]: v["id"] for v in x["variable"]}
        out.append({"iso3": d["Country"], "year": int(d["Time"][2:]), "value": x["value"]})
    df = pd.DataFrame(out)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


# --------------------------------------------------------------------------
def main(refetch: bool):
    OUT.mkdir(parents=True, exist_ok=True)
    panel = sa.load_panel()
    a = sa.analysis_rows(panel)
    ent = pd.read_csv(ROOT / "data" / "processed" / "entity_classification.csv")

    # =================================================================== A
    section("A1  Central African Republic: current release vs earlier WDI releases")
    caf_now = panel[panel.iso3 == "CAF"].set_index("year")["life_expectancy"]
    vint = {}
    for v in REQUIRED_VERSIONS:
        vint[v] = fetch_archive(v, "SP.DYN.LE00.IN", refetch)
    for v in OPTIONAL_VERSIONS:  # only if present locally; never downloaded by default
        if archive_io.available(v, ARCH):
            vint[v] = fetch_archive(v, "SP.DYN.LE00.IN", False)
    vint = dict(sorted(vint.items()))
    R["archive_versions_used"] = list(vint)
    R["archive_original_sha256"] = {v: e["original_sha256"] for v, e in
                                    archive_io.load_manifest(ARCH / archive_io.MANIFEST.name)["versions"].items()
                                    if v in vint}
    caf = pd.DataFrame({"current_2026-10-08": caf_now})
    for v, arc in vint.items():
        caf[f"archive_{v}"] = arc[arc.iso3 == "CAF"].set_index("year")["value"]
    caf = caf.loc[2005:2024]
    print(caf.round(2).to_string())
    caf.to_csv(OUT / "caf_life_expectancy_vintages.csv")
    R["caf_vintages"] = caf.round(3).reset_index().to_dict("records")

    # breadth of the 202503 -> 202504 revision, economies only
    econ = set(ent.loc[~ent.is_aggregate, "iso3"])
    m = vint["202503"].merge(vint["202504"], on=["iso3", "year"], suffixes=("_old", "_new"))
    m = m[m.iso3.isin(econ) & m.year.between(2000, 2022)].dropna()
    m["diff"] = m.value_new - m.value_old
    rev = {
        "pairs_compared": int(len(m)),
        "pairs_changed_gt_0.01": int((m["diff"].abs() > 0.01).sum()),
        "economies_compared": int(m.iso3.nunique()),
        "economies_changed": int(m.loc[m["diff"].abs() > 0.01, "iso3"].nunique()),
        "mean_abs_change": float(m["diff"].abs().mean()),
        "median_abs_change": float(m["diff"].abs().median()),
        "share_abs_change_gt_1yr": float((m["diff"].abs() > 1).mean()),
        "largest_changes": m.reindex(m["diff"].abs().sort_values(ascending=False).index).head(12)
        [["iso3", "year", "value_old", "value_new", "diff"]].round(2).to_dict("records"),
    }
    R["revision_202503_to_202504"] = rev
    print(json.dumps({k: v for k, v in rev.items() if k != "largest_changes"}, indent=1))
    # is the current release identical to 202504 for CAF? (to know whether the change persisted)
    R["caf_current_equals_202504"] = bool(np.allclose(caf["current_2026-10-08"].loc[2005:2022],
                                                      caf["archive_202504"].loc[2005:2022], atol=1e-6))

    section("A2  Effect of the LE vintage on results (2022 = latest year in the 202503 release)")
    old = vint["202503"].rename(columns={"value": "le_old"})
    p22 = a[a.year == 2022].merge(old, on=["iso3", "year"], how="left")
    p22 = p22.dropna(subset=["le_old"])
    rows = []
    for col, lab in (("life_expectancy", "current release"), ("le_old", "WDI 2025-03 release")):
        d = p22.assign(life_expectancy=p22[col])
        fits, used = sa.fit_models(d)
        cr = sa.correlations(used.log_gdp_pc, used.life_expectancy)
        b = fits["B_log"]
        rows.append({"LE vintage": lab, "n": int(b.nobs), "slope_B": b.params["log_gdp_pc"],
                     "ci_low": b.conf_int().loc["log_gdp_pc", 0], "ci_high": b.conf_int().loc["log_gdp_pc", 1],
                     "r2_B": b.rsquared, "r2_A": fits["A_linear"].rsquared,
                     "pearson_log": cr["pearson_r"], "spearman": cr["spearman_rho"]})
    vt = pd.DataFrame(rows)
    print(vt.round(3).to_string())
    R["vintage_2022_cross_section"] = vt.to_dict("records")
    # panel two-way FE 2000-2022 with old vs current LE
    pp = a[a.year <= 2022].merge(old, on=["iso3", "year"], how="left").dropna(subset=["le_old"])
    rows = []
    for col, lab in (("life_expectancy", "current release"), ("le_old", "WDI 2025-03 release")):
        d = pp.assign(life_expectancy=pp[col]).reset_index(drop=True)
        r_ = sa._clustered("life_expectancy ~ log_gdp_pc + C(iso3) + C(year)", d)
        rows.append({"LE vintage": lab, "n_obs": int(r_.nobs), "twoway_fe_slope": r_.params["log_gdp_pc"],
                     "ci_low": r_.conf_int().loc["log_gdp_pc", 0], "ci_high": r_.conf_int().loc["log_gdp_pc", 1]})
    vf = pd.DataFrame(rows)
    print(vf.round(3).to_string())
    R["vintage_twoway_fe_2000_2022"] = vf.to_dict("records")

    section("A3  Classification of aggregates and territories")
    agg = ent[ent.is_aggregate]
    R["n_entities"], R["n_aggregates"], R["n_economies"] = int(len(ent)), int(len(agg)), int((~ent.is_aggregate).sum())
    # Consistency: every aggregate has an empty income level or "Aggregates", every economy has a real one
    eco = ent[~ent.is_aggregate]
    R["aggregates_with_income_level_not_aggregates"] = agg.loc[agg.income_level != "Aggregates", "iso3"].tolist()
    R["economies_with_missing_income_level"] = eco.loc[eco.income_level.isin(["", "Aggregates"]) |
                                                       eco.income_level.isna(), ["iso3", "name", "income_level"]].to_dict("records")
    print("entities", R["n_entities"], "aggregates", R["n_aggregates"], "economies", R["n_economies"])
    print("aggregates whose incomeLevel != 'Aggregates':", R["aggregates_with_income_level_not_aggregates"])
    print("economies without income level:", R["economies_with_missing_income_level"])
    agg[["iso3", "name"]].to_csv(OUT / "aggregates_excluded.csv", index=False)
    # Territories / non-UN-member economies: hand-compiled list (World Bank "economies" are not all
    # sovereign states). The list is reviewed by hand. It is NOT read from the API.
    non_sovereign = {
        "ABW": "Aruba (NLD)", "ASM": "American Samoa (USA)", "BMU": "Bermuda (GBR)", "CHI": "Channel Islands (GBR)",
        "CUW": "Curacao (NLD)", "CYM": "Cayman Islands (GBR)", "FRO": "Faroe Islands (DNK)", "GIB": "Gibraltar (GBR)",
        "GRL": "Greenland (DNK)", "GUM": "Guam (USA)", "HKG": "Hong Kong SAR (CHN)", "IMN": "Isle of Man (GBR)",
        "MAC": "Macao SAR (CHN)", "MAF": "St. Martin (FRA)", "MNP": "Northern Mariana Islands (USA)",
        "NCL": "New Caledonia (FRA)", "PRI": "Puerto Rico (USA)", "PYF": "French Polynesia (FRA)",
        "SXM": "Sint Maarten (NLD)", "TCA": "Turks and Caicos Islands (GBR)", "VGB": "British Virgin Islands (GBR)",
        "VIR": "U.S. Virgin Islands (USA)", "XKX": "Kosovo (not a UN member)", "PSE": "West Bank and Gaza (UN observer)",
    }
    missing_codes = [c for c in non_sovereign if c not in set(eco.iso3)]
    R["non_sovereign_codes_not_in_wb_list"] = missing_codes
    ns_in = sorted(set(non_sovereign) & set(a.iso3))
    R["non_sovereign_in_analysis"] = ns_in
    R["non_sovereign_in_2023"] = sorted(set(non_sovereign) & set(a[a.year == 2023].iso3))
    print("non-sovereign economies in the analysis sample:", len(ns_in), ns_in)

    section("A4  Economy lists and missing-data arithmetic")
    lst199 = (a.groupby(["iso3", "name", "region", "income_level"]).year.agg(["count", "min", "max"])
              .reset_index().rename(columns={"count": "usable_years", "min": "first_year", "max": "last_year"}))
    lst199.to_csv(OUT / "economies_in_analysis_199.csv", index=False)
    lst197 = a[a.year == 2023][["iso3", "name", "region", "income_level", "gdp_pc_ppp", "life_expectancy"]]
    lst197.sort_values("iso3").to_csv(OUT / "economies_cross_section_2023_197.csv", index=False)
    in_199_not_197 = sorted(set(lst199.iso3) - set(lst197.iso3))
    R["n_analysis_economies"], R["n_2023"] = int(len(lst199)), int(len(lst197))
    R["in_analysis_but_not_2023"] = lst199[lst199.iso3.isin(in_199_not_197)][["iso3", "name", "last_year"]].to_dict("records")
    n_grid = len(panel)
    n_missing = int((panel.exclusion_reason == "missing_gdp").sum())
    R["missing_arithmetic"] = {
        "economies": int(panel.iso3.nunique()), "years": int(panel.year.nunique()), "grid_rows": int(n_grid),
        "grid_check": int(panel.iso3.nunique() * panel.year.nunique()),
        "missing_gdp": n_missing, "missing_share": n_missing / n_grid,
        "missing_from_18_never_usable": int(18 * 25),
        "missing_from_partially_covered": n_missing - 18 * 25,
        "included": int(panel.in_analysis.sum()),
        "share_of_199_economies_grid_missing": (n_missing - 450) / (199 * 25),
    }
    print(json.dumps(R["missing_arithmetic"], indent=1))
    print("in 199 but not in 2023:", R["in_analysis_but_not_2023"])

    # =================================================================== B
    section("B1  Same observations in Models A, B, C")
    cs = sa.cross_section(panel, 2023)
    fits, used = sa.fit_models(cs)
    idx = {k: tuple(v.model.data.row_labels) for k, v in fits.items()}
    R["same_sample"] = {"nobs": {k: int(v.nobs) for k, v in fits.items()},
                        "identical_row_sets": len(set(idx.values())) == 1}
    print(R["same_sample"])

    section("B2  HC3 by hand vs statsmodels")
    hc3 = {}
    for k in ("A_linear", "B_log"):
        f = fits[k]
        X, y = f.model.exog, f.model.endog
        XtXi = np.linalg.inv(X.T @ X)
        b = XtXi @ X.T @ y
        e = y - X @ b
        h = np.einsum("ij,jk,ik->i", X, XtXi, X)
        meat = X.T @ (X * (e**2 / (1 - h) ** 2)[:, None])
        V = XtXi @ meat @ XtXi
        se_hand = np.sqrt(np.diag(V))
        hc3[k] = {"se_statsmodels": f.bse.values.tolist(), "se_by_hand": se_hand.tolist(),
                  "max_abs_diff": float(np.max(np.abs(se_hand - f.bse.values))),
                  "use_t": bool(f.use_t), "max_leverage": float(h.max())}
    R["hc3_check"] = hc3
    print(json.dumps(hc3, indent=1))

    section("B3  Heteroskedasticity and RESET test variants")
    tv = {}
    for k in ("A_linear", "B_log"):
        f = fits[k].model.fit()
        bp_koenker = het_breuschpagan(f.resid, f.model.exog, robust=True)
        bp_classic = het_breuschpagan(f.resid, f.model.exog, robust=False)
        wh = het_white(f.resid, f.model.exog)
        rs_f = linear_reset(f, power=2, use_f=True)
        rs_hc3 = linear_reset(f, power=2, use_f=False, cov_type="HC3")
        tv[k] = {"bp_koenker_p": bp_koenker[1], "bp_classic_p": bp_classic[1], "white_p": wh[1],
                 "white_df": int(wh[0] / stats.chi2.isf(wh[1], 1)) if False else "x, x^2 (2 df)",
                 "reset2_F_p": float(rs_f.pvalue), "reset2_HC3_wald_p": float(rs_hc3.pvalue)}
    R["test_variants"] = tv
    print(json.dumps(tv, indent=1, default=float))

    section("B4  Fixed-effects design matrix")
    d = a.reset_index(drop=True)
    fe = sa._clustered("life_expectancy ~ log_gdp_pc + C(iso3) + C(year)", d)
    X = fe.model.exog
    names = fe.model.exog_names
    ref_iso = sorted(d.iso3.unique())[0]
    ref_year = int(sorted(d.year.unique())[0])
    R["fe_design"] = {
        "n_obs": int(X.shape[0]), "n_columns": int(X.shape[1]), "rank": int(np.linalg.matrix_rank(X)),
        "expected_columns": 1 + 1 + (d.iso3.nunique() - 1) + (d.year.nunique() - 1),
        "country_dummies": int(sum(n.startswith("C(iso3)") for n in names)),
        "year_dummies": int(sum(n.startswith("C(year)") for n in names)),
        "reference_country": ref_iso, "reference_country_in_names": any(f"[T.{ref_iso}]" in n for n in names),
        "reference_year": ref_year, "reference_year_in_names": any(f"[T.{ref_year}]" in n for n in names),
    }
    print(R["fe_design"])

    # FWL: alternating projections (two-way demeaning of an unbalanced panel)
    def demean2(s, g1, g2, tol=1e-12, it=10000):
        v = s.astype(float).copy()
        for _ in range(it):
            old = v.copy()
            v = v - v.groupby(g1).transform("mean")
            v = v - v.groupby(g2).transform("mean")
            if np.max(np.abs(v - old)) < tol:
                break
        return v

    yt = demean2(d.life_expectancy, d.iso3, d.year)
    xt = demean2(d.log_gdp_pc, d.iso3, d.year)
    b_fwl = float((xt * yt).sum() / (xt**2).sum())
    u = yt - b_fwl * xt
    # cluster-robust sandwich, by hand
    G, N = d.iso3.nunique(), len(d)
    scores = (xt * u).groupby(d.iso3).sum()
    meat = float((scores**2).sum())
    bread = float((xt**2).sum())
    v0 = meat / bread**2
    K_full = X.shape[1]
    se_sm_formula = np.sqrt(v0 * G / (G - 1) * (N - 1) / (N - K_full))
    se_stata_like = np.sqrt(v0 * G / (G - 1) * (N - 1) / (N - 1 - (d.year.nunique() - 1) - 1))  # FE nested in clusters
    se_g_only = np.sqrt(v0 * G / (G - 1))
    ci_t = (b_fwl - stats.t.ppf(0.975, G - 1) * se_sm_formula, b_fwl + stats.t.ppf(0.975, G - 1) * se_sm_formula)
    R["fe_cluster_check"] = {
        "slope_statsmodels": float(fe.params["log_gdp_pc"]), "slope_fwl_by_hand": b_fwl,
        "se_statsmodels": float(fe.bse["log_gdp_pc"]), "se_by_hand_same_correction": float(se_sm_formula),
        "se_by_hand_G_correction_only": float(se_g_only), "se_stata_xtreg_like": float(se_stata_like),
        "statsmodels_use_t": bool(fe.use_t), "statsmodels_ci": fe.conf_int().loc["log_gdp_pc"].tolist(),
        "ci_with_t_G_minus_1": list(ci_t), "n_clusters": int(G),
    }
    print(json.dumps(R["fe_cluster_check"], indent=1))

    section("B5  Slope-trend p-value, step by step")
    st = sa.slope_trend_test(panel)
    dd = a.assign(t=a.year - 2000).reset_index(drop=True)
    res = sa._clustered("life_expectancy ~ log_gdp_pc + log_gdp_pc:t + C(year)", dd)
    k = "log_gdp_pc:t"
    z = res.params[k] / res.bse[k]
    R["slope_trend_steps"] = {"coef": float(res.params[k]), "se_cluster": float(res.bse[k]), "z": float(z),
                              "p_normal_2sided": float(2 * stats.norm.sf(abs(z))),
                              "p_t_G_minus_1": float(2 * stats.t.sf(abs(z), dd.iso3.nunique() - 1)),
                              "p_reported": float(st["p"]), "implied_change_2000_2024": float(res.params[k] * 24)}
    print(json.dumps(R["slope_trend_steps"], indent=1))

    section("B6  Long differences: periods and observation counts")
    ld = {}
    for s0, s1 in sa.LONG_DIFF_WINDOWS:
        has0 = set(a[a.year == s0].iso3)
        has1 = set(a[a.year == s1].iso3)
        both = has0 & has1
        ld[f"{s0}-{s1}"] = {
            "n": len(both),
            "in_199_but_missing_start": sorted(set(a.iso3) - has0),
            "in_199_but_missing_end": sorted(set(a.iso3) - has1),
        }
    R["long_diff_counts"] = ld
    print(json.dumps(ld, indent=1))

    section("B7  2024 life-expectancy values")
    p = panel.pivot(index="iso3", columns="year", values="life_expectancy")
    ch24 = (p[2024] - p[2023]).dropna()
    ch23 = (p[2023] - p[2022]).dropna()
    R["le_2024"] = {
        "n_with_2024": int(p[2024].notna().sum()),
        "median_change_2023_2024": float(ch24.median()), "sd_change_2023_2024": float(ch24.std()),
        "median_change_2022_2023": float(ch23.median()), "sd_change_2022_2023": float(ch23.std()),
        "share_2024_change_between_0_and_0.6": float(ch24.between(0, 0.6).mean()),
        "note": "API footnotes for 2022-2024 (CAF, DEU, NGA, TUR) are empty; obs_status empty for all records; "
                "WDI metadata: annual WPP series are interpolated; the UN data-portal API returned HTTP 401 (token required)",
    }
    print(json.dumps(R["le_2024"], indent=1))

    # =================================================================== C
    section("C1  Independent recomputation with numpy only (2023)")
    x, y, g = used.log_gdp_pc.values, used.life_expectancy.values, used.gdp_pc_ppp.values

    def pearson(u, v):
        u, v = u - u.mean(), v - v.mean()
        return float((u * v).sum() / np.sqrt((u**2).sum() * (v**2).sum()))

    def avg_rank(v):
        return pd.Series(v).rank(method="average").values

    def ols(xv, yv):
        Xm = np.column_stack([np.ones_like(xv), xv])
        coef, *_ = np.linalg.lstsq(Xm, yv, rcond=None)
        return coef

    rep = json.loads((ROOT / "reports" / "tables" / "results.json").read_text(encoding="utf-8"))
    ind = {
        "pearson_gdp": (pearson(g, y), rep["correlations"]["gdp_level"]["pearson_r"]),
        "pearson_log": (pearson(x, y), rep["correlations"]["log_gdp"]["pearson_r"]),
        "spearman": (pearson(avg_rank(g), avg_rank(y)), rep["correlations"]["log_gdp"]["spearman_rho"]),
        "slope_A_per_1000": (float(ols(g / 1000, y)[1]), rep["models"]["A_linear"]["params"]["gdp_k"]["coef"]),
        "slope_B": (float(ols(x, y)[1]), rep["models"]["B_log"]["params"]["log_gdp_pc"]["coef"]),
        "intercept_B": (float(ols(x, y)[0]), rep["models"]["B_log"]["params"]["Intercept"]["coef"]),
        "r2_B_as_r_squared": (pearson(x, y) ** 2, rep["models"]["B_log"]["r2"]),
        "twoway_fe_fwl": (b_fwl, float(fe.params["log_gdp_pc"])),
    }
    R["independent"] = {k: {"independent": v[0], "reported": v[1], "abs_diff": abs(v[0] - v[1])} for k, v in ind.items()}
    print(pd.DataFrame(R["independent"]).T.to_string())

    section("C2  Small example that can be checked by hand (5 economies, 2023)")
    ex = used[used.iso3.isin(["BDI", "NGA", "IND", "TUR", "DEU"])][["iso3", "name", "gdp_pc_ppp", "life_expectancy"]].copy()
    ex["x=ln(gdp)"] = np.log(ex.gdp_pc_ppp)
    ex = ex.sort_values("gdp_pc_ppp").reset_index(drop=True)
    xm, ym = ex["x=ln(gdp)"].mean(), ex.life_expectancy.mean()
    ex["x-xbar"] = ex["x=ln(gdp)"] - xm
    ex["y-ybar"] = ex.life_expectancy - ym
    ex["(x-xbar)(y-ybar)"] = ex["x-xbar"] * ex["y-ybar"]
    ex["(x-xbar)^2"] = ex["x-xbar"] ** 2
    ex["(y-ybar)^2"] = ex["y-ybar"] ** 2
    Sxy, Sxx, Syy = ex["(x-xbar)(y-ybar)"].sum(), ex["(x-xbar)^2"].sum(), ex["(y-ybar)^2"].sum()
    hand = {"xbar": xm, "ybar": ym, "Sxy": Sxy, "Sxx": Sxx, "Syy": Syy, "b1=Sxy/Sxx": Sxy / Sxx,
            "b0=ybar-b1*xbar": ym - Sxy / Sxx * xm, "r=Sxy/sqrt(SxxSyy)": Sxy / np.sqrt(Sxx * Syy),
            "scipy_pearson": float(stats.pearsonr(ex["x=ln(gdp)"], ex.life_expectancy).statistic),
            "statsmodels_slope": float(smf.ols("life_expectancy ~ np.log(gdp_pc_ppp)", ex).fit().params.iloc[1]),
            "ranks_x": avg_rank(ex.gdp_pc_ppp).tolist(), "ranks_y": avg_rank(ex.life_expectancy.values).tolist(),
            "spearman_scipy": float(stats.spearmanr(ex.gdp_pc_ppp, ex.life_expectancy).statistic)}
    dsq = ((np.array(hand["ranks_x"]) - np.array(hand["ranks_y"])) ** 2).sum()
    hand["sum_d2"] = float(dsq)
    hand["spearman_formula_1-6sum_d2/(n(n^2-1))"] = float(1 - 6 * dsq / (5 * 24))
    ex.round(4).to_csv(OUT / "hand_example_2023.csv", index=False)
    R["hand_example"] = {"table": ex.round(4).to_dict("records"), **{k: v for k, v in hand.items()}}
    print(ex.round(3).to_string())
    print(json.dumps({k: v for k, v in hand.items()}, indent=1, default=float))

    section("C3  Transformations")
    b_ln = float(ols(x, y)[1])
    b_log10 = float(ols(np.log10(g), y)[1])
    R["transform"] = {"slope_ln": b_ln, "slope_log10": b_log10, "ratio_log10/ln": b_log10 / b_ln, "ln10": float(np.log(10)),
                      "r2_ln": pearson(x, y) ** 2, "r2_log10": pearson(np.log10(g), y) ** 2,
                      "slope_per_1000_lin": float(ols(g / 1000, y)[1]),
                      "loglog_elasticity": float(ols(x, np.log(y))[1])}
    print(json.dumps(R["transform"], indent=1))

    # =================================================================== D
    section("D  Sensitivity analyses")
    sens = []

    def add(label, d23=None, pnl=None):
        row = {"analysis": label}
        if d23 is not None:
            f_, u_ = sa.fit_models(d23)
            b = f_["B_log"]
            row.update({"n_2023": int(b.nobs), "slope_B_2023": b.params["log_gdp_pc"],
                        "ci_low": b.conf_int().loc["log_gdp_pc", 0], "ci_high": b.conf_int().loc["log_gdp_pc", 1],
                        "r2_B": b.rsquared, "r2_A": f_["A_linear"].rsquared,
                        "spearman": sa.correlations(u_.gdp_pc_ppp, u_.life_expectancy)["spearman_rho"]})
        if pnl is not None:
            pm = sa.panel_models(pnl).set_index("model")
            row.update({"between": pm.loc["between_country_means", "slope"], "twoway_fe": pm.loc["twoway_fe", "slope"],
                        "twoway_fe_ci_low": pm.loc["twoway_fe", "ci_low"], "twoway_fe_ci_high": pm.loc["twoway_fe", "ci_high"],
                        "panel_obs": int(pm.loc["twoway_fe", "n_obs"]), "panel_countries": int(pm.loc["twoway_fe", "n_countries"])})
            st_ = sa.slope_trend_test(pnl)
            row.update({"slope_trend_per_year": st_["change_per_year"], "slope_trend_p": st_["p"]})
        sens.append(row)

    add("Baseline", cs, panel)
    add("Without CAF (all years)", cs[cs.iso3 != "CAF"], panel[panel.iso3 != "CAF"])
    flagged = panel.le_extreme_low | panel.le_transient_shock
    add("Without flagged LE values", cs, panel[~flagged])
    add("Without 24 non-sovereign economies", cs[~cs.iso3.isin(list(non_sovereign))],
        panel[~panel.iso3.isin(list(non_sovereign))])
    infl = pd.read_csv(ROOT / "reports" / "tables" / "influential_B_2023.csv")
    add("2023 without 9 influential economies", cs[~cs.iso3.isin(infl.iso3)])
    bal = sa.balanced_countries(panel, range(2000, 2025))
    add(f"Balanced panel ({len(bal)} economies)", cs[cs.iso3.isin(bal)], panel[panel.iso3.isin(bal)])
    add("Excluding 2020-2022", None, panel[~panel.year.isin([2020, 2021, 2022])])
    add("2024 instead of 2023 cross-section", sa.cross_section(panel, 2024))
    # oil/resource-heavy and very high GDP microstates, high leverage at the top
    top = cs.nlargest(10, "gdp_pc_ppp").iso3.tolist()
    add("2023 without the 10 richest economies", cs[~cs.iso3.isin(top)])
    st_tab = pd.DataFrame(sens)
    st_tab.to_csv(OUT / "sensitivity_summary.csv", index=False)
    R["sensitivity"] = st_tab.to_dict("records")
    R["richest_10_2023"] = top
    print(st_tab.round(3).to_string())

    # yearly slope with vs without CAF for the dip years
    y_all = sa.yearly_cross_sections(panel).set_index("year")
    y_nocaf = sa.yearly_cross_sections(panel[panel.iso3 != "CAF"]).set_index("year")
    dip = pd.DataFrame({"slope_all": y_all.slope_B, "slope_without_CAF": y_nocaf.slope_B,
                        "ci_width_all": y_all.slope_B_ci_high - y_all.slope_B_ci_low,
                        "ci_width_without_CAF": y_nocaf.slope_B_ci_high - y_nocaf.slope_B_ci_low,
                        "pearson_log_all": y_all.pearson_log, "pearson_log_without_CAF": y_nocaf.pearson_log})
    dip.to_csv(OUT / "yearly_with_without_caf.csv")
    R["yearly_with_without_caf"] = dip.round(4).reset_index().to_dict("records")
    print(dip.loc[[2008, 2009, 2010, 2018, 2019, 2020, 2021, 2022, 2023]].round(3).to_string())

    # long differences without CAF
    ldn = []
    for s0, s1 in sa.LONG_DIFF_WINDOWS:
        for lab, pnl in (("all", panel), ("without CAF", panel[panel.iso3 != "CAF"])):
            r_ = sa.long_differences(pnl, s0, s1)
            ldn.append({"window": f"{s0}-{s1}", "sample": lab, "n": r_["n"], "slope": r_["slope"],
                        "ci_low": r_["ci_low"], "ci_high": r_["ci_high"], "p": r_["p"], "r2": r_["r2"]})
    R["long_diff_without_caf"] = ldn
    print(pd.DataFrame(ldn).round(3).to_string())

    (OUT / "audit_results.json").write_text(json.dumps(R, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
                                            encoding="utf-8")
    print("\nAudit complete. Results in reports/audit/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refetch", action="store_true")
    main(ap.parse_args().refetch)
