# Ada-RCA Research Status

## Current Phase

Final Method Freeze V1.0 and adversarial scientific audit: exact replay,
S0/S1/S2, S3, and anchor feasibility are complete. All three RCA controls are
`CONTROL_SEPARATED`; S2 does not trigger `CORE_INTERPRETATION_NOT_SUPPORTED`.
S3 reports a stronger OB and weaker TT service fingerprint. Anchor feasibility
is `ANCHOR_AUDIT_NOT_FEASIBLE_UNDER_FROZEN_PIPELINE`; shifted performance is
not authorized. Final scientific status is `SCIENTIFIC_CLAIM_RESTRICTED` and
implementation status is `FINAL_METHOD_IMPLEMENTATION_FROZEN`. P3-G1 and
P4-G0 remain closed decisions.

## Frozen Protocol Version

Ada-RCA Standalone RCA Research Execution Protocol V0.6-min. The repository stores the protocol as `docs/RCA_P3_Research_Execution_Protocol_V0.6_min.md`; the requested `docs/RESEARCH_DESIGN_V0.6_MIN.md` path is absent and is treated as a filename alias only. Protocol content is not being changed.

P4-G0 Minimal Comparative Protocol V0.7 is frozen in
`docs/RCA_P4_G0_MINIMAL_COMPARATIVE_PROTOCOL_V0.7.md` before any P3-M
exploratory analysis. It preserves the P3 representation and split and freezes
the A1-A0 gate.

## Completed Gates

- Repository identity check: PASS.
- Protocol read-through: COMPLETE.
- P3-R0: PASS.
- P3-A0: PASS.
- P3-A0.5: PASS.
- P3-A1: PASS (diagnostic completed).
- P3-A2: PASS (five zero-model OOF variants and integrity checks complete).
- P3-G1: NO-GO.
- P3-G1 status: CLOSED; it is not reinterpreted by P4.
- P4-G0: PROTOCOL_FROZEN.
- P4-G0 implementation/tests: IMPLEMENTED.
- P4-G0 configs: FROZEN.
- P3-M exploratory post-mortem: COMPLETE.
- P4-G0 formal runs: COMPLETE (polished replay).
- P4-G0 bootstrap/LOSO/context diagnostics: COMPLETE.
- P4-G0 failure analysis: COMPLETE.
- P4-G0 decision: NO-GO.

## Current Blocker

No blocker for the frozen final-method audit path. No neural RCA stage or
learned comparative model is authorized. The 514 blank timestamp rows in two
RE2-OB `simple_metrics.csv` files remain explicit missingness evidence.

## Latest Experiment

The latest experiment is the frozen S0/S1/S2 adversarial control audit under
source commit `dcd1f14ebaa5b34281a04222e20ebec2e85c2a7a`. Exact replay remains
identity/integrity verification rather than fresh performance evidence.

## Latest Commit

- Latest gate decision commit: `0030111` (`decision: record P4-G0 no-go and stop`).
- Latest governance freeze commit: `c5507b9cf8394d23b648084fa9c1a5702f26182c`.
- Latest final-method replay commit: `0e3987b63b941ab37ef922447f6ad2da60e64a3c`.
- Latest audit source commit: `dcd1f14ebaa5b34281a04222e20ebec2e85c2a7a`.
- Latest diagnostic probe commit: `88e3dcf726e14256013b989add8d6fbc5183dc74`.
- Latest anchor-feasibility implementation commit: `5cc0e0747610fa93500da530aa5ffee511bde2e5`.
- Latest anchor-feasibility correction commit: `9ececc0a9d974841243ddc8a09d5980fceb8d94e`.
- Anchor performance audit: skipped under the frozen feasibility rule.
- Final evidence summary and method decision are the next and final logical stage; after their commit the round is stopped for human review.
- Current HEAD is updated by subsequent logical-stage commits; this document
  must be refreshed after each committed audit stage.

## Next Authorized Action

Continue only with the frozen final-method integrity replay and pre-frozen
S0/S1/S2/S3/anchor audits described in
`docs/RCA_FINAL_METHOD_FREEZE_V1.0.md`. Any integrity failure or frozen
scientific STOP condition ends this round. Learned comparative modeling,
method rescue, and new datasets remain unauthorized.

## Final-method audit governance

The final operational combination `Z2 + event-level conditional logit` was
synthesized after P3 and P4 outcomes were observed. Exact replay is an
identity/integrity verification, not fresh performance evidence. P3 and P4
share the same 180-case RE2-OB/RE2-TT corpus. The foreign-context diagnostic
limitation is recorded in `docs/P4_CONTEXT_DIAGNOSTIC_LIMITATION.md`; it does
not alter P4-G0.

## Decision Log

### 2026-08-27 — P4-G0 minimal comparative protocol freeze

