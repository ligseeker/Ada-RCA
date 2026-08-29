# Ada-RCA V2-F1 Cross-Modal Concordance Decision

Status: **V2_F1 = NO_GO**
Date: 2026-08-29
Protocol: `docs/V2_MULTIMODAL_FUSION_PROTOCOL_V0.1.md`
Fit/bootstrap source commit: `76e4045af701ebea89594e7770a9534656170c18`
Gate-audit commit: `369719c55e5476a6b2217bb2008688253e375e41`

## Integrity

All aligned and misaligned F1 runs satisfy the fixed 98D feature order, frozen
68D Z2 prefix, complete candidate rankings, root coverage, frozen folds,
train-fold-only scaler, deterministic shifts, modality-row multiset
preservation, finite features, convergence, and gradient tolerance. Maximum
gradient infinity norms are `1.2657e-14` (OB aligned), `1.7195e-13` (TT
aligned), `3.0309e-14` (OB misaligned), and `2.1617e-13` (TT misaligned).

The AC@1 exact `-1/90` boundary audit is disclosed in
`docs/V2_PROTOCOL_DEVIATIONS.md`. It changed only the guard from an erroneous
floating false to the exact rational PASS; no fit, prediction, metric, or
bootstrap sample was rerun, and the F1 decision remained NO-GO.

## Overall metrics

| Dataset | Method | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---|---:|---:|---:|---:|---:|
| RE2-OB | Z2 | 0.877778 | 0.988889 | 0.988889 | 0.962222 | 0.931481 |
| RE2-OB | F1-ALIGNED | 0.877778 | 0.988889 | 0.988889 | 0.962222 | 0.931481 |
| RE2-OB | F1-MISALIGNED | 0.855556 | 0.966667 | 0.988889 | 0.946667 | 0.912698 |
| RE2-TT | Z2 | 0.711111 | 0.866667 | 0.933333 | 0.851111 | 0.803472 |
| RE2-TT | F1-ALIGNED | 0.700000 | 0.855556 | 0.933333 | 0.837778 | 0.791105 |
| RE2-TT | F1-MISALIGNED | 0.722222 | 0.877778 | 0.933333 | 0.851111 | 0.807927 |

Fault macro and root macro equal the corresponding overall Avg@5 to displayed
precision. Full fault, root, fold, case metrics, candidate scores, rankings,
and root ranks are persisted under `artifacts/v2/f1_concordance/` and
`artifacts/v2/f1_misaligned/`.

## Performance comparison: F1-ALIGNED minus Z2

| Metric | OB delta [95% CI] | TT delta [95% CI] | Equal-dataset mean [95% CI] |
|---|---:|---:|---:|
| AC@1 | 0.000000 [0.000000,0.000000] | -0.011111 [-0.066667,0.033333] | -0.005556 [-0.033333,0.016667] |
| AC@3 | 0.000000 [0.000000,0.000000] | -0.011111 [-0.033333,0.000000] | -0.005556 [-0.016667,0.000000] |
| AC@5 | 0.000000 [0.000000,0.000000] | 0.000000 [0.000000,0.000000] | 0.000000 [0.000000,0.000000] |
| Avg@5 | 0.000000 [0.000000,0.000000] | -0.013333 [-0.028889,0.000000] | -0.006667 [-0.014444,0.000000] |
| MRR | 0.000000 [0.000000,0.000000] | -0.012367 [-0.040412,0.013108] | -0.006183 [-0.020206,0.006554] |

Root ranks are unchanged on all 90 OB cases. On TT, aligned improves 3 cases,
is unchanged on 79, and degrades 8 relative to Z2; mean signed root-rank change
is `+0.255556` where positive means worse.

The TT Avg@5 delta is concentrated directionally in delay (`-0.053333`), loss
(`-0.013333`), and socket (`-0.013333`); CPU, disk, and memory are null to
floating precision. This subgroup description does not authorize selection or
repair.

### Performance gate

- OB Delta Avg@5 >= 0: PASS (`0.000000`).
- TT Delta Avg@5 >= 0: FAIL (`-0.013333`).
- At least one strict positive Avg@5 delta: FAIL.
- Equal-dataset Avg@5 CI lower > 0: FAIL (`-0.014444`).
- AC@1 guard on OB: PASS (`0`).
- AC@1 guard on TT: PASS (exactly `-1/90`).
- Integrity: PASS.

Therefore `PERFORMANCE_GO = false`.

## Mechanism comparison: F1-ALIGNED minus F1-MISALIGNED

| Metric | OB delta [95% CI] | TT delta [95% CI] | Equal-dataset mean [95% CI] |
|---|---:|---:|---:|
| AC@1 | +0.022222 [-0.033333,0.088889] | -0.022222 [-0.100000,0.044444] | 0.000000 [-0.050000,0.050000] |
| AC@3 | +0.022222 [0.000000,0.055556] | -0.022222 [-0.077778,0.033333] | 0.000000 [-0.027778,0.027778] |
| AC@5 | 0.000000 [0.000000,0.000000] | 0.000000 [-0.033333,0.033333] | 0.000000 [-0.016667,0.016667] |
| Avg@5 | +0.015556 [0.000000,0.033333] | -0.013333 [-0.046722,0.022222] | +0.001111 [-0.017778,0.021111] |
| MRR | +0.018783 [-0.012963,0.053042] | -0.016822 [-0.060366,0.026085] | +0.000981 [-0.026103,0.028674] |

Aligned improves 9, ties 78, and degrades 3 OB root ranks relative to
misaligned. On TT it improves 10, ties 63, and degrades 17. Avg@5 fault deltas
are nonnegative on OB, but TT is negative for CPU, loss, memory, and socket,
positive for delay, and null for disk.

### Mechanism gate

- OB Delta Avg@5 > 0: PASS (`+0.015556`).
- TT Delta Avg@5 > 0: FAIL (`-0.013333`).
- Equal-dataset Avg@5 CI lower > 0: FAIL (`-0.017778`).
- Integrity: PASS.

Therefore `MECHANISM_GO = false`.

## Decision and interpretation

`PERFORMANCE_GO AND MECHANISM_GO` is false, therefore **V2_F1 = NO_GO**.

**FACT:** XC30 is null relative to Z2 on OB and degrades TT Avg@5. Deliberate
misalignment is worse on OB but better on TT, with an equal-dataset interval
that includes zero.

**INFERENCE:** the observed result is heterogeneous across datasets and does
not supply stable incremental ranking information from the fixed aligned
cross-modal representation.

**NOT SUPPORTED:** attributing an OB difference to same-service cross-modal
temporal concordance, claiming an incremental V2 improvement, selecting only
the favorable modality pairs, changing XC definitions, or proceeding to F2.

Per protocol, F2 and F3 are not authorized and are not implemented.

**STOPPED FOR HUMAN REVIEW**
