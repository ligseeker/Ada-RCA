# Ada-RCA Final Method Freeze V1.0 and Adversarial Scientific Audit

Status: **FROZEN BEFORE ANY S0/S1/S2/S3 OR NONZERO ANCHOR-SHIFT RESULT**  
Date: 2026-08-27  
Starting repository commit: `0da248cfdf26240dde90be1b9b78b981ec658d64`  
Scope: standalone service-level RCA on RE2-OB and RE2-TT only.

This protocol implements the human decision **Route A: Freeze Z2 core**. It
does not reopen P3-G1 or P4-G0. P3-G1 is `NO-GO / CLOSED`; P4-G0 is
`NO-GO / CLOSED`. Audit findings may restrict or invalidate the scientific
claim, but must never trigger method rescue.

## 1. Final method

The final method is **Ada-RCA: Event-Relative Multimodal Morphology Ranking**.
The sole authoritative representation specification is
`docs/REPRESENTATION_FREEZE.md`. Deep Research reports, prompts, summaries, and
this document may describe that representation but may not redefine it.

### 1.1 Frozen representation

The event window is `[t0 - 600 s, t0 + 600 s)`, represented by 80 half-open
15-second bins. The fixed channel order is:

1. metric;
2. log;
3. trace-error;
4. trace-latency.

Z1 contains 8 fields per channel, in this order:

1. magnitude;
2. mean impact;
3. pre/post shift;
4. onset seconds;
5. onset missing;
6. persistence;
7. coverage;
8. channel available.

Z1 is therefore 32-dimensional. Z2 appends 9 fields per channel, in this
order:

1. normalized pre mean;
2. normalized post mean;
3. normalized post-minus-pre mean;
4. post peak-time fraction;
5. post amplitude-weighted temporal centroid fraction;
6. post OLS slope;
7. mean absolute difference over adjacent observed post bins;
8. fraction of observed post bins with normalized `z >= 0.5`;
9. morphology active.

The extension is 36-dimensional and Z2 is exactly 68-dimensional. Feature
order, thresholds, sentinels, missing semantics, pre-event robust
normalization, Q90 service/channel aggregation, amplitude normalization, and
binning remain exactly as frozen and implemented for P3. No Z2 feature may be
added, removed, selected, regrouped, or reinterpreted.

### 1.2 Frozen scorer

The operational scorer is event-level conditional logistic regression. For
candidate `i` in event `e`:

`score_ei = beta^T z_ei`

`P(i | e) = exp(score_ei) / sum_j exp(score_ej)`

The scorer is scientifically equivalent to P4 `A2 = Z2-ABS` and must reuse the
existing implementation in `src/rca/p4.py`; mathematical duplication is not
authorized. Its fixed settings are:

- input: frozen Z2 only, dimension 68;
- L2 `lambda = 1.0`;
- `StandardScaler` fitted on training-fold candidate rows only;
- deterministic float64 optimization from all-zero weights;
- SciPy L-BFGS-B followed, where needed, by the already documented
  deterministic Newton polishing of the identical objective;
- final gradient infinity norm `<= 1e-8`;
- frozen three-fold OOF by repetition;
- RE2-OB and RE2-TT trained separately;
- complete legal candidate ranking with deterministic canonical candidate
  order for exact score ties;
- no service identity, fault type, topology, pruning, hyperparameter search,
  or candidate-relative transform.

Conditional logit is not a novelty claim. Its sole selection rationale is:

> RCA is an event-conditioned complete-ranking task, therefore an event-level
> conditional scorer is task-aligned.

It must not be stated that conditional logit was selected because P4 A2
produced better performance.

### 1.3 Required persisted state

Every dataset/fold must persist, rather than later reconstruct:

- scaler mean and scale;
- conditional-logit weight vector;
- feature dimension and exact feature-order identifier;
- lambda, optimizer, convergence status, loss, iteration count, and gradient
  norm;
- generating source commit;
- representation and split provenance;
- dataset tree digest/checksum;
- environment and runtime versions.

## 2. Post-selection disclosure

The final operational combination `Z2 + event-level conditional logit` was
synthesized after P3 and P4 outcomes had already been observed. P4 A2 is not an
untouched confirmation, and final replay is not a new confirmatory experiment.

