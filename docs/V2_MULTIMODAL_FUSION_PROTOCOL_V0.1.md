# Ada-RCA V2 Multimodal Fusion Protocol V0.1

Status: PREREGISTERED BEFORE ANY NEW V2 PERFORMANCE RESULT  
Date: 2026-08-29  
Base commit: `bed295326e567395e725caa82840a534dcc0b1de`  
Branch: `research/multimodal-fusion-v2`  
Scope: standalone service-level RCA on RE2-OB and RE2-TT only.

## 1. Scientific boundary and selection disclosure

This protocol starts a new exploratory research line named **Ada-RCA V2 -
Low-Capacity Cross-Modal Concordance and Reliability-Aware Root Ranking**. It
does not reopen, rescue, or modify P3-G1, P4-G0, the V1 representation freeze,
the V1 final-method decision, or any historical conclusion.

V2 uses a previously inspected 180-case corpus and therefore cannot provide
untouched or independent confirmation.

The V1 method remains **Event-Relative Multimodal Morphology Ranking**: frozen
68-dimensional Z2, event-level conditional logistic ranking, train-fold-only
`StandardScaler`, L2 lambda 1.0, frozen three-fold repetition OOF, and separate
training for RE2-OB and RE2-TT. Exact replay is an integrity check, not new
performance evidence.

No V2 result may be described as state of the art, causal RCA, causal
propagation, universal, independent confirmation, unseen-root generalization,
or unseen-fault generalization. Positive, negative, null, and heterogeneous
results must all be retained.

## 2. Research questions and hypotheses

The research questions are:

1. Are the four frozen modalities descriptively complementary?
2. Does same-service cross-modal temporal concordance add ranking information
   beyond frozen Z2?
3. Does any such information survive deliberate correspondence
   misalignment?
4. Does inference-visible event telemetry reliability justify dynamic
   modality weighting?
5. After those mechanisms hold, is a six-parameter rank-1 expert interaction
   residual warranted?
6. Is there evidence in this line that would authorize a higher-capacity
   Transformer, GNN, attention model, or other rescue? The preregistered answer
   is no: none is authorized in this protocol.

The exact hypotheses are:

- **H1, cross-modal concordance:** `[Z2, XC30]` improves primary Avg@5 over Z2
  under the F1 performance gate, and aligned XC30 improves Avg@5 over a
  deliberate same-event cross-modal misalignment under the F1 mechanism gate.
  H1 is supported only when both gates pass.
- **H2, reliability-aware weighting:** after H1 passes, the fixed
  reliability-aware gated conditional ranker improves Avg@5 over F1 under the
  F2 gate without violating the AC@1 guardrail. H2 is supported only when F2
  passes.
- **H3, rank-1 expert interaction:** after H2 passes, a frozen-offset residual
  containing exactly six standardized expert-score products improves Avg@5
  over F2 under the F3 gate without violating the AC@1 guardrail. H3 is
  supported only when F3 passes.

F0 is a descriptive audit. Its outcome cannot select modalities, pairs,
features, thresholds, models, or later-stage specifications. F1 always uses all
six frozen modality pairs.

## 3. Fixed data, candidates, and folds

The only datasets are the existing 90-case RE2-OB and 90-case RE2-TT corpora.
They are evaluated separately. RE2-OB has 11 legal candidates per case and
RE2-TT has 68 legal candidates per case. Every prediction must rank the full
legal candidate registry exactly once and contain the labeled root.

The exact fold assignments are the committed files at the base commit:

| Dataset | Assignment file | SHA-256 | Fold sizes |
|---|---|---|---|
| RE2-OB | `artifacts/splits/re2ob/assignments.json` | `ca576819554ebe3d1cddd8f261bb661e7111896ff7b7dd6258e9f5daafad5195` | 30/30/30 test; 60 train per fold |
| RE2-TT | `artifacts/splits/re2tt/assignments.json` | `88b4615ed3c950569ed7e4c4e9c66a302e8f88adf1715a8457540e00390b68e7` | 30/30/30 test; 60 train per fold |

