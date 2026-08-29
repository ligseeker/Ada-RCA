# Ada-RCA V2-F0 Modality Complementarity Audit

Status: **DESCRIPTIVE AUDIT COMPLETE - NO MODEL SELECTION AUTHORIZED**
Date: 2026-08-29
Protocol: `docs/V2_MULTIMODAL_FUSION_PROTOCOL_V0.1.md`
Fit source commit: `d3041956ca376835831293e971304bcad0129afa`
Audit-resume commit: `9e64ab1fff4fc18049c10b3e778f34f6772b1aef`

## Scope and integrity

F0 used the frozen 17D blocks for metric (`M`), log (`L`), trace-error (`TE`),
and trace-latency (`TL`). All 15 preregistered variants used the same frozen
folds, training-fold-only `StandardScaler`, `src/rca/p4.py` event-level
conditional logit, L2 lambda 1.0, and complete legal candidate rankings. No
hyperparameter search or modality selection was performed.

All 30 dataset/variant runs converged with gradient infinity norm below
`1e-8`. Metrics recompute exactly from 90 complete OOF rankings per dataset.
`FULL-Z2` has exact ranking and metric identity with V1 on both datasets. The
fresh-fit score differences are recorded as `1.2079226507921703e-13` for OB
and `1.2008172234345693e-12` for TT. The audit-only correction and no-rerun
resume are disclosed in `docs/V2_PROTOCOL_DEVIATIONS.md`; no fit or performance
value changed.

## Full results

`fault macro` and `root macro` below are unweighted macro Avg@5. Full fault,
root, fold, and case-level metrics are in the run artifacts.

### RE2-OB

| Variant | AC@1 | AC@3 | AC@5 | Avg@5 | MRR | Fault macro | Root macro |
|---|---:|---:|---:|---:|---:|---:|---:|
| M | 0.866667 | 0.977778 | 0.988889 | 0.955556 | 0.923148 | 0.955556 | 0.955556 |
| L | 0.188889 | 0.400000 | 0.588889 | 0.400000 | 0.381107 | 0.400000 | 0.400000 |
| TE | 0.000000 | 0.200000 | 0.600000 | 0.240000 | 0.203889 | 0.240000 | 0.240000 |
| TL | 0.100000 | 0.522222 | 0.733333 | 0.437778 | 0.346257 | 0.437778 | 0.437778 |
| M+L | 0.911111 | 0.977778 | 0.988889 | 0.962222 | 0.943254 | 0.962222 | 0.962222 |
| M+TE | 0.866667 | 0.977778 | 0.988889 | 0.955556 | 0.923148 | 0.955556 | 0.955556 |
| M+TL | 0.833333 | 0.988889 | 1.000000 | 0.953333 | 0.907778 | 0.953333 | 0.953333 |
| L+TE | 0.144444 | 0.400000 | 0.577778 | 0.373333 | 0.351768 | 0.373333 | 0.373333 |
| L+TL | 0.300000 | 0.600000 | 0.866667 | 0.608889 | 0.516124 | 0.608889 | 0.608889 |
| TE+TL | 0.066667 | 0.588889 | 0.733333 | 0.457778 | 0.345582 | 0.457778 | 0.457778 |
| FULL-M | 0.300000 | 0.600000 | 0.866667 | 0.608889 | 0.516124 | 0.608889 | 0.608889 |
| FULL-L | 0.833333 | 0.988889 | 1.000000 | 0.953333 | 0.907778 | 0.953333 | 0.953333 |
| FULL-TE | 0.877778 | 0.988889 | 0.988889 | 0.962222 | 0.931481 | 0.962222 | 0.962222 |
| FULL-TL | 0.911111 | 0.977778 | 0.988889 | 0.962222 | 0.943254 | 0.962222 | 0.962222 |
| FULL-Z2 | 0.877778 | 0.988889 | 0.988889 | 0.962222 | 0.931481 | 0.962222 | 0.962222 |

### RE2-TT

