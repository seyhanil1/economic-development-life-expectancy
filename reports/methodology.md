# Methodology

## Design

This is an **observational, ecological** study. The unit of observation is an *economy* (country or territory) in a given year. All estimates describe **associations between country-level averages**. They do not identify causal effects, and they do not describe individuals.

**Equal weighting.** Every economy counts once, so Nauru and India carry the same weight. The estimates answer the question "how does life expectancy vary across *countries*". They do not answer "how does it vary across *people*". A population-weighted analysis (WLS with population weights) would be a different estimand. It was not run, because it needs a third indicator (`SP.POP.TOTL`); see *Possible extensions*.

## Sample

* 217 World Bank economies. All 79 aggregates are excluded (see `data_quality_report.md`).
* Window 2000–2024: the common years of both indicators.
* Analysis sample: 4,916 economy-years with both indicators valid, covering 199 economies.
* Primary cross-section: **2023**, n = 197. 2023 was chosen over 2024 for two reasons. First, the 2024 life-expectancy values may be largely model- or projection-based: they change unusually smoothly from 2023, and the source does not say what they are (see `data_quality_report.md` §3). Second, GDP coverage in 2023 is close to its maximum. Whether the 2023 values are themselves estimates or projections was **not verified** either. The 2024 cross-section gives almost the same result.
* Comparison years: 2000, 2010, 2019 (the last year before the pandemic) and 2023, plus every year from 2000 to 2024 in the annual series.

## Variables

* Outcome `LE`: life expectancy at birth in years. This is a *period* measure: the mean length of life under the age-specific death rates of that year.
* Exposure `GDP`: GDP per capita, PPP, constant 2021 international \$. `ln(GDP)` is the natural logarithm, defined only for GDP > 0. Every observed value is positive.
* No control variables were added. The research question is the *bivariate* association, its shape and its stability. Adding controls such as health spending, schooling or inequality would change the estimand to a conditional association. It would also bring in more missing data, and some of those variables are plausibly *mediators* (GDP → health spending → LE), so controlling for them would be wrong if the target is the total association.

## 1. Descriptive statistics

For GDP, ln(GDP) and LE: n, mean, SD (ddof = 1), min, Q1, median, Q3, max, skewness and excess kurtosis (both bias-corrected). They are reported for each comparison year and for the pooled 2000–2024 panel. The pooled statistics describe the data only. They are not used for inference, because the observations are repeated.

## 2. Correlation

* **Pearson r** measures *linear* association. It is sensitive to outliers and to skewed marginal distributions. The 95% CI uses the Fisher z-transform with SE = 1/√(n−3).
* **Spearman ρ** is the Pearson correlation of the ranks. It measures *monotone* association, is invariant to monotone transformations (so ρ(GDP, LE) = ρ(lnGDP, LE)) and is robust to outliers. The 95% CI uses Fisher z with the Bonett–Wright (2000) SE √((1+ρ²/2)/(n−3)).
* The p-values test H₀: correlation = 0. With n ≈ 200 this null is not informative. The CIs matter more.

## 3. Cross-sectional regression (primary year)

All three models are fitted **on the same 197 observations**, so R², AIC and BIC can be compared.

* **Model A**: LE = β₀ + β₁·(GDP / 1000) + ε
* **Model B**: LE = β₀ + β₁·ln(GDP) + ε
* **Model C** (curvature check): LE = β₀ + β₁·c + β₂·c² + ε, where c = ln(GDP) − mean. Centring reduces collinearity between c and c².

**Interpreting Model B.** A 1% higher GDP is associated with about β₁/100 more years. A 10% higher GDP gives β₁·ln(1.1) years, and a doubling gives β₁·ln 2 years. In *levels*, the slope dLE/dGDP = β₁/GDP decreases as GDP rises. This is the "diminishing marginal association" asked about in sub-question 2.

**Inference.** OLS point estimates with **HC3** heteroskedasticity-consistent standard errors (MacKinnon & White, 1985). HC3 is used by default because the variance of LE plausibly differs across income levels, and HC3 behaves well in samples of moderate size. Classical standard errors are also reported in `regression_models_2023.csv`. When the two are close, the main inferences do not depend on the choice.

Implementation detail (verified in the audit): with `cov_type="HC3"` or `"cluster"`, statsmodels uses the **normal distribution** for p-values and CIs (`use_t=False`), not the t distribution. With n = 197 and G = 199 clusters the difference is negligible: the two-way FE CI is [0.494, 2.605] with z and [0.487, 2.612] with t(198).

The cluster-robust variance uses the CR1 correction G/(G−1)·(N−1)/(N−K), and statsmodels counts the 222 FE dummies in K. The resulting SE (0.539) is about 2% larger than the Stata `xtreg, fe vce(cluster)`-style value (0.528), so it is slightly conservative.

The Breusch–Pagan test is statsmodels' default **studentised (Koenker) version**, which is robust to non-normal errors. The classical version gives p = 0.072 for Model B, against 0.160 for the Koenker version.

## 4. Diagnostics