> Exact replay is an identity/integrity verification, not fresh performance
> evidence.

P3 and P4 use the same 180-case RE2-OB/RE2-TT corpus. New bootstrap summaries,
fold summaries, replay artifacts, or scorer wording cannot turn Z2 into an
independent replication or untouched hypothesis.

## 3. Frozen claim boundary before audit

Candidate claims that may remain, subject to the audits below, are:

- a lightweight event-relative multimodal morphology representation;
- complete service-level root ranking;
- known-root x known-fault new-repetition evaluation on RE2-OB/TT;
- the P3 temporal-shuffle experiment indicates that aligned temporal
  organization contains RCA-relevant information;
- positive Z2-over-Z1 point-estimate direction was observed under two scoring
  formulations.

The following claims are prohibited:

- untouched confirmation of Z2;
- unseen-root, unseen-fault, or cross-system generalization;
- causal RCA or a universal temporal morphology mechanism;
- state-of-the-art performance;
- topology is unnecessary;
- full temporal trajectories are universally ineffective;
- candidate-relative information is universally useless.

The audits may only narrow this boundary.

## 4. Exact replay integrity gate

The final execution path must replay committed P4 A2 predictions on all 90
cases per dataset, with complete legal rankings and the root present. Expected
metrics are:

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |

The final rankings must be identical to committed P4 A2 and metrics must
recompute exactly. The target score condition is
`max_abs_score_difference <= 1e-12`. If a persistence or numerical serialization
effect prevents this bound while rankings remain identical, the exact cause
and observed error must be recorded; it may not be silently relaxed.

Required tests cover Z2 dimension/order/provenance, label firewall, split
integrity, complete rankings, metric recomputation, deterministic rerun,
persisted-state replay, P4 A2 ranking identity, and gradient tolerance.

Any ranking or metric mismatch sets `INTEGRITY_STATUS = INTEGRITY_INVALID` and
requires `STOP: FINAL METHOD REPLAY INVALID`. No scientific control may then
run.

## 5. Frozen adversarial controls

Exactly three RCA controls, S0/S1/S2, and one diagnostic probe, S3, are
authorized. No fourth RCA control may be added after results are seen.

### 5.1 S0: train-seen-root-set structural baseline

For each fold, define `seen_roots_train` as the unique training root labels.
Assign score 1 to a legal candidate in that set and 0 otherwise. This is a
benchmark/root-universe structural baseline, not a root-frequency prior and not
a feature-leakage baseline.

S0-A breaks score ties by frozen canonical registry order and reports all RCA
metrics. S0-B reports analytical tie-neutral expected AC@1, AC@3, AC@5,
Avg@5, and MRR under uniform ordering within each score tie group. The actual
event/fold tie-group sizes must be used; no fixed `K` may be assumed and no
Monte Carlo permutation may be used.

### 5.2 S1: observability-only RCA

S1 uses exactly 8 Z1 fields: `coverage` and `channel_available` for each of the
four frozen channels. It excludes onset missing, magnitude, mean impact,
pre/post shift, onset, persistence, and every morphology field. It uses the
same split, train-only scaler, conditional-logit objective, lambda, optimizer,
and convergence rule as the final method.

The question is how much RCA information telemetry observability/missingness
alone contains. A high result does not by itself prove label leakage,
instrumentation shortcut, or invalidity because post-event observability may be
failure-responsive. It supports only that observability structure carries
RCA-relevant information, with stable instrumentation/service fingerprint
considered jointly with S2 and S3.

### 5.3 S2: pre-event-only RCA

S2 is the primary adversarial falsification control. It may consume only
`[t0 - 600 s, t0)` and must not reuse any full-event normalized Z2/Z3 field or
active state that can read post-event information.

It reuses the frozen raw-to-q semantics: official derived telemetry inputs,
pre-event indicator robust normalization, original service/channel mapping,
and service/channel Q90 aggregation. Per channel it contains exactly:

1. `pre_mean_q`;
2. `pre_max_q`;
3. `pre_coverage = observed pre q bins / 40`;
4. `pre_available`.