| Variant | AC@1 | AC@3 | AC@5 | Avg@5 | MRR | Fault macro | Root macro |
|---|---:|---:|---:|---:|---:|---:|---:|
| M | 0.711111 | 0.855556 | 0.866667 | 0.828889 | 0.796499 | 0.828889 | 0.828889 |
| L | 0.066667 | 0.188889 | 0.288889 | 0.186667 | 0.198023 | 0.186667 | 0.186667 |
| TE | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.039034 | 0.000000 | 0.000000 |
| TL | 0.122222 | 0.122222 | 0.122222 | 0.122222 | 0.153173 | 0.122222 | 0.122222 |
| M+L | 0.700000 | 0.833333 | 0.900000 | 0.817778 | 0.785461 | 0.817778 | 0.817778 |
| M+TE | 0.711111 | 0.855556 | 0.866667 | 0.828889 | 0.796499 | 0.828889 | 0.828889 |
| M+TL | 0.788889 | 0.844444 | 0.900000 | 0.851111 | 0.836920 | 0.851111 | 0.851111 |
| L+TE | 0.066667 | 0.188889 | 0.288889 | 0.186667 | 0.198023 | 0.186667 | 0.186667 |
| L+TL | 0.188889 | 0.400000 | 0.500000 | 0.366667 | 0.337984 | 0.366667 | 0.366667 |
| TE+TL | 0.122222 | 0.122222 | 0.122222 | 0.122222 | 0.153173 | 0.122222 | 0.122222 |
| FULL-M | 0.188889 | 0.400000 | 0.500000 | 0.366667 | 0.337984 | 0.366667 | 0.366667 |
| FULL-L | 0.788889 | 0.844444 | 0.900000 | 0.851111 | 0.836920 | 0.851111 | 0.851111 |
| FULL-TE | 0.711111 | 0.866667 | 0.933333 | 0.851111 | 0.803472 | 0.851111 | 0.851111 |
| FULL-TL | 0.700000 | 0.833333 | 0.900000 | 0.817778 | 0.785461 | 0.817778 | 0.817778 |
| FULL-Z2 | 0.711111 | 0.866667 | 0.933333 | 0.851111 | 0.803472 | 0.851111 | 0.851111 |

## Availability and coverage

| Dataset | Modality | Availability mean | Coverage mean | Event availability range | Event coverage range |
|---|---|---:|---:|---:|---:|
| RE2-OB | M | 1.000000 | 0.993472 | [1.000000, 1.000000] | [0.675000, 1.000000] |
| RE2-OB | L | 0.815152 | 0.809242 | [0.727273, 0.818182] | [0.521591, 0.818182] |
| RE2-OB | TE | 0.000000 | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] |
| RE2-OB | TL | 0.377778 | 0.373737 | [0.090909, 0.636364] | [0.090909, 0.636364] |
| RE2-TT | M | 1.000000 | 1.000000 | [1.000000, 1.000000] | [1.000000, 1.000000] |
| RE2-TT | L | 0.278922 | 0.278472 | [0.000000, 0.294118] | [0.000000, 0.294118] |
| RE2-TT | TE | 0.000000 | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] |
| RE2-TT | TL | 0.138399 | 0.138145 | [0.000000, 0.191176] | [0.000000, 0.191176] |

## Root-rank disagreement

The table reports mean absolute root-rank difference and the number of cases
with unequal single-modality root ranks.

| Pair | OB mean abs | OB unequal | TT mean abs | TT unequal |
|---|---:|---:|---:|---:|
| M-L | 3.444444 | 75/90 | 18.188889 | 88/90 |
| M-TE | 4.622222 | 88/90 | 40.144444 | 90/90 |
| M-TL | 2.777778 | 77/90 | 33.277778 | 81/90 |
| L-TE | 3.866667 | 86/90 | 24.511111 | 89/90 |
| L-TL | 3.155556 | 84/90 | 22.222222 | 89/90 |
| TE-TL | 2.111111 | 79/90 | 8.133333 | 81/90 |

The disagreement values are partly driven by candidate-universe size and the
strong modality availability imbalance. They do not establish useful
complementarity or incremental information.

## Leave-one-out transitions

