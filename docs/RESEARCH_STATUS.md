# Ada-RCA Research Status

## Current Phase

P3-A2 bootstrap comparisons and P3-G1 decision.

## Frozen Protocol Version

Ada-RCA Standalone RCA Research Execution Protocol V0.6-min. The repository stores the protocol as `docs/RCA_P3_Research_Execution_Protocol_V0.6_min.md`; the requested `docs/RESEARCH_DESIGN_V0.6_MIN.md` path is absent and is treated as a filename alias only. Protocol content is not being changed.

## Completed Gates

- Repository identity check: PASS.
- Protocol read-through: COMPLETE.
- P3-R0: PASS.
- P3-A0: PASS.
- P3-A0.5: PASS.
- P3-A1: PASS (diagnostic completed).
- P3-A2: RUNS COMPLETE; bootstrap pending.
- P3-G1: NOT STARTED.

## Current Blocker

None. P3-R0, P3-A0, and P3-A0.5 passed. The 514 blank timestamp rows in two RE2-OB `simple_metrics.csv` files remain explicit missingness evidence.

## Latest Experiment

P3-A2 five zero-model OOF variants, generated from commit `f974c8c0bb6fe487ebcbe54b33d28276846a0708`; bootstrap and P3-G1 gate are pending.

## Latest Commit

Latest completed experiment commit: `f974c8c0bb6fe487ebcbe54b33d28276846a0708`; MI audit commit: `650b59d90d0cc5baefadc80f8c8dc80d778fe84c`.

## Next Authorized Action

Run fixed-seed 10,000-resample paired bootstrap for Z3−Z1 and Z3−Z3-SHUFFLE, then apply P3-G1 exactly.

## Decision Log

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
