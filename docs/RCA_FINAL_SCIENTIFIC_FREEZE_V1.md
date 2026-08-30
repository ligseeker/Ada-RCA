# Ada-RCA Final Scientific Freeze V1

Final state: `RCA_FREEZE_READY_WITH_LIMITATION`

This document freezes the scientifically supportable Ada-RCA V1 method and its
claim boundary. It does not upgrade post-hoc diagnostics, development OOF
selection, unavailable evidence, or unexecuted methods into confirmatory
results.

# 1. Frozen method

Ada-RCA V1 is a service-level root-cause ranking pipeline for a confirmed
failure event. It constructs an event-relative four-channel Z2 feature vector
for every legal candidate service, fits an event-level Conditional Logit model
on training-fold candidate sets, and returns a complete descending-score
ranking with candidate-name tie breaking.

The frozen scientific configuration is:

- event window `[t0 - 600 s, t0 + 600 s)`;
- 80 bins of 15 seconds, split into 40 pre-event and 40 post-event bins;
- Metric, Log, Trace Error, and Trace Latency channels;
- pre-event-only median/MAD normalization with IQR fallback;
- per-service/channel Q90 absolute normalized-deviation aggregation;
- 68D Z2 representation;
- train-fold-only `StandardScaler`;
- event-level Conditional Logit with L2 lambda `1.0`;
- float64 deterministic fitting and canonical candidate ordering; and
- separate three-fold out-of-fold evaluation for RE2-OB and RE2-TT.

Canonical implementation: `src/rca/features.py` and
`src/rca/final_method.py`. No method component is changed by this freeze.

# 2. Repository provenance

| Role | Commit |
|---|---|
| V1 scientific reference | `bed295326e567395e725caa82840a534dcc0b1de` |
| Frozen optimization record | `53c9face2c96761c9114edb558eb6d8666a38dc6` |
| Evidence Closure final decision | `5957b465fac7351a6c55ab799a058ef66a60f9bc` |

The final decision commit is recorded after the self-contained freeze commit is
created. Any later evidence-index routing commit is documentation-only and does
not alter the frozen method or decision.

# 3. Task definition

Given a confirmed failure event, its event timestamp, prediction-visible
telemetry, and the fixed legal candidate-service registry, rank candidate
services by likelihood of being the labelled service-level root cause.

This is supervised service ranking. It is not causal discovery, fault
detection, topology propagation, or unseen-system inference.

# 4. Inputs

- Metrics: `simple_metrics.csv`.
- Logs: `logts.csv`.
- Trace Error: `tracets_err.csv`.
- Trace Latency: `tracets_lat.csv`.
- Candidate services: the committed per-dataset service registry.
- Event timestamp and prediction-visible source paths.

Root service and fault type are evaluation labels and are not predictive
features.

# 5. Frozen representation

Each channel contributes 17 fields in this exact order.

Base fields (8):

1. `magnitude`
2. `mean_impact`
3. `pre_post_shift`
4. `onset_seconds`
5. `onset_missing`
6. `persistence`
7. `coverage`
8. `channel_available`

Morphology fields (9):

1. `normalized_pre_mean`
2. `normalized_post_mean`
3. `normalized_post_minus_pre_mean`
4. `post_peak_time_fraction`
5. `post_amplitude_weighted_centroid_fraction`
6. `post_ols_slope`
7. `post_mean_absolute_adjacent_difference`
8. `post_fraction_z_ge_0_5`
9. `morphology_active`

The fixed channel order is Metric, Log, Trace Error, Trace Latency, producing
`4 x 17 = 68` dimensions. The exact feature order and digest are defined by
`src/rca/final_method.py`.

# 6. Ranker

The only executed frozen V1 ranker is Conditional Logit. Candidate rows are
grouped by event; the labelled root is the selected alternative during
training. Standardization is fitted inside the relevant training fold. The
frozen V1 lambda is `1.0` and the final ranking sorts by descending score with
ascending candidate name as the deterministic tie break.

# 7. Datasets

- RE2-OB: 90 failure cases, 11 legal candidate services per case.
- RE2-TT: 90 failure cases, 68 legal candidate services per case.

These are reused development benchmarks, not untouched external test systems.

# 8. Evaluation protocol

Each dataset uses three frozen folds with 30 test cases per fold and 60
training cases per outer fit. The candidate universe and root mapping are
committed per dataset. V1 complete rankings must contain each legal candidate
exactly once and contain the labelled root.

For one-indexed root rank `r`:

```text
AC@k   = mean(1[r <= k]), k in {1, 3, 5}
Avg@5  = mean((1/5) * sum_{k=1}^5 1[r <= k])
MRR    = mean(1/r)
```

Canonical protocol evidence:
`artifacts/evidence_closure/metric_reconstruction_v1_1.json`.

# 9. Independently reproduced V1 metrics

Canonical numeric artifact:
`artifacts/evidence_closure/metric_reconstruction_v1_1.json`.

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |

V1 has `FULL_RANKING_INTEGRITY_PASS` and
`RANK_METRIC_SUFFICIENT_PASS` on both datasets. Independent reconstruction
matches the frozen committed metrics within tolerance.