- Frozen Rule: Test A1-A0 as the sole primary H2 comparison using the frozen
  Z1 evidence, deterministic within-event feature-wise percentiles, identical
  event-level conditional-logit scorers, lambda 1.0, frozen repetition OOF,
  and the preregistered five-condition gate plus integrity checks.
- New Evidence: No P4 performance result and no new P3 post-mortem result was
  inspected before this freeze. Repository audit found a clean `main` worktree
  at `e5103bdb1be648bcda1d54ad91f387dc29a7a68e`; frozen OB/TT inputs, features,
  splits, predictions, and audits are present and consistent with governance.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: P4 implementation may proceed. P3-G1 remains
  `NO-GO / CLOSED`; P4 cannot retroactively rescue it.

### 2026-08-27 — P4-G0 implementation and config freeze

- Frozen Rule: Use only A0/A1/A2/A3 with dimensions 32/64/68/136, the sole
  within-event percentile transform, train-fold-only scaling, lambda 1.0,
  float64 zero-initialized SciPy L-BFGS-B, tolerance 1e-8, max_iter 1000, and
  the frozen P3 repetition split.
- New Evidence: The full repository suite passes 37 tests. No formal P4 result
  or new P3-M result was inspected before the implementation/config freeze.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: P3-M is now authorized as exploratory analysis, but
  cannot modify P4 scientific design, implementation, or configs.

### 2026-08-27 — P3-M exploratory post-mortem

- Frozen Rule: Analyze only committed P3 Z1/Z2/Z3 predictions, frozen MI
  membership, and frozen feature coverage after all P4 freeze commits.
- New Evidence: Z2-Z1 Avg@5 is +0.026667 on OB with 95% CI approximately
  [0, 0.057778] and +0.086667 on TT with CI [0.020000, 0.157778]. Fault, root,
  fold, MI, transition, and coverage results are heterogeneous and explicitly
  exploratory.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: No P4 rule or implementation changes. P3-G1 remains
  `NO-GO / CLOSED`; Z2 is not new untouched confirmatory evidence.

### 2026-08-27 — P4-G0 formal runs and diagnostics

- Frozen Rule: Run all A0/A1/A2/A3 variants separately on RE2-OB and RE2-TT,
  then use the fixed paired fault-stratified case bootstrap, LOSO, and
  foreign-context diagnostics.
- New Evidence: Polished runs are complete with exact metric recomputation,
  complete rankings, checksums, replay equality, and all fold gradients at or
  below `1e-8`. Primary Avg@5 deltas are `-0.004444` (OB) and `+0.066667`
  (TT); mean `+0.031111`, bootstrap 95% CI `[+0.001111,+0.062222]`.
- Why Current Rule Is Invalid/Infeasible: Initial optimizer stopping required
  the documented deterministic Newton-polishing deviation; no scientific
  design was changed.
- Proposed Revision: None.
- Scientific Consequence: Final gate evaluation must mark OB positivity as
  failed despite positive mean bootstrap evidence. Decision remains pending
  failure analysis and must not rescue the cross-dataset condition.

### 2026-08-27 — P4-G0 decision

- Frozen Rule: P4-G0 PASS requires OB and TT A1-A0 Avg@5 deltas both positive,
  mean delta at least +0.01, both AC@1 guardrails, positive mean bootstrap CI
  lower bound, and all integrity checks.
- New Evidence: OB A1-A0 Avg@5 is `-0.004444`; TT is `+0.066667`; mean is
  `+0.031111` with bootstrap CI `[+0.001111,+0.062222]`. Integrity is PASS.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: Condition 1 fails; P4-G0 is `NO-GO`. H2 is not
  supported by this minimal comparative test. The current route stops without
  rescue or learned comparative implementation.

### 2026-08-26 — Governance initialization

- Frozen Rule: V0.6-min governs standalone RCA; only RE2-OB and RE2-TT are in scope.
- New Evidence: The repository protocol filename is `RCA_P3_Research_Execution_Protocol_V0.6_min.md`, not `RESEARCH_DESIGN_V0.6_MIN.md`; RE2-TT is nested under `datasets/RCAEval/RE2/RE2-TT`.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible; both differences are local naming/layout issues.
- Proposed Revision: None. Resolve through documented path aliases.
- Scientific Consequence: None.

### 2026-08-26 — P3-R0 benchmark compatibility

- Frozen Rule: RE2-OB and RE2-TT must each provide 90 service-level RCA cases, reliable root/fault/t0 semantics, complete metrics/logs/traces, and RCAEval-aligned AC@1/3/5 and Avg@5.
- New Evidence: Both datasets provide 90/90 valid cases, 720/720 required files, strict 5-root × 6-fault × 3-repetition balance, and complete label-free candidate registries. The content tree digests are `ce48691243bcf4871abaedc49d5c7ffe45d51f66dcf669fec3da54e0aa60df8a` (OB) and `84b26bcd083cea2db5c7d46330974c23d9ef963ed586ec9325c663baa5dd0958` (TT). RCAEval checkout HEAD is `5e96b700445bfb5c599e505ecf37d53bf847bbeb`; its dirty diff digest is `24fd630537aee9daec7ca907e68360b6616046989b79d6c25d32e83021291320`. Two OB metric files contain 514 blank timestamp rows.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible. Blank timestamps are representable through explicit masks.
- Proposed Revision: None.
- Scientific Consequence: P3-R0 passes; P3-A0 is authorized. No morphology result has been inspected.