Root-rank change is `rank(FULL-X) - rank(FULL-Z2)`; negative is improved.

| Dataset | Variant | Improved | Unchanged | Degraded | Mean signed change | Mean abs change |
|---|---|---:|---:|---:|---:|---:|
| RE2-OB | FULL-M | 2 | 27 | 61 | 1.844444 | 1.888889 |
| RE2-OB | FULL-L | 6 | 75 | 9 | 0.044444 | 0.177778 |
| RE2-OB | FULL-TE | 0 | 90 | 0 | 0.000000 | 0.000000 |
| RE2-OB | FULL-TL | 4 | 82 | 4 | 0.011111 | 0.100000 |
| RE2-TT | FULL-M | 11 | 15 | 64 | 12.500000 | 14.077778 |
| RE2-TT | FULL-L | 11 | 65 | 14 | 0.611111 | 1.011111 |
| RE2-TT | FULL-TE | 0 | 90 | 0 | 0.000000 | 0.000000 |
| RE2-TT | FULL-TL | 2 | 71 | 17 | 0.377778 | 0.422222 |

## Unique rank-1 corrections

Relative to FULL-Z2, the largest correction counts were:

- RE2-OB: M and M+TE each corrected 5 cases; M+L, M+TL, FULL-L, and FULL-TL
  each corrected 4. Other variants corrected 0-2 cases.
- RE2-TT: M+TL and FULL-L each corrected 10 cases; M and M+TE each corrected
  8; other variants corrected 0-3 cases.

Family-unique rank-1 counts also show that most single-modality rank-1 cases
belong to M (57 OB and 53 TT), while L has 3 OB and 4 TT unique cases, TL has
0 OB and 2 TT, and TE has none. Among pair variants, M+L has 5 OB and 2 TT
family-unique rank-1 cases; M+TL has 0 OB and 2 TT; L+TE and TE+TL each have
one OB case only. Exact opaque case IDs are preserved in
`rank1_corrections.json`.

## Descriptive observations

1. Metric is the dominant observed block under this corpus and representation.
   It is fully available, M alone is close to FULL-Z2 in Avg@5, and removing M
   causes broad degradation on both datasets.
2. Frozen trace-error contributes no observed feature variation: availability
   and coverage are zero on every event, `FULL-TE` is rank-identical to
   FULL-Z2, and M+TE is identical to M in aggregate metrics. TE-only results
   reflect deterministic canonical tie ordering, not telemetry signal.
3. Log and trace-latency are sparse, especially on TT. Their single-modality
   aggregate performance is weak, but they change some individual root ranks,
   including both corrections and degradations. On TT, M+TL and FULL-L match
   FULL-Z2 Avg@5 while changing the top-rank/top-k distribution; on OB, M+L and
   FULL-TL match FULL-Z2 Avg@5. These are heterogeneous point estimates, not a
   validated incremental mechanism.
4. Large single-modality root-rank disagreement demonstrates different
   rankings, but disagreement alone is not complementarity. Availability,
   canonical ties, and the larger TT candidate registry are material
   confounds.

## Scientific boundary

**FACT:** the fixed modalities produce heterogeneous root rankings and a small
number of modality-specific corrections; metric carries most observed
standalone ranking performance; trace-error is unavailable in the frozen
bundles; log and trace-latency are sparse.

**INFERENCE:** there is enough descriptive rank heterogeneity to execute the
already-preregistered F1 falsification, but F0 does not establish that aligned
same-service cross-modal concordance has incremental information.

**NOT SUPPORTED:** selecting a modality pair, dropping any F1 pair, claiming a
cross-modal mechanism, claiming that sparse modalities improve FULL-Z2, or
using F0 to tune XC30. F1 remains fixed to all six modality pairs.

## Artifacts

The formal directory is `artifacts/v2/f0_modality_audit/`. It contains 30
complete run directories, the case-by-variant root-rank matrix, metric table,
pairwise disagreement, rank-1 corrections, leave-one-out transitions,
event-level availability/coverage, V1 identity records, provenance, model and
scaler states, convergence records, environments, runtimes, and checksums.