S2 is exactly 16-dimensional. With no observed pre q, all four values are zero.
No pre standard deviation, quantile, trend, slope, identity, or other statistic
is allowed. The final conditional-logit split, scaler, lambda, optimizer, and
no-tuning rules apply unchanged.

The scientific question is whether stable pre-failure telemetry/service
fingerprints can reproduce final RCA ranking performance.

### 5.4 S3: service-identity probe

S3 is not an RCA baseline and does not enter the RCA gate. It uses the exact S2
16D rows to predict candidate service identity under the frozen event-level OOF
split; all rows from an event remain in one fold and scaling is train-only.

Use `sklearn.linear_model.LogisticRegression` with `penalty="l2"`, `C=1.0`,
`solver="lbfgs"`, `max_iter=5000`, `class_weight=None`, and
`fit_intercept=True`, with no hyperparameter search. The installed sklearn
version's standard multinomial-capable lbfgs behavior is used and documented;
solvers may not be tried and selected by performance.

Report top-1 accuracy, macro-F1, number of classes, empirical class
distribution, uniform reference where informative, and empirical
majority-class accuracy. High accuracy is evidence of a stable service
fingerprint, not root-label leakage. No post-result numeric thresholds may be
invented for weak/moderate/strong labels.

## 6. Frozen control statistics and states

For S0, S1, and S2, compare
`Delta_C = Avg@5(FINAL_Z2) - Avg@5(Control)` and also report `Delta_AC1`.
Use paired failure cases and a fault-stratified bootstrap with 10,000 resamples,
seed `20260827`. Resample OB and TT separately, then report each dataset and
the equal-dataset arithmetic mean with 95% percentile confidence intervals.
S0-A and analytical S0-B must be handled separately.

The descriptive state is:

- `CONTROL_SEPARATED` only if OB and TT Avg@5 point deltas are both positive
  and the equal-dataset mean bootstrap CI lower bound is positive;
- `CONTROL_OVERLAP` if the equal-dataset mean point delta is positive but the
  separation conditions are not all met;
- `CONTROL_MATCH_OR_EXCEED` if the equal-dataset mean point delta is nonpositive.

These states describe numerical comparison only; their scientific consequences
are control-specific.

### 6.1 Frozen consequence mapping

- S0 `CONTROL_MATCH_OR_EXCEED` sets
  `BENCHMARK_ROOT_UNIVERSE_DOMINANT`, severely weakens benchmark
  discrimination, and requires human scientific review after already-safe
  descriptive artifacts are completed. It does not authorize method changes.
- S1 `CONTROL_MATCH_OR_EXCEED` sets `OBSERVABILITY_SIGNAL_DOMINANT` and limits
  morphology-specific incremental interpretation. S2/S3 still run because
  they distinguish observability from pre-event fingerprint.
- S2 `CONTROL_MATCH_OR_EXCEED` sets
  `CORE_INTERPRETATION_NOT_SUPPORTED`, requires necessary records followed by
  `STOP FOR HUMAN REVIEW`, and forbids the anchor performance audit.
- S3 has no hard gate and is reported quantitatively and qualitatively only.

## 7. Separate status axes

Integrity status is exactly one of:

- `INTEGRITY_VALID`;
- `INTEGRITY_INVALID`.

It is determined by representation identity, label firewall, split integrity,
complete/root-containing rankings, exact metric recomputation, persisted model
replay, and final/P4 A2 identity. Invalid integrity stops all later work.

Scientific claim status is exactly one of:

- `SCIENTIFIC_CLAIM_RETAINED_WITH_LIMITATIONS`;
- `SCIENTIFIC_CLAIM_RESTRICTED`;
- `CORE_INTERPRETATION_NOT_SUPPORTED`.

It is limited jointly by S0, S1, S2, S3, and anchor evidence where available.
Valid implementation integrity does not establish a scientific claim.

## 8. Anchor robustness feasibility before performance

Before any nonzero shifted performance is calculated, perform a data-only
feasibility audit for offsets `-30`, `-15`, `0`, `+15`, and `+30` seconds while
retaining the full `[anchor - 600, anchor + 600)` window. Full support therefore
requires `[t0 - 630, t0 + 630)`.