### 2026-08-26 — P3-A0 data and leakage firewall

- Frozen Rule: Inputs and labels must be physically separated; candidate registries must be label-free and complete; no path, root, or fault token may enter prediction-visible data.
- New Evidence: OB and TT manifests each contain 90 unique inputs, labels, and source records; registry sizes are 11 and 68; all candidate sets are complete and stable; forbidden input token hits are zero; root-in-registry violations are zero.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: P3-A0 data/leakage portion passes.

### 2026-08-26 — P3-A0 split freeze

- Frozen Rule: Each dataset uses independent fixed 3-fold OOF; every root × fault stratum contributes repetition 1/2/3 to fold 0/1/2.
- New Evidence: Both datasets have 30 test and 60 train cases per fold, with all 30 root × fault strata represented exactly once in every test fold. Main manifests are `artifacts/splits/re2ob_3fold.json` and `artifacts/splits/re2tt_3fold.json`.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: Split is frozen before any morphology performance experiment.

### 2026-08-26 — P3-A0.5 representation freeze

- Frozen Rule: Use the committed event-relative representation in `docs/REPRESENTATION_FREEZE.md`; no post-result representation changes are allowed.
- New Evidence: The local derived telemetry supports the four fixed channels, 1-second metrics and 15-second log/trace grids, with explicit malformed/missing timestamp masks.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: P3-A1 and P3-A2 are authorized under the fixed representation.

### 2026-08-26 — P3-A0.5 full representation extraction

- Frozen Rule: Extract only the committed label-free event-relative representation; no labels or paths may enter the feature pipeline.
- New Evidence: OB and TT each produced 90 finite feature artifacts. Mean observed q-bin ratios are 0.5441 (OB) and 0.3542 (TT); mean available-channel ratios are 0.5482 and 0.3543. Z3 shape is 676 flattened fields per candidate.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: P3-A1 magnitude inversion is authorized; no model result has been inspected.

### 2026-08-26 — P3-A1 magnitude inversion

- Frozen Rule: Rank by the label-free frozen `A_i`; report MI-1/MI-3 overall and by all six fault types.
- New Evidence: OB has MI-1 66/90 (0.7333) and MI-3 25/90 (0.2778). TT has MI-1 90/90 (1.0000) and MI-3 85/90 (0.9444). Complete root-rank distributions are preserved in `artifacts/audits/magnitude_inversion.json`.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: Frozen magnitude alone often does not place the root first, especially in TT. This diagnostic does not establish that morphology helps; P3-A2 is required.

### 2026-08-26 — P3-A2 zero-model OOF runs

- Frozen Rule: Run only Z0, Z1, Z2, Z3, and Z3-SHUFFLE with fixed L2 logistic regression and train-fold-only scaling.
- New Evidence: All 10 dataset×variant runs produced 90/90 unique OOF predictions and complete rankings. Z3 Avg@5 is 0.9400 (OB) and 0.7044 (TT); Z1 is 0.9267 (OB) and 0.7600 (TT). Z3-SHUFFLE is 0.7556 (OB) and 0.4422 (TT).
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible.
- Proposed Revision: None.
- Scientific Consequence: The preregistered gate comparison is mixed before uncertainty analysis; bootstrap is mandatory and no neural model is authorized yet.

### 2026-08-26 — P3-G1 morphology signal gate

- Frozen Rule: P3-G1 requires the OB/TT mean `Avg@5(Z3)` to exceed `Avg@5(Z1)`, neither dataset may fall below a `-0.02` Z3-minus-Z1 delta, at least one dataset must improve, the mean Z3 score must exceed Z3-SHUFFLE, and all integrity audits must pass.
- New Evidence: Z3-minus-Z1 is `+0.013333` on OB, `-0.055556` on TT, and `-0.021111` on the OB/TT mean. Z3-minus-Z3-SHUFFLE is `+0.184444` on OB, `+0.262222` on TT, and `+0.223333` on the mean. The 10,000-resample fixed-seed paired bootstrap is stored in `artifacts/bootstrap/p3_g1_bootstrap.json`.
- Why Current Rule Is Invalid/Infeasible: It is not invalid or infeasible. The preregistered gate is directly evaluable and produces a negative result.
- Proposed Revision: None.
- Scientific Consequence: P3-G1 is NO-GO. The morphology route stops; no neural RCA implementation is authorized.
