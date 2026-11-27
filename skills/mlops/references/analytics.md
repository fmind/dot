---
name: analytics
description: "Design and audit KPI analyses and A/B experiments: power, SRM, bias, causality, uncertainty."
---

# Statistical, KPI & A/B Experiment Analytics

Classify every study first as **exploratory/descriptive**, **observational/causal**, or **randomized experiment** so methodology and claims match the evidence. Audit analytical notebooks, KPI deep-dives, and rollout decisions with `fmind-review-analytics` ([subagent](../../subagent/SKILL.md)).

## Experiment Design, Power & Assignment

- **Size before launch (`scipy`/`statsmodels`)**: define the primary metric, randomization unit (user/account/cluster, never raw event rows — use cluster-robust SEs or cluster-level aggregation for clustered treatments), minimum detectable effect (MDE), `alpha`, power (`1-beta`), and fixed horizon via `statsmodels.stats.power.NormalIndPower` / `TTestIndPower`.
- **Guard assignment integrity (SRM)**: run a chi-square goodness-of-fit Sample Ratio Mismatch check (`scipy.stats.chisquare`) on actual vs expected arm counts before reading lift; treat `p < 0.001` as a triggering, logging, or bucketing defect. Watch for novelty, carryover, and network interference.
- **Control peeking & multiple testing**: forbid unadjusted early peeking on fixed-horizon p-values (use pre-registered fixed horizons or explicit group-sequential / always-valid bounds). Control error rates across multi-metric or multi-slice cuts with Benjamini-Hochberg FDR (`scipy.stats.false_discovery_control`) or Bonferroni FWER for strict decision gates.
- **Reduce variance cleanly**: apply CUPED (`Y_adj = Y - theta * (X - mean(X))`, estimating `theta` strictly from pre-experiment covariates) or post-stratification to tighten confidence intervals without introducing post-treatment bias.

## Causal Rigor, Bias & Uncertainty

- **Hold causal boundaries**: never use causal verbs (_caused_, _drove_, _lifted_) on observational data without an identification design (difference-in-differences with parallel-trends checks, IV, RD, or matched controls). Stratify key segments to catch **Simpson's paradox** and cohort mix shifts, and account for seasonality, trends, and external shocks in before/after comparisons.
- **Prevent survivorship & denominator bias**: never filter to retained, active, or completed entities when measuring conversion or churn; keep metric definitions and denominators identical across comparison periods, guard right-censored windows and base-rate neglect on rare events, and log explicit row attrition counts on every `filter`, `dropna()`, or inner join.
- **Match estimators to distributions**: pair arithmetic means with median, IQR, and upper quantiles (`p90`/`p99`) on skewed or heavy-tailed metrics (revenue, counts, durations). Report effect sizes, confidence intervals, and sample `n` (never bare p-values); verify parametric t-tests on severe skew or small `n` with bootstrap or non-parametric checks (Mann-Whitney / permutation).
- **Guardrails & slice stability**: pair every headline KPI with counter/guardrail metrics (latency, error rate, churn, spend) matching production formulas, inspect segment slices for opposing effects, and flag or suppress noisy small-`n` bins.

## Reproducible Analytical Stack

- **Deterministic pipeline**: query snapshots with explicit UTC `[start, end)` bounds in [sql](../../sql/SKILL.md) (DuckDB) or [polars](polars.md), pin snapshot timestamps/digests, and execute analyses in reactive [marimo](marimo.md) notebooks without hidden cross-cell state or hardcoded magic constants.
- **Verify rendered numbers & charts**: confirm summary tables match live outputs and export clean visuals via [diagrams-as-code/charts](../../diagrams-as-code/references/charts.md) (paired with `fmind-review-visuals` on plots).

## Documentation

- [SciPy stats](https://docs.scipy.org/doc/scipy/reference/stats.html) · [statsmodels power](https://www.statsmodels.org/stable/stats.html#power-and-sample-size-calculations) · Companions: [marimo](marimo.md), [polars](polars.md), [sql](../../sql/SKILL.md), [subagent](../../subagent/SKILL.md).