The corresponding split-manifest SHA-256 values are
`a672d12be89e91efd7fe69cdf81713b3d18482bba6b46620b0bfd0b4ff7bfd62`
for RE2-OB and
`3c3947d6377433507ca1ea6b69d88f6d8f359b42937bbcff1a7ac98422f05d7e`
for RE2-TT. Fold assignments may not be regenerated or changed.

The committed feature-manifest SHA-256 values are
`cc171f32c7642c6ddbe59b5b52bb6f8351dd8d8a35289144277900bbbb1da4ed`
for RE2-OB and
`ac0424a4018624a61e993649e2b94c678838a2d02dfc4bf8f5c1b0694a145256`
for RE2-TT. Formal runs must bind these files, the source manifests, and the
dataset tree digests already frozen by V1.

## 4. Fixed evaluation and uncertainty

The primary metric is **Avg@5**. Secondary metrics are **AC@1** and **MRR**.
Every formal table also reports AC@1, AC@3, AC@5, Avg@5, and MRR.

For each dataset and method, reports must include:

- overall case arithmetic means;
- per-fault metrics and fault macro, defined as the unweighted arithmetic mean
  over the six fixed faults `cpu`, `mem`, `disk`, `socket`, `delay`, `loss`;
- per-root metrics and root macro, defined as the unweighted arithmetic mean
  over roots present in that dataset;
- fold-level metrics for folds 0, 1, and 2;
- case-level complete ranking, candidate scores, root service, root rank,
  fault type, and fold.

All formal paired uncertainty uses failure cases as the paired unit and a
fault-stratified percentile bootstrap with exactly 10,000 resamples and seed
`20260829`. Within each dataset, every resample draws 15 cases with replacement
inside each of the six fault strata in the fixed fault order above, concatenates
the 90 sampled case deltas, and takes their arithmetic mean. A single
`numpy.random.RandomState(20260829)` stream is used; for each resample, RE2-OB
is drawn first and RE2-TT second, each with independent successive RNG draws.
The equal-dataset replicate is the arithmetic mean of that replicate's OB and
TT deltas. The 95% percentile CI is `numpy.percentile(samples, [2.5, 97.5])`
with NumPy's default linear percentile method. Point deltas are always computed
from the complete unresampled paired cases.

No pooled 180-case weighting may replace the equal-dataset arithmetic mean.
No alternative seed, bootstrap, confidence interval, metric, or aggregation
may be substituted after results are observed.

## 5. V2-G0: V1 integrity replay

Before F0 or any new V2 performance is computed, the committed V1 final-method
replay path must be executed and independently recomputed. It must reproduce:

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |

G0 requires exact candidate coverage, exact root coverage, exact fold
assignments, exact metric recomputation, V1 tests passing, and ranking identity
where the frozen replay artifact exists. The existing V1 implementation and
artifacts must not be changed to regain a match.

Any mismatch sets `V2_BASELINE_INTEGRITY_INVALID` and immediately stops V2.

## 6. V2-F0: modality complementarity audit

The fixed channel and modality order is:

1. `M` = metric;
2. `L` = log;
3. `TE` = trace-error;
4. `TL` = trace-latency.

Each modality is its existing contiguous 17-dimensional Z2 block: the frozen
eight base fields followed by the frozen nine morphology fields. F0 runs these
fixed variants with the V1 event-level conditional logit, train-only scaler,
lambda 1.0, identical folds, identical optimizer requirements, and complete
ranking:

- single: `M`, `L`, `TE`, `TL`;
- pair: `M+L`, `M+TE`, `M+TL`, `L+TE`, `L+TL`, `TE+TL`;
- leave one out: `FULL-M`, `FULL-L`, `FULL-TE`, `FULL-TL`;
- reference: `FULL-Z2`.

F0 produces a case-by-modality root-rank matrix. Pairwise single-modality
root-rank disagreement is reported for the six fixed modality pairs as signed
rank difference, absolute rank difference, nonzero-disagreement count, and
mean absolute difference. A rank-1 correction relative to FULL-Z2 is a case
where a variant has root rank 1 and FULL-Z2 has root rank greater than 1. A
family-unique rank-1 case is a case where exactly one variant within the
single, pair, or leave-one-out family has root rank 1. Leave-one-out transitions
are the per-case root-rank changes `rank(FULL-X) - rank(FULL-Z2)`, with improved,
unchanged, and degraded counts.

