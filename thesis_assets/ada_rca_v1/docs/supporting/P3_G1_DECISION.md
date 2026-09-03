# P3-G1 Morphology Signal Gate Decision

## Scope and binding

This is the preregistered P3-G1 decision for standalone RCA on RE2-OB and
RE2-TT. No external baseline is involved. The controlled variants, candidate
universe, representation, split, evaluator, and stop rule are frozen in
`docs/RCA_P3_Research_Execution_Protocol_V0.6_min.md` and
`docs/REPRESENTATION_FREEZE.md`.

The zero-model OOF predictions are bound to Ada-RCA commit
`f974c8c0bb6fe487ebcbe54b33d28276846a0708`. The fixed-seed paired bootstrap
was generated from clean source commit `092e4f37ad15b3cd6b9e01e16ed184035c258cb2`
and is stored in `artifacts/bootstrap/p3_g1_bootstrap.json`, committed in
`297cc4eec3eb039bc416576014b3c97ebe8796bc`.

Bootstrap details: 10,000 resamples, seed `20260826`, paired case-level
sampling stratified by the six fault types with 15 cases per fault.

## Headline results

| Variant | RE2-OB Avg@5 | RE2-TT Avg@5 | OB/TT mean |
|---|---:|---:|---:|
| Z1 | 0.926667 | 0.760000 | 0.843333 |
| Z3 | 0.940000 | 0.704444 | 0.822222 |
| Z3-SHUFFLE | 0.755556 | 0.442222 | 0.598889 |

The full AC@1, AC@3, Avg@5 tables and fault-separated results are preserved in
`docs/ZERO_MODEL_AUDIT.md` and the per-run `metrics.json` artifacts.

## Preregistered gate checks

1. **Mean improvement over Z1:** FAIL. The OB/TT mean delta is
   `Avg@5(Z3-Z1) = -0.021111` (`0.822222 - 0.843333`), so Z3 is not greater
   than Z1.
2. **No strong contradiction:** FAIL. RE2-TT has
   `Delta Avg@5(Z3-Z1) = -0.055556`, below the allowed `-0.02` bound.
3. **At least one positive dataset:** PASS. RE2-OB has
   `Delta Avg@5(Z3-Z1) = +0.013333`.
4. **Temporal-order falsification:** PASS. The mean delta is
   `Avg@5(Z3-Z3-SHUFFLE) = +0.223333` (`0.822222 - 0.598889`).
5. **Integrity audits:** PASS. Label firewall, path leakage, service-identity
   exclusion, split integrity, train-fold preprocessing, complete candidate
   rankings, and OOF completeness all pass.

Because checks 1 and 2 fail, the gate fails regardless of bootstrap CI
exclusion. The protocol explicitly does not permit CI significance to replace
cross-dataset consistency.

## Paired bootstrap uncertainty

| Comparison | RE2-OB point [95% CI] | RE2-TT point [95% CI] | OB/TT mean point [95% CI] |
|---|---|---|---|
| Z3 - Z1 | +0.013333 [-0.013333, +0.042222] | -0.055556 [-0.157778, +0.046667] | -0.021111 [-0.074444, +0.031111] |
| Z3 - Z3-SHUFFLE | +0.184444 [+0.124444, +0.246667] | +0.262222 [+0.157778, +0.364444] | +0.223333 [+0.163333, +0.283333] |

The positive temporal-order comparison is retained as evidence that the
trajectory ordering carries signal relative to the deterministic shuffle, but
it does not establish the required incremental improvement over Z1.

## Decision

**P3-G1 = NO-GO**

The frozen full normalized morphology trajectory does not support entry into a
neural RCA stage: it lowers the two-dataset mean Avg@5 and materially degrades
RE2-TT beyond the preregistered tolerance. This negative result is preserved.

The following are not authorized under this decision: neural models, GNN,
Transformer, topology, attention, additional datasets or baselines, threshold
changes, representation changes, split changes, or gate relaxation.

Protocol deviations: 0.

Next action: `STOPPED: MORPHOLOGY HYPOTHESIS NOT SUPPORTED`.
