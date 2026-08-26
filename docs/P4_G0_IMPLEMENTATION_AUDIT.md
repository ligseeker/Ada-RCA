# P4-G0 Implementation Audit

Status: IMPLEMENTED; FORMAL P4 RESULTS NOT RUN.

Implementation is bound to
`docs/RCA_P4_G0_MINIMAL_COMPARATIVE_PROTOCOL_V0.7.md` and reuses the frozen P3
feature artifacts and split manifests without modification.

## Implemented controls

- `src/rca/p4.py` implements feature-wise within-event ascending average-rank
  percentiles, concatenation after frozen raw Z1/Z2 extraction and before
  scaling, deterministic event-level conditional logit, analytic gradient,
  float64 zero initialization, L2 lambda 1.0, SciPy L-BFGS-B, and complete
  candidate ranking.
- The percentile builder accepts only a finite candidate feature matrix. It has
  no label/root/fault parameter or dependency.
- `StandardScaler` is fit only on concatenated training-event candidate rows in
  each frozen OOF fold. Conditional-logit loss is summed by event and uses one
  root index per event; candidate rows are not treated as independent
  statistical units.
- Score ties use stable candidate identity only. Candidate permutation followed
  by identity alignment preserves percentiles, scores, and ranking.
- `src/rca/p4_stats.py` fixes evaluation, factorial effects, gate arithmetic,
  and paired fault-stratified case bootstrap interfaces.
- `scripts/run_p4_g0.py` loads only frozen NPZ features and frozen assignments,
  persists label-free model-input provenance separately from evaluation
  predictions, and records runtime/environment/checksums.

## Required tests

The following protocol-required modules are present:

- `tests/test_p4_percentile_context.py`
- `tests/test_p4_candidate_permutation.py`
- `tests/test_p4_label_firewall.py`
- `tests/test_p4_conditional_logit.py`
- `tests/test_p4_gradient.py`
- `tests/test_p4_event_batching.py`
- `tests/test_p4_split_integrity.py`
- `tests/test_p4_prediction_completeness.py`
- `tests/test_p4_metric_recompute.py`
- `tests/test_p4_determinism.py`

The full repository suite passes 37 tests. Covered invariants include
percentile bounds/ties, no-label construction, numerical gradient and L2 term,
softmax normalization, synthetic root recovery, loss decrease, event batching,
frozen split integrity, complete/unique/root-containing rankings, metric
recomputation, permutation equivariance, and strict deterministic rerun equality.

## Scientific boundary

No P4-G0 dataset result and no new P3-M post-mortem result was generated or
inspected during implementation. Config freeze remains a separate commit and
must complete before P3-M.
