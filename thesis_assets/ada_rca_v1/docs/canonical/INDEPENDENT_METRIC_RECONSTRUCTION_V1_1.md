# Independent Frozen Rank-Metric Reconstruction V1.1

Status: **GATE 1 PASS**  
Protocol basis: `RCA_EVIDENCE_CLOSURE_PROTOCOL_AMENDMENT_V1_1.md`  
Machine-readable result:
`artifacts/evidence_closure/metric_reconstruction_v1_1.json`

## Independence boundary

The reconstruction reads only committed frozen ranking/root-rank artifacts and
canonical case, fold, fault, root, and candidate registries. It does not import
or call `src/rca/evaluator.py`, fit a model, regenerate a score, modify a root
rank, or reconstruct a missing candidate ranking.

For V1-SCIENTIFIC and GLOBAL-OPT, the one-indexed true-root rank is derived
from each immutable complete ranking. For PER-DATASET-OPT, it is read directly
from the immutable `case_ranks.csv` artifact.

## Verified metric definitions

Let `r_i` be the one-indexed true-root rank for case `i`, let `N = 90`, and let
`1[condition]` be one when the condition is true and zero otherwise. The frozen
evaluator source establishes the following definitions, which are independently
implemented from `r_i`:

```text
AC@k   = (1/N) * sum_i 1[r_i <= k], for k in {1, 3, 5}

Avg@5 = (1/N) * sum_i ((1/5) * sum_{k=1}^5 1[r_i <= k])

MRR   = (1/N) * sum_i (1/r_i)
```

Thus Avg@5 gives case utility `1.0, 0.8, 0.6, 0.4, 0.2, 0.0` for root ranks
`1, 2, 3, 4, 5, >5`, respectively.

## Evidence-level classification

| Track | Dataset | FULL_RANKING_INTEGRITY | RANK_METRIC_SUFFICIENT |
|---|---|---|---|
| V1-SCIENTIFIC | RE2-OB | `FULL_RANKING_INTEGRITY_PASS` | `RANK_METRIC_SUFFICIENT_PASS` |
| V1-SCIENTIFIC | RE2-TT | `FULL_RANKING_INTEGRITY_PASS` | `RANK_METRIC_SUFFICIENT_PASS` |
| GLOBAL-OPT | RE2-OB | `FULL_RANKING_INTEGRITY_PASS` | `RANK_METRIC_SUFFICIENT_PASS` |
| GLOBAL-OPT | RE2-TT | `FULL_RANKING_INTEGRITY_PASS` | `RANK_METRIC_SUFFICIENT_PASS` |
| PER-DATASET-OPT | RE2-OB | `FULL_RANKING_INTEGRITY_NOT_AUDITABLE` | `RANK_METRIC_SUFFICIENT_PASS` |
| PER-DATASET-OPT | RE2-TT | `FULL_RANKING_INTEGRITY_NOT_AUDITABLE` | `RANK_METRIC_SUFFICIENT_PASS` |

The PER-DATASET limitation is permanent: matching root-rank metrics does not
establish missing candidate completeness, duplicate absence, score/ranking
consistency, deterministic candidate ordering, score calibration, or
candidate-level prediction reproducibility.

## Independently reconstructed metrics

| Track | Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---|---:|---:|---:|---:|---:|
| V1-SCIENTIFIC | RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| V1-SCIENTIFIC | RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |
| GLOBAL-OPT | RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| GLOBAL-OPT | RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |
| PER-DATASET-OPT | RE2-OB | 0.8555555556 | 0.9777777778 | 0.9888888889 | 0.9511111111 | 0.9157407407 |
| PER-DATASET-OPT | RE2-TT | 0.7888888889 | 0.8555555556 | 0.9000000000 | 0.8577777778 | 0.8392494434 |

## Legacy metric comparison

Every independently reconstructed metric matches the corresponding committed
legacy `overall_cases` value within the declared absolute tolerance `1e-12`.
Twenty-nine comparisons are bit-identical as parsed floating-point values. The
remaining PER-DATASET RE2-OB Avg@5 comparison differs by approximately
`1.11e-16`, which is floating-point accumulation order and is below tolerance.

| Track | Dataset | Comparisons | Maximum absolute difference | Status |
|---|---|---:|---:|---|
| V1-SCIENTIFIC | RE2-OB | 5 | 0 | PASS |
| V1-SCIENTIFIC | RE2-TT | 5 | 0 | PASS |
| GLOBAL-OPT | RE2-OB | 5 | 0 | PASS |
| GLOBAL-OPT | RE2-TT | 5 | 0 | PASS |
| PER-DATASET-OPT | RE2-OB | 5 | 1.11e-16 | PASS |
| PER-DATASET-OPT | RE2-TT | 5 | 0 | PASS |

## Gate decision

`GATE_1_PASS — GATE_2_AUTHORIZED`

This decision validates the five rank-derived quantities at the evidence level
available for each track. It does not upgrade PER-DATASET to full-ranking
integrity and does not yet validate any bootstrap interval.
