# Optimization Search Space Freeze V1

Status: `SEARCH_SPACE_FROZEN`
Freeze occurs before the first optimization outer OOF.

## Representations (6/8 slots)

1. `Z1-M`: metric channel, 17 fields.
2. `M+L`: metric and log, 34 fields.
3. `M+TE`: metric and trace-error, 34 fields.
4. `M+TL`: metric and trace-latency, 34 fields.
5. `M+L+TL`: metric, log, trace-latency, 51 fields.
6. `FULL-Z2`: all four canonical channels, 68 fields.

Channels are exact frozen V1 field blocks. No derived root/fault/service
identity fields are admitted. The sparse-event family is predeclared in the
protocol (rate, log1p difference/ratio clipped to [-10,10], emergence flag,
post-active fraction, burst change, onset fraction, coverage, available) but is
not enabled because the current canonical artifacts do not contain a
root-independent raw sparse bundle with complete mapping.

## Rankers and grids

- `R0-ConditionalLogit`: lambda `{0.1, 1.0, 10.0}`.
- `R1-XGBoost rank:pairwise`: unavailable in the pinned environment; no
  fallback implementation is substituted.
- `R2-LightGBM LambdaRank`: unavailable in the pinned environment; no fallback
  implementation is substituted.

Per outer-train split, representations are screened with lambda 1.0 under
deterministic three-fold inner CV; only `TOP_K_REPRESENTATIONS = 3` continue to
the ranker/grid stage. Inner objective is event-level Avg@5. Ties use higher
AC@1, then higher MRR, then lower lambda, then lower representation
complexity/name. A deterministic two-fold inner fallback is allowed only when
three-fold stratification is impossible.

## Ensemble and budgets

The only allowed ensemble is conditional-logit plus the best available tree
family, with event-wise z-score normalization fitted on inner-train and alpha
`{0, 0.25, 0.5, 0.75, 1}` selected inside inner CV. Because both tree
dependencies are unavailable, no ensemble is selected.

Maximum formal budget: 8 representations, 3 ranker families, 8 XGBoost
configurations, 8 LightGBM configurations, 3 conditional-logit lambdas,
TOP-K=3, and one 3-fold outer OOF per dataset. Seed is `20260829`.

After this commit, no scientific search-space element, objective, tie-break,
candidate universe, fold, or rescue may be added. Outer OOF results can only be
used for final metrics and diagnostics. Any implementation defect invalidates
the affected run and requires a documented full rerun.
