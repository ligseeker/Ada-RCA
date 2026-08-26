# Ada-RCA Research Status

## Current Phase

P3-A0 data, candidate-universe, split, and leakage audit.

## Frozen Protocol Version

Ada-RCA Standalone RCA Research Execution Protocol V0.6-min. The repository stores the protocol as `docs/RCA_P3_Research_Execution_Protocol_V0.6_min.md`; the requested `docs/RESEARCH_DESIGN_V0.6_MIN.md` path is absent and is treated as a filename alias only. Protocol content is not being changed.

## Completed Gates

- Repository identity check: PASS.
- Protocol read-through: COMPLETE.
- P3-R0: PASS.
- P3-A0: NOT STARTED.
- P3-A0.5: NOT STARTED.
- P3-A1: NOT STARTED.
- P3-A2: NOT STARTED.
- P3-G1: NOT STARTED.

## Current Blocker

None. P3-R0 found 514 blank timestamp rows in two RE2-OB `simple_metrics.csv` files. They are preserved as missingness evidence and do not prevent reliable case labels, t0, candidates, or tri-modal access.

## Latest Experiment

P3-R0 formal compatibility audit, generated from Ada-RCA commit `04a9bdf8474cb024a4c365ab4ba5d12e6e91549c`. This is a data/evaluator audit, not a performance experiment.

## Latest Commit

Audit implementation commit: `04a9bdf8474cb024a4c365ab4ba5d12e6e91549c`.

## Next Authorized Action

Complete P3-A0 label-separated manifests, canonical service registries, frozen 3-fold OOF splits, and leakage tests.

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