| Assumption / issue | Check |
|---|---|
| Linearity / functional form | residual vs fitted plot with LOWESS; Ramsey RESET (powers 2 and 3); comparison with Model C |
| Homoskedasticity | Breusch–Pagan; White test |
| Normality of errors | Q-Q plot; Jarque–Bera; Shapiro–Wilk. With n ≈ 200, mild non-normality does not invalidate inference on coefficients |
| Influential observations | leverage (cut-off 2k/n); externally studentised residuals (cut-off ±3); Cook's distance (cut-off 4/n); DFBETAS |
| Sensitivity to influence | refit without the economies flagged by Cook's D or the studentised residual; Huber M-estimator (robust linear model) on the full sample |

The thresholds are conventional rules of thumb, not tests. A flagged economy is not an error. It is an economy that the model describes poorly, and it gets a closer look.

## 5. Over time

Two different questions are kept apart.

**(a) Repeated cross-sections (sub-question 4).** Model B is estimated separately for each year from 2000 to 2024, (i) on all economies available that year and (ii) on a constant set of 189 economies observed in all 25 years, so that changes in composition cannot drive the trend. The yearly CIs are **not** compared with each other to test for change, because the same countries appear in every year and the estimates are not independent. Instead, one pooled model is fitted:

LE_it = α_t + (b + c·(t − 2000))·ln GDP_it + ε_it

It has year intercepts α_t and **standard errors clustered by country**. The coefficient c tests whether the slope drifts over time.

**(b) Within-country change (sub-question 6).** Variation across countries and variation within a country over time are different sources of information:

| Estimator | Variation used | Inference |
|---|---|---|
| Pooled OLS (± year effects) | mainly between countries | SE clustered by country |
| Between (country means, 1 observation per country) | between countries only | HC3 |
| Country fixed effects (FE) | within country, *including* the common global trend | SE clustered by country |
| Two-way FE (country + year) | within country, *net of* shocks and trends common to all countries in a year | SE clustered by country |
| Long differences (ΔLE on ΔlnGDP, 2000→2019 and 2000→2023) | within country over a long horizon, 1 observation per country | HC3; plus a version that controls for initial LE (catch-up) |

**Why panel methods.** Sub-question 6 asks about within-country change, so panel methods are *needed*. They are *feasible* because there are ~199 economies over 25 years, enough clusters for cluster-robust inference. Pooling the 4,916 economy-years with classical OLS standard errors would treat them as 4,916 independent observations. Residuals of the same country are strongly autocorrelated, so those standard errors would be far too small. Every panel model here therefore clusters by country.

**Why year effects.** LE and GDP both trend upward almost everywhere over 2000–2024. A model with country FE but no year effects attributes this common trend to GDP. That is the classic problem of a spurious correlation between trending series. Year FE remove it. The two-way FE slope is therefore the most defensible within-country estimate. It is still **not causal**: time-varying confounders specific to a country (conflict, epidemics, policy reform), reverse causality (health → productivity) and measurement error remain. Measurement error also biases the FE estimate toward zero (attenuation), more strongly than in the cross-section.

## 6. Sensitivity analyses

* Excluding the COVID-19 years 2020–2022 (panel models).
* Excluding life-expectancy values flagged as extreme (< 40) or as transient shocks (panel models).
* Excluding influential economies, and Huber regression (2023 cross-section).
* Constant-composition sample of 189 economies (annual cross-sections and slope-trend test).

## Archived data releases (audit only)

The data-version sensitivity analysis (`audit/run_audit.py`) compares the current WDI release with archived releases from the *WDI Database Archives* (API source 57).

* **Stored in the repository** (`data/raw/archive/`):
  * life expectancy (`SP.DYN.LE00.IN`) from release **202503**, the last before the April 2025 revision;
  * the same series from release **202504**, the first after it.
* **Format.** Each file is the complete API response (all entities, 1960 onward), compressed with deterministic gzip (level 9, mtime = 0).
* **Integrity.** `ARCHIVE_MANIFEST.json` records the SHA-256 and size of the original download and of the compressed file. `audit/archive_io.py` decompresses the file in memory and refuses it if the SHA-256 differs from the original.
* **What each release is used for:**
  * 202503: life expectancy of the 2022 cross-section and of the 2000–2022 two-way FE panel. GDP is kept at the current release, so that only the life-expectancy vintage changes.
  * 202503 vs 202504: the size of the revision (economies, 2000–2022).
* **Not stored.** Release 202412 was downloaded but is not published. Its values are identical to 202503 for every economy. Earlier releases (e.g. 202407) were inspected only through direct API queries during the audit.

## Possible extensions (not done)

* Population-weighted estimates (needs `SP.POP.TOTL`).
* Male and female life expectancy separately (`SP.DYN.LE00.MA.IN`, `SP.DYN.LE00.FE.IN`).
* Lagged GDP or distributed-lag models for the within-country dynamics.
* A sensitivity analysis to missing data that bounds the effect of the 18 excluded economies, for example using external GDP estimates for Venezuela and Yemen.

## Software

Python 3.14.4, pandas 3.1.0, NumPy 2.5.4, SciPy 1.18.1, statsmodels 0.15.0, Matplotlib 3.11.2, requests 2.33.1, pytest 9.2.0.
