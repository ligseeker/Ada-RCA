# P3 Exploratory Post-Mortem

Status: **EXPLORATORY ONLY**. P4-G0 protocol, implementation, tests, and configs were committed before this analysis. These results cannot modify P4.

## Z2-Z1 paired bootstrap

| Dataset | Avg@5 delta [95% CI] | AC@1 delta [95% CI] |
|---|---:|---:|
| RE2OB | +0.026667 [+0.000000, +0.057778] | +0.011111 [-0.055556, +0.077778] |
| RE2TT | +0.086667 [+0.020000, +0.157778] | +0.122222 [+0.033333, +0.211111] |

Two-dataset descriptive mean: Avg@5 +0.056667; AC@1 +0.066667. No untouched confirmation claim is made.

## Case transitions

- RE2OB Z2 vs Z1: {'z2_vs_z1_transitions': {'improved': 10, 'degraded': 5, 'unchanged': 75}, 'top_transitions': {'top1_gained': 6, 'top3_gained': 3, 'top5_gained': 1}, 'top_lost': {'top1_lost': 5, 'top3_lost': 0, 'top5_lost': 0}}.
- RE2TT Z2 vs Z1: {'z2_vs_z1_transitions': {'improved': 27, 'degraded': 14, 'unchanged': 49}, 'top_transitions': {'top1_gained': 17, 'top3_gained': 13, 'top5_gained': 10}, 'top_lost': {'top1_lost': 6, 'top3_lost': 7, 'top5_lost': 2}}.

## MI, fault, root, fold, and coverage

OB MI-1 cases show a Z2-Z1 Avg@5 delta of `+0.039394`; non-MI-1 cases show
`-0.008333`. OB MI-3 cases improve Avg@5 by `+0.056000` but AC@1 changes by
`-0.040000`. TT is entirely MI-1, so a TT non-MI-1 comparison is unavailable;
TT MI-3 Avg@5 changes by `+0.061176`. The five TT non-MI-3 cases have a large
`+0.520000` Avg@5 delta and must not be generalized because the subgroup is
tiny.

OB fault-level Avg@5 deltas are all non-negative (`+0.013333` to `+0.040000`),
but fold 1 is negative (`-0.006667`). OB root gains range from `0` for
emailservice to `+0.088889` for currencyservice. TT is strongly heterogeneous:
CPU is `+0.266667`, SOCKET `+0.160000`, DISK `0`, and DELAY `-0.080000`.
TT root deltas range from `+0.444444` for ts-train-service to `-0.066667` for
ts-order-service; all folds are positive, but fold 2 is largest (`+0.120000`).

Coverage is available from frozen feature artifacts. Mean observed-q coverage
is `0.544113` on OB and `0.354154` on TT. Correlations between coverage and
Z2-vs-Z1 root-rank gain are small (absolute values at most `0.126`); this is
descriptive and does not establish absence of a coverage interaction.

Detailed outputs are preserved in `artifacts/postmortem/mi_subset_analysis.json`,
`fault_root_fold_analysis.json`, and `coverage_analysis.json`. Interpret all
heterogeneity descriptively only. P3-G1 remains `NO-GO / CLOSED`.

## Provenance

Generated from clean Ada-RCA commit `1d58464df7cc70ae8b1a96470f943fe946afee42` using only committed P3 predictions, MI membership, and frozen feature artifacts; bootstrap uses 10,000 fault-stratified paired case resamples with seed 20260826.