Modality availability is the mean frozen `channel_available` indicator and
modality coverage is the mean frozen `coverage` value. Both are reported at
candidate-row level, event-modality level using the candidate mean, and by
dataset. These quantities are descriptive only.

F0 creates `artifacts/v2/f0_modality_audit/` and
`docs/V2_F0_MODALITY_AUDIT.md`. F0 may not select the F1 pair set or alter any
later specification.

## 7. V2-F1: cross-modal concordance

### 7.1 Frozen XC30 representation

The six pair order is:

1. `M-L`;
2. `M-TE`;
3. `M-TL`;
4. `L-TE`;
5. `L-TL`;
6. `TE-TL`.

Each pair contributes exactly five fields in this order:

1. `onset_gap`;
2. `peak_gap`;
3. `centroid_gap`;
4. `post_activity_overlap`;
5. `pair_valid`.

For candidate `i` and modalities `m,n`:

- `onset_gap = abs(onset_m - onset_n) / 600` if both frozen
  `onset_missing == 0`; otherwise 1.0.
- `peak_gap = abs(peak_fraction_m - peak_fraction_n)` if both frozen
  `morphology_active == 1`; otherwise 1.0.
- `centroid_gap = abs(centroid_fraction_m - centroid_fraction_n)` if both
  frozen `morphology_active == 1`; otherwise 1.0.
- `post_activity_overlap` uses the frozen normalized trajectory `z(t)` only on
  jointly observed post-event bins 40 through 79. A bin is active when
  `z >= 0.5`. The value is Jaccard intersection over union. If the active union
  is empty, the value is 0.0.
- `pair_valid = 1.0` only when both frozen `channel_available == 1`, both
  frozen `morphology_active == 1`, and at least one jointly observed post-event
  bin exists; otherwise 0.0.

These rules always emit finite values. XC30 is exactly 6 pairs times 5 fields,
in pair-major then field-major order. F1 is `[Z2, XC30]`, exactly 98D. The
original 68D Z2 bytes/values and V1 freeze are not modified.

F1 uses the existing `src/rca/p4.py` event-level conditional-logit
implementation, lambda 1.0, the same folds, train-fold-only `StandardScaler`,
the same deterministic optimizer/convergence requirements, no tuning, and a
complete canonical-tie-broken ranking.

### 7.2 Frozen misalignment falsification

F1 has two variants: `F1-ALIGNED` and `F1-MISALIGNED`. Misalignment modifies
only the modality row correspondence used while constructing XC30. Original
Z2 remains aligned to the original candidate and unchanged.

For each event's committed canonical candidate order with `N` candidates,
metric shift is zero. For each of log, trace-error, and trace-latency, compute
SHA-256 over the exact UTF-8 seed material:

`Ada-RCA|V2-F1|20260829|<opaque_case_id>|<modality>`

Interpret the first eight digest bytes as an unsigned big-endian integer and
take modulo `N`. If the result is zero or already used by another non-metric
modality, increment it by one modulo `N` until a nonzero unused shift is found.
Modalities are resolved in fixed order `L`, `TE`, `TL`. If `N < 4`, the
integrity check fails and the experiment stops rather than changing the rule.

For XC construction at target candidate index `i`, a shifted modality with
shift `s` reads the modality row at source index `(i + s) mod N`. The complete
row, including base features, morphology fields, trajectory, and observation
mask, moves together. The original Z2 row at `i` does not move. Thus each
shifted modality preserves its within-event row multiset and candidate-marginal
information while breaking same-service cross-modal correspondence.

Tests must verify deterministic shifts, nonzero shifts, distinct non-metric
shifts, per-modality row-multiset preservation, unchanged Z2, and permutation
handling.

### 7.3 F1 gates

The formal performance comparison is `F1-ALIGNED - Z2`. `PERFORMANCE_GO`
requires all of:

1. OB Delta Avg@5 >= 0;
2. TT Delta Avg@5 >= 0;
3. at least one dataset Delta Avg@5 > 0;
4. equal-dataset mean Delta Avg@5 bootstrap 95% CI lower bound > 0;
5. OB Delta AC@1 >= -1/90 and TT Delta AC@1 >= -1/90;
6. all integrity tests pass.

