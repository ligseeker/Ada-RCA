# Final Ada-RCA Method Replay Audit

Status: **INTEGRITY_VALID**  
Generating source commit: `8e2667e98fdea4a792113dbff2dd8f960ba4edad`  
Purpose: identity/integrity verification only; not fresh performance evidence.

## Frozen identity

The replay uses the 68-dimensional frozen Z2 representation from
`docs/REPRESENTATION_FREEZE.md`, the frozen repetition-based three-fold OOF
split, train-fold-only `StandardScaler`, and the existing event-level
conditional-logit implementation with lambda 1.0. The feature-order SHA-256 is
`0acf244e629a5e62e3cca82f33f01cd25157ffaf2843f985b46755b615637dfa`.

Each dataset/fold now persists float64 scaler means, scaler scales, and weights
plus convergence, gradient, representation, split, dataset-tree, source-commit,
runtime, and environment provenance. Persisted state is checksum-bound and can
be used directly without deterministic reconstruction.

## Replay results

| Dataset | Cases | AC@1 | AC@3 | AC@5 | Avg@5 | MRR | P4 A2 ranking | Max score error |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| RE2-OB | 90/90 | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 | identical | 0.0 |
| RE2-TT | 90/90 | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 | identical | 0.0 |

The machine recomputation uses full float64 values. The prompt's rounded TT MRR
`0.8034718882` differs from the full recomputed value
`0.8034718881941106` only by decimal display rounding; fit, persisted-state
replay, and committed P4 A2 predictions have zero score difference and exact
ranking identity.

Maximum gradient infinity norms are:

- RE2-OB: `3.4139358007223564e-14`;
- RE2-TT: `1.4144241333724494e-13`.

All six folds converged and satisfy the frozen `1e-8` tolerance. Rankings are
complete, unique, root-containing, and cover all legal candidates.

## Integrity checks

The replay test suite covers:

- Z2 dimension 68 and exact feature order;
- representation, split, and dataset provenance;
- absence of label/service-identity fields from feature names;
- 60/30 train/test case separation in each fold;
- complete legal rankings and root presence;
- exact metric recomputation;
- deterministic conditional-logit behavior;
- checksum-bound persisted model-state reload;
- persisted-state and fresh-fit identity with committed P4 A2;
- gradient tolerance.

Conclusion: `INTEGRITY_VALID`. This conclusion authorizes the pre-frozen
scientific controls; it does not confirm the morphology interpretation.