# 10. Optimization post-study

GLOBAL-OPT is the same FULL-Z2, Conditional-Logit, lambda-1 configuration as
V1. Its frozen predictions are byte-identical to V1 on both datasets; every
corrected point delta and interval is `[0, 0]`. It provides no shared gain.

PER-DATASET-OPT rank metrics are independently reproducible, but complete
candidate scores/rankings were not frozen. It permanently retains
`FULL_RANKING_INTEGRITY_NOT_AUDITABLE` while preserving
`RANK_METRIC_SUFFICIENT_PASS`.

Canonical reconstructed metrics:
`artifacts/evidence_closure/metric_reconstruction_v1_1.json`.

| Track | Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---|---:|---:|---:|---:|---:|
| GLOBAL-OPT | RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| GLOBAL-OPT | RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |
| PER-DATASET-OPT | RE2-OB | 0.8555555556 | 0.9777777778 | 0.9888888889 | 0.9511111111 | 0.9157407407 |
| PER-DATASET-OPT | RE2-TT | 0.7888888889 | 0.8555555556 | 0.9000000000 | 0.8577777778 | 0.8392494434 |

Corrected paired bootstrap uses `Delta = Candidate - V1`, 10,000 paired
fault-stratified case resamples, and seed `20260829`. Canonical numeric
artifact: `artifacts/evidence_closure/bootstrap_corrected_v1_1.json`.

| Candidate | Dataset | Metric | Point | Corrected 95% CI |
|---|---|---|---:|---:|
| GLOBAL-OPT | RE2-OB | Avg@5 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-OB | AC@1 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-OB | MRR | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-TT | Avg@5 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-TT | AC@1 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-TT | MRR | 0.0000000000 | [0.0000000000, 0.0000000000] |
| PER-DATASET-OPT | RE2-OB | Avg@5 | -0.0111111111 | [-0.0266666667, 0.0000000000] |
| PER-DATASET-OPT | RE2-OB | AC@1 | -0.0222222222 | [-0.0555555556, 0.0000000000] |
| PER-DATASET-OPT | RE2-OB | MRR | -0.0157407407 | [-0.0379629630, 0.0000000000] |
| PER-DATASET-OPT | RE2-TT | Avg@5 | +0.0066666667 | [-0.0333333333, +0.0466666667] |
| PER-DATASET-OPT | RE2-TT | AC@1 | +0.0777777778 | [0.0000000000, +0.1555555556] |
| PER-DATASET-OPT | RE2-TT | MRR | +0.0357775552 | [-0.0132650477, +0.0870892761] |

The result is `NO_CLEAR_OPTIMIZATION_GAIN`: OB is lower, TT has a
dataset-specific AC@1 signal, TT primary Avg@5 uncertainty includes zero, and
there is no consistent cross-dataset Avg@5 improvement.

# 11. Telemetry information-loss result

Canonical numeric artifact:
`artifacts/evidence_closure/telemetry_information_loss_v1_1.json`.

| Dataset | Modality | Eligible | Mapped | Scale valid | Feature active |
|---|---|---:|---:|---:|---:|
| RE2-OB | Metric | 990 | 990 | 990 | 990 |
| RE2-OB | Log | 990 | 812 | 807 | 807 |
| RE2-OB | Trace Error | 990 | 900 | 0 | 0 |
| RE2-OB | Trace Latency | 990 | 900 | 374 | 374 |
| RE2-TT | Metric | 6,120 | 6,120 | 6,120 | 6,120 |
| RE2-TT | Log | 6,120 | 1,787 | 1,707 | 1,707 |
| RE2-TT | Trace Error | 6,120 | 2,347 | 0 | 0 |
| RE2-TT | Trace Latency | 6,120 | 2,347 | 847 | 847 |

For RE2-OB, 30 candidate-case pairs have an all-zero/constant pre-event Trace
Error baseline and a post-event positive signal, yet every one is rejected by
the frozen MAD/IQR scale rule. This establishes a real information-loss
mechanism. It does not establish that a sparse-aware replacement improves RCA.

# 12. Trace Error representation invariant

Canonical numeric artifact:
`artifacts/evidence_closure/trace_error_representation_invariant.json`.

| Dataset | Rows | All-zero rows | Nonzero rows | Unique vectors | Nonzero-variance dimensions | Candidate-discriminative cases |
|---|---:|---:|---:|---:|---:|---:|
| RE2-OB | 990 | 0 | 990 | 1 | 0 | 0 / 90 |
| RE2-TT | 6,120 | 0 | 6,120 | 1 | 0 | 0 / 90 |

Every frozen TE block equals
`[0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0]`; the nonzero coordinate is
`base.onset_missing`. The block is globally nonzero but constant across all
candidates and cases. Removing it changes raw vectors only by a block common
to all candidates, so it cannot alter within-case Conditional Logit utility
differences.

Final classification:
`TRACE_ERROR_EFFECTIVELY_NONDISCRIMINATIVE_IN_FROZEN_Z2`.