The formal mechanism comparison is `F1-ALIGNED - F1-MISALIGNED`.
`MECHANISM_GO` requires OB Delta Avg@5 > 0, TT Delta Avg@5 > 0, and the
equal-dataset mean bootstrap 95% CI lower bound > 0. Integrity must also pass.

`V2_F1 = GO` only when `PERFORMANCE_GO AND MECHANISM_GO`; otherwise
`V2_F1 = NO_GO`. A mechanism failure prohibits attributing any predictive
change to cross-modal same-service temporal concordance.

F1 creates aligned, misaligned, and bootstrap artifacts plus
`docs/V2_F1_CONCORDANCE_DECISION.md`. If F1 is NO-GO, V2 stops and F2/F3 are
not implemented.

## 8. V2-F2: reliability-aware gated conditional ranker

F2 is authorized only after a committed F1 GO decision.

For event `e` and modality `m`, define inference-visible reliability:

- `A_em` is the mean frozen `channel_available` over all legal candidates;
- `C_em` is the mean frozen `coverage` over all legal candidates.

For each OOF fold and modality, means and standard deviations for A and C are
fit using training-fold events only. A zero training standard deviation maps
the standardized value to zero. Test-fold values use only those persisted
training statistics. Root, fault type, service identity, historical root
statistics, and test labels are forbidden.

The gate is frozen as the additive low-capacity form

`g_em = b_m + gamma_A * std(A_em) + gamma_C * std(C_em)`

`alpha_em = softmax_m(g_em)`.

There are exactly four modality biases `b_m` and two global slopes
`gamma_A,gamma_C`; modality-specific slopes, temperature, hidden units, and
additional reliability inputs are prohibited.

The 98 F1 features are transformed by the fold's F1 train-only scaler and
split into four 17D standardized modality blocks plus the standardized XC30
block. Define `u_eim = w_m^T z_eim` and

`score_F2(e,i) = sum_m 4 * alpha_em * u_eim + v^T XC_ei`.

The plus sign is binding: it is required by the stated F1-degeneration and
residual semantics. At initialization, `b_m = gamma_A = gamma_C = 0`, every
`alpha_em = 1/4`, each `w_m` is the corresponding 17-weight block from that
fold's fitted F1 model, and `v` is its XC30 block. Initial candidate scores and
rankings must be numerically equivalent to F1 before F2 optimization.

All 98 expert/XC weights and the six gate parameters are then optimized jointly
under the same event-level conditional likelihood with L2 lambda 1.0 applied
to every learned parameter. Initialization is deterministic and there is one
run only. The fixed optimizer is SciPy L-BFGS-B in float64 with analytic
gradient, maximum 1000 iterations, gradient infinity tolerance `1e-8`, and the
same fixed line-search settings as V1 where applicable. The gradient must pass
a finite-difference unit test. A numerical failure is documented and stops F2;
optimizer alternatives may not be selected by performance.

The formal comparison is `F2 - F1-ALIGNED` under the same bootstrap. F2 GO
requires nonnegative Avg@5 deltas on both datasets, at least one strict positive
delta, equal-dataset mean bootstrap CI lower > 0, AC@1 delta >= -1/90 on both,
and all integrity tests passing. Failure sets `V2_F2 = NO_GO`, retains F1 as
the V2 candidate, and stops before F3.

## 9. V2-F3: rank-1 expert interaction

F3 is authorized only after a committed F2 GO decision.

For each OOF fold, use the fitted F2 modality experts to calculate `u_M`,
`u_L`, `u_TE`, and `u_TL` on training-fold candidate rows. Fit one mean and
standard deviation per modality on training rows only; zero standard deviation
maps standardized scores to zero. Test rows use only the persisted training
statistics. The interaction order is exactly:

1. `uM*uL`;
2. `uM*uTE`;
3. `uM*uTL`;
4. `uL*uTE`;
5. `uL*uTL`;
6. `uTE*uTL`.

Here each factor is the corresponding standardized expert score. The fitted
F2 candidate score is a frozen offset. F3 is the additive residual