The consumed sources remain the official derived `simple_metrics.csv`,
`logts.csv`, `tracets_err.csv`, and `tracets_lat.csv`. Raw metrics/logs/traces
may be used only if the already frozen preprocessing can deterministically
regenerate numerical inputs identical to delta zero without changing semantics.

For every one of 180 cases and every consumed source, record timestamp support,
derived-series coverage, reconstructability of every shifted full window, and
whether reconstruction exactly follows frozen preprocessing. This phase must
not compute shifted model performance.

No zero/edge padding, truncation, smaller offset, interpolation, shorter
window, silent source switch, unsupported-case removal, or feasible-subset
analysis is allowed. If any required offset is unavailable for any case under
frozen semantics, set
`ANCHOR_AUDIT_NOT_FEASIBLE_UNDER_FROZEN_PIPELINE`, record the reason, and skip
anchor performance. This means robustness evidence is unavailable, not that
the method failed.

## 9. Anchor identity and jitter audit

Only after feasibility passes, shifted extraction must first run delta zero.
It must reproduce final Z2 arrays exactly or with a documented floating-
equivalent difference, scores within strict tolerance, identical rankings, and
exact metrics. Failure sets `INTEGRITY_INVALID` and requires
`STOP: ANCHOR EXTRACTION PATH INVALID`.

Only when integrity remains valid, S2 has not set
`CORE_INTERPRETATION_NOT_SUPPORTED`, and feasibility passes may the jitter
audit run. Train once at original `t0`. For shifted test inputs, use the
persisted fold scaler and weights without retraining, refitting, or tuning.

For each dataset and offset, report AC@1, AC@3, AC@5, Avg@5, MRR, change from
zero, improved/degraded/unchanged root rank, and fault/root/fold breakdowns.
Use paired failure-case, fault-stratified 10,000-resample bootstrap with seed
`20260827` for each offset versus zero. No subgroup tuning is permitted.

There is no numerical hard pass margin. The descriptive summary is one of:

- `ANCHOR_ROBUST`: complete numerical evidence shows approximately null
  effects at both +/-15 seconds on OB and TT, no CI evidence of clear systematic
  degradation, and no concentrated rank collapse;
- `ANCHOR_SENSITIVITY_OBSERVED`: +/-15 seconds shows clear and consistent
  degradation;
- `ANCHOR_ROBUSTNESS_MIXED`: direction, dataset, or metric is heterogeneous.

No post-result cutoffs may be created. Full numbers control the interpretation;
the label is only a summary. +/-30 seconds is stress characterization only.

## 10. Final synthesis and stop rule

Final evidence must preserve observed positive and negative results, including
magnitude inversion, Z0 to Z1, Z3 versus Z3-SHUFFLE, exploratory Z2 signal,
positive Z2 direction under two scoring formulations, S0-S3, and anchor results
when feasible. It must preserve the closed negative conclusions:

- P3-G1 `NO-GO / CLOSED`: full amplitude-normalized trajectory plus frozen
  independent scorer did not provide stable cross-dataset gain;
- P4-G0 `NO-GO / CLOSED`: deterministic within-event feature-wise percentile
  failed the preregistered cross-dataset consistency gate.

The final operational Ada-RCA configuration was frozen after observing P3 and
P4 outcomes; therefore its reported RE2 performance is descriptive evidence
for the selected method, not a fresh confirmatory evaluation. There is no
untouched confirmation, unseen-root/fault claim, cross-system claim, causal
claim, SOTA claim, universal morphology mechanism, claim that candidate-
relative information is useless, or claim that topology is unnecessary.

Method status is:

- `FINAL_METHOD_INVALID` if integrity is invalid;
- a frozen historical implementation followed by `STOPPED FOR HUMAN
  SCIENTIFIC REVIEW` if integrity is valid but S2 sets
  `CORE_INTERPRETATION_NOT_SUPPORTED`;
- `FINAL_METHOD_IMPLEMENTATION_FROZEN` if integrity is valid and S2 does not
  negate the core interpretation. This status freezes implementation only and
  is not strong scientific confirmation.

After `docs/FINAL_METHOD_DECISION.md` is committed, the only authorized state
is `STOPPED - awaiting human review`. P5, learned or neural rescue, topology,
new transforms, new datasets, baseline reproduction, GradPaper synchronization,
thesis writing, and new method design are not authorized.