Ada-RCA accepts trace-error telemetry as input, but the frozen robust-scale
representation effectively suppresses its candidate-discriminative
contribution in these datasets.

# 13. Leakage / shortcut boundary

`NO_EXPLICIT_LABEL_LEAKAGE_DETECTED`

The bounded predictive-path audits find no explicit root or fault feature,
outer-test/selection overlap, root-frequency predictive feature, or scaler fit
outside training scope. Canonical artifact:
`artifacts/opt/diagnostics/shortcut_audit.json`.

This is not proof of no shortcut. Stable service-specific coverage,
availability, and telemetry patterns may act as indirect fingerprints.

# 14. Historical evidence

Canonical term: `HIST-BEST-RECOVERED-REFERENCE`.

Required qualifier: recovered legacy result; not canonically replayed; not an
unbiased comparator.

Historical C1-I/M1-S values are descriptive only. They are not same-protocol
baselines, cannot support paired bootstrap against V1, and cannot drive method
selection. Canonical provenance artifact:
`artifacts/evidence_closure/provenance_normalization_v1_1.json`.

# 15. Ranker limitation

| Ranker | Status |
|---|---|
| Conditional Logit | `EXECUTED` |
| XGBoost | `NOT EXECUTED — DEPENDENCY UNAVAILABLE` |
| LightGBM | `NOT EXECUTED — DEPENDENCY UNAVAILABLE` |

Unavailable rankers are not negative performance results. Optimization
evidence is limited to Conditional Logit, the six frozen representation
combinations, and lambda grid `{0.1, 1.0, 10.0}`. Canonical artifact:
`artifacts/evidence_closure/provenance_normalization_v1_1.json`.

# 16. Supported claims

The following exact claims are supported:

- Ada-RCA performs service-level ranking on RE2-OB and RE2-TT under the frozen
  task and candidate universes.
- V1 rank metrics are independently reproducible from complete frozen V1
  rankings.
- Frozen robust scaling can lose zero-baseline/post-positive Trace Error
  emergence signals.
- No explicit root/fault leakage was detected by the bounded audits.

The exact evidence and limitation for each claim are authoritative in
`docs/RCA_THESIS_CLAIM_MATRIX.md`.

# 17. Conditional claims

Only with their comparator and limitation in the same passage:

- PER-DATASET has a TT-specific positive AC@1 signal.
- Exact tested multimodal combinations provide useful development-ranking
  evidence.
- Trace Latency provides a TT development-screen signal in M+TL versus the
  metric-only-equivalent comparator.
- Aligned event-relative temporal organization outperforms the frozen
  deterministic shuffle.

# 18. Unsupported claims

The evidence does not support GLOBAL improvement, consistent PER-DATASET
Avg@5 improvement, candidate-discriminative Trace Error in frozen Z2,
universal FULL-Z2 optimality, universal candidate-relative superiority, causal
discovery, unseen-root generalization, untouched external confirmation, SOTA,
or an absolute no-label-leakage claim.

# 19. Not-tested claims

Stage-aware superiority, topology improvement, a dedicated timing/order model,
unseen-system generalization, XGBoost-versus-Conditional-Logit performance, and
LightGBM-versus-Conditional-Logit performance were not tested.

# 20. Limitations

Scientific limitations:

- Protocol Amendment V1.1 is a transparent post-audit clarification, not the
  original preregistration.
- The operational V1 synthesis and optimization reuse development benchmarks.
- There is no untouched external test or causal identification design.
- Service/telemetry fingerprint risk remains despite no explicit label leakage.

Provenance limitations:

- PER-DATASET complete candidate scores/rankings are unavailable, so full
  ranking integrity remains unauditable.
- Raw-record to derived-cell lineage is not fully auditable from committed
  canonical artifacts.
- Historical recovered evidence is descriptive and protocol-incompatible as a
  comparator.

Statistical limitations:

- Corrected intervals are conditional on fixed frozen root ranks.
- They exclude search/selection, benchmark reuse, system sampling, and method-
  development uncertainty.
- The TT Avg@5 interval includes zero; the TT AC@1 interval touches zero.

Dataset limitations:

- Evidence is limited to 90 RE2-OB and 90 RE2-TT cases in known systems with
  fixed candidate registries.
- No untouched external system and no confirmed unseen-root test are present.

Implementation/evaluation-scope limitations:

- XGBoost and LightGBM rankers were not executed.
- No topology, stage-aware, timing/order, neural, ensemble, or new sparse
  representation was executed in this freeze.
- Frozen robust scaling removes candidate-discriminative Trace Error content
  and demonstrably loses 30 OB zero-baseline/post-positive candidate-case
  signals before the feature block.

# 21. Scientific freeze boundary

No further Ada-RCA performance search is included in this scientific freeze.
The frozen method, predictions, root ranks, scores, feature artifacts,
candidate registries, root mappings, folds, and legacy artifacts remain
unchanged.

Future work is not current evidence. Any later sparse-aware representation,
new ranker, topology method, timing model, external evaluation, or new dataset
must be treated as a separate study and cannot be back-projected into this
freeze.
