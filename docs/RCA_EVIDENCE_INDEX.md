# Ada-RCA Evidence Index

This is the canonical navigation entrypoint for Ada-RCA scientific and thesis
evidence. The terminal evidence decision is
`RCA_FREEZE_READY_WITH_LIMITATION`. Read the final freeze and claim matrix
before reusing any result.

## CANONICAL CURRENT EVIDENCE

- [`RCA_FINAL_SCIENTIFIC_FREEZE_V1.md`](RCA_FINAL_SCIENTIFIC_FREEZE_V1.md):
  frozen V1 method, reproduced metrics, evidence boundary, limitations, and
  terminal scientific decision.
- [`RCA_THESIS_RESULTS_PACKAGE.md`](RCA_THESIS_RESULTS_PACKAGE.md):
  thesis-facing task, protocol, results, negative evidence, safe wording, and
  limitations.
- [`RCA_THESIS_CLAIM_MATRIX.md`](RCA_THESIS_CLAIM_MATRIX.md): exact status,
  evidence class, comparator, artifact, and limitation for every thesis claim.
- [`BOOTSTRAP_FORENSIC_AUDIT.md`](BOOTSTRAP_FORENSIC_AUDIT.md): canonical
  correction of bootstrap direction, estimator reproducibility, and thesis-use
  boundary.
- [`TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md`](TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md):
  candidate-case modality funnel and Trace Error robust-scale information-loss
  mechanism.
- [`TRACE_ERROR_REPRESENTATION_INVARIANT.md`](TRACE_ERROR_REPRESENTATION_INVARIANT.md):
  read-only proof of the frozen 17D Trace Error block's exact contribution.
- [`EVIDENCE_ERRATA.md`](EVIDENCE_ERRATA.md): canonical corrections and
  supersession notices.

Canonical interpretation and machine-readable decision layers:

- [`EVIDENCE_LEVEL_SEMANTIC_CORRECTION.md`](EVIDENCE_LEVEL_SEMANTIC_CORRECTION.md)
  and `artifacts/evidence_closure/evidence_semantic_correction_v1_1.json`;
- `artifacts/evidence_closure/final_decision_v1_1.json`;
- `artifacts/evidence_closure/metric_reconstruction_v1_1.json`;
- `artifacts/evidence_closure/bootstrap_corrected_v1_1.json`;
- `artifacts/evidence_closure/telemetry_information_loss_v1_1.json`;
- `artifacts/evidence_closure/trace_error_representation_invariant.json`; and
- `artifacts/evidence_closure/provenance_normalization_v1_1.json`.

The protocol chain remains part of the canonical audit trail:

- [`RCA_EVIDENCE_CLOSURE_PROTOCOL.md`](RCA_EVIDENCE_CLOSURE_PROTOCOL.md);
- [`RCA_EVIDENCE_CLOSURE_PROTOCOL_AMENDMENT_V1_1.md`](RCA_EVIDENCE_CLOSURE_PROTOCOL_AMENDMENT_V1_1.md);
- [`INDEPENDENT_METRIC_RECONSTRUCTION_V1_1.md`](INDEPENDENT_METRIC_RECONSTRUCTION_V1_1.md); and
- [`BOOTSTRAP_FORENSIC_AUDIT.md`](BOOTSTRAP_FORENSIC_AUDIT.md).

## HISTORICAL / SUPERSEDED

- [`OPT_FINAL_EVIDENCE_SUMMARY.md`](OPT_FINAL_EVIDENCE_SUMMARY.md) is a legacy
  optimization summary. Its bootstrap intervals are superseded, its historical
  terminology is superseded, and it must not be used as canonical thesis
  evidence. Use the corrected bootstrap artifact, final freeze, and claim
  matrix above.
- [`RCA_EVIDENCE_CLOSURE_FAILURE.md`](RCA_EVIDENCE_CLOSURE_FAILURE.md) preserves
  the immutable Gate 0 failure. The later post-audit Protocol Amendment V1.1
  separates complete-ranking integrity from root-rank metric sufficiency. The
  failure report remains immutable history and is not silently rewritten into
  a pass.

Other P3, P4, optimization, post-mortem, and recovered historical documents are
retained as development or historical evidence. They do not override the
current freeze, corrected bootstrap, semantic correction, or claim matrix.

## Use boundary

- Use only artifacts named by the exact claim and comparator.
- Do not treat `NOT_AUDITABLE` as either `PASS` or `FAIL`.
- Do not turn unavailable rankers into negative results.
- Do not present recovered historical scores as same-protocol baselines.
- Do not infer absence of shortcuts from the bounded no-explicit-leakage audit.
- Do not extend current evidence to SOTA, causal discovery, unseen systems,
  unseen roots, or untouched external confirmation.

No further Ada-RCA performance search is included in this scientific freeze.
