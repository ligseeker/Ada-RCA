# Ada-RCA Research Status

## Current Phase

P3-A1 magnitude-inversion audit.

## Frozen Protocol Version

Ada-RCA Standalone RCA Research Execution Protocol V0.6-min. The repository stores the protocol as `docs/RCA_P3_Research_Execution_Protocol_V0.6_min.md`; the requested `docs/RESEARCH_DESIGN_V0.6_MIN.md` path is absent and is treated as a filename alias only. Protocol content is not being changed.

## Completed Gates

- Repository identity check: PASS.
- Protocol read-through: COMPLETE.
- P3-R0: PASS.
- P3-A0: PASS.
- P3-A0.5: PASS.
- P3-A1: NOT STARTED.
- P3-A2: NOT STARTED.
- P3-G1: NOT STARTED.

## Current Blocker

None. P3-R0, P3-A0, and P3-A0.5 passed. The 514 blank timestamp rows in two RE2-OB `simple_metrics.csv` files remain explicit missingness evidence.

## Latest Experiment

P3-A0.5 full feature extraction, generated from commit `19a463cdc138083b38d3a8fe042e03cb73bbf4d1`; OB/TT each 90 cases and all arrays finite. No ranking performance result has been generated.

## Latest Commit

Latest completed audit commit: `19a463cdc138083b38d3a8fe042e03cb73bbf4d1`; representation freeze commit: `7cd6d418a114978b33838e788346febbeae71818`; split implementation commit: `ca4a49b103fe5e688bb9e8f27756e5944fab3f51`.

## Next Authorized Action

Run the frozen, label-free magnitude-inversion audit and preserve all MI-1/MI-3 cases.

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