`score_F3 = score_F2 + sum_{m<n} eta_mn * u_tilde_m * u_tilde_n`.

Only the six `eta` values are trained, from all-zero initialization, using the
event-level conditional likelihood and L2 lambda 1.0. F2 parameters, expert
normalization, pair set, and pair order are frozen. No rank increase, hidden
layer, feature selection, or pair selection is allowed.

The formal comparison is `F3 - F2` under the same bootstrap and the same gate:
nonnegative Avg@5 delta on both datasets, at least one strict positive, the
equal-dataset mean CI lower > 0, AC@1 delta >= -1/90 on both, and integrity
pass. The result is `V2_F3 = GO` or `V2_F3 = NO_GO`. Regardless of the result,
V2 stops for human review after F3.

## 10. Integrity tests

The full repository test suite is mandatory. At minimum
`tests/test_v2_fusion.py` must cover:

1. Z2 remains exactly 68D;
2. V1 source and artifact integrity is unchanged;
3. XC is exactly 30D;
4. F1 is exactly 98D;
5. all XC values are finite;
6. pair order is frozen;
7. modality order is frozen;
8. missing and sentinel semantics;
9. no root, fault, or service identity enters the feature builder;
10. misalignment determinism;
11. nonzero misalignment shifts;
12. mutually distinct non-metric shifts;
13. per-modality row-multiset preservation;
14. original Z2 unchanged by misalignment;
15. complete rankings;
16. candidate permutation handling;
17. train-only scaler;
18. train-only reliability normalization;
19. F2 zero-gate initialization reproduces F1 rankings;
20. F2 analytic gradient versus finite difference;
21. F3 interaction dimension is six;
22. F3 train-only interaction normalization;
23. exact metric recomputation;
24. deterministic bootstrap;
25. label firewall.

Any integrity failure blocks a GO decision. Tests may not be weakened after a
performance result.

## 11. Required formal artifacts

Formal outputs use `artifacts/v2/` with stage-specific directories for F0,
F1 aligned, F1 misaligned, F2, F3, and bootstrap. Each formal run must persist:

- exact config and feature order;
- generating source commit;
- dataset/source/feature/split digests and fold assignments;
- scaler and every train-only normalization state;
- complete model state;
- predictions, candidate scores, complete ranking, and root rank per case;
- full metrics, fault/root/fold breakdowns, and case metrics;
- convergence diagnostics;
- runtime and environment;
- provenance and file checksums.

Aggregate-only artifacts are invalid. Artifact directories are immutable once
committed; an existing formal directory is not overwritten.

## 12. Stop rules and prohibited actions

The mandatory stops are:

- any G0 mismatch: `V2_BASELINE_INTEGRITY_INVALID`, stop before F0;
- F1 NO-GO: stop before implementing F2;
- F2 NO-GO: retain F1 and stop before implementing F3;
- after any F3 decision: `STOPPED FOR HUMAN REVIEW`.

Unfavorable, null, or heterogeneous performance never authorizes threshold
changes, alternate XC definitions, lag search, feature selection, pair
selection, hyperparameter search, random restart, optimizer selection by
performance, additional datasets, changed folds, changed metrics, or changed
gates. MLP, attention, TCN, Transformer, GNN, Graph Transformer, LambdaMART,
XGBoost, topology propagation, candidate pruning, new representations, and
all other rescue attempts are prohibited.

Numerical or implementation infeasibility must be recorded before inspecting
performance and handled only by a scientifically equivalent, explicitly
documented correction. If equivalence cannot be established without adding
researcher degrees of freedom, the stage stops.

## 13. Reporting and governance

Stage decisions are mechanical consequences of the gates above. Reports must
separate FACT, INFERENCE, and NOT SUPPORTED. They must preserve negative, null,
and heterogeneous evidence and must not use "significantly better" without the
corresponding preregistered statistical basis.

Each completed stage is committed immediately. No development occurs on main,
main is not modified, no force operation is allowed, and only
`research/multimodal-fusion-v2` may be pushed. A push or network failure is
reported without force, rewrite, or branch substitution.

Protocol deviations at freeze time: **none**. No new V2 performance was
computed before this protocol was written and committed.
