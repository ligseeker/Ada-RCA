# Ada-RCA Final Method Decision

Date: 2026-08-27  
Decision scope: Route-A Z2 freeze and adversarial scientific audit on RE2-OB/TT.

## Integrity

**`INTEGRITY_VALID`**

Evidence:

- final Z2 dimension is 68 with exact frozen feature order and provenance;
- Label Firewall and prediction-visible input separation pass;
- frozen 3-fold split integrity passes with 60 train / 30 test cases per fold;
- all 180 final replay cases have complete, unique, legal, root-containing
  rankings;
- persisted scaler means/scales and conditional-logit weights reload directly;
- persisted-state predictions have identical rankings to committed P4 A2 and
  `max_abs_score_difference = 0.0` on both datasets;
- exact metric recomputation matches the committed expected metrics;
- all folds converge with gradient infinity norm `<=1e-8`;
- full repository test suite passes 56/56 at the final audit state;
- S2 pre-event extraction is independently checked against frozen pre-bin q
  values and contains no post-event information;
- anchor performance was not run because its feasibility prerequisite failed.

No integrity failure occurred. The ULP-aware Newton polishing change is a
disclosed numerical deviation preserving the same objective, lambda, scaler,
split, and feature semantics.

## Scientific interpretation

**`SCIENTIFIC_CLAIM_RESTRICTED`**

Reasons:

1. S0-A/S0-B, S1, and S2 are all `CONTROL_SEPARATED`, so the final method
   exceeds the tested structural, observability-only, and exact pre-event-only
   controls on both datasets. S2 does **not** trigger
   `CORE_INTERPRETATION_NOT_SUPPORTED`.
2. S3 shows a strong OB and weaker TT service-identity signal from the exact
   pre-event S2 representation. This is stable service-fingerprint evidence,
   not root-label leakage, but it limits a morphology-specific attribution of
   the selected method's performance.
3. Anchor robustness evidence is unavailable because the frozen derived-data
   pipeline cannot support every required shifted full window. This is not a
   method failure, but it prevents a robustness claim.
4. P3-G1 and P4-G0 are both closed negative gates. The observed Z2-positive
   direction is post-selection descriptive evidence, not untouched confirmation.

The restricted status therefore permits a narrow historical/operational
description while prohibiting a strong causal or universal morphology claim.

## Method status

**`FINAL_METHOD_IMPLEMENTATION_FROZEN`**

The implementation and representation are frozen as a historical artifact. This
status does not mean that a strong scientific claim has been confirmed. Because
integrity is valid and S2 did not match or exceed the final method, the frozen
protocol does not require `FINAL_METHOD_INVALID` or `STOPPED FOR HUMAN
SCIENTIFIC REVIEW` on the S2 core-interpretation rule. Human review is still
required before any thesis or next-stage interpretation.

## Exact claim boundary

### Currently supportable, narrowly

- A lightweight event-relative multimodal morphology representation can be
  implemented as a complete service-level root-ranking pipeline.
- On known-root x known-fault new-repetition evaluation on RE2-OB and RE2-TT,
  the selected frozen Z2 + event-level conditional-logit implementation
  produced the replayed descriptive metrics recorded in the evidence summary.
- P3 temporal shuffling indicates that aligned temporal organization contains
  RCA-relevant information relative to the tested deterministic shuffle.
- Under this corpus and protocol, final Z2 separates from the tested S0/S1/S2
  controls.

### Restricted or requiring qualification

- Any morphology-specific incremental interpretation must acknowledge the
  post-selection synthesis, the same P3/P4 corpus, the strong OB pre-event
  service fingerprint, and unavailable anchor robustness evidence.
- Z2-over-Z1 positive direction may be reported only as observed descriptive
  evidence under two scoring formulations, never as untouched confirmation.
- Observability and pre-event structure carry RCA-relevant information, but
  neither result alone establishes leakage or invalidates the implementation.

### Prohibited

- untouched confirmation or independent replication of Z2;
- unseen-root, unseen-fault, or cross-system generalization claims;
- causal RCA, SOTA, or universal morphology-mechanism claims;
- claims that topology is unnecessary;
- claims that full trajectories are universally ineffective;
- claims that candidate-relative information is universally useless;
- P5 temporal relation, learned comparative rescue, topology/GNN/Transformer/
  attention models, new transforms, feature selection, new datasets, or
  external-baseline reproduction.

## Final state

**`STOPPED — awaiting human review`**

After this decision document is committed, no baseline reproduction,
benchmark-comparison design, GradPaper synchronization, thesis writing, or new
method design is authorized in this round.

