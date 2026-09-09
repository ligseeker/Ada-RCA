# Ada-RCA reproduction notes

## Reproduction contract

The final method is the frozen 68-dimensional Z2 representation with an event-level conditional-logit ranker. Reproduction must preserve all of the following:

- the two datasets are evaluated separately;
- each dataset contains 90 cases and three 30-case test folds;
- the scaler is fitted only on candidate rows from the training folds;
- the model uses float64, zero initialization, L2 `lambda=1.0`, L-BFGS-B, and deterministic Newton polishing;
- every prediction is a complete permutation of the legal candidate registry;
- fold states satisfy gradient infinity norm `<=1e-8`;
- rankings must equal the committed P4-A2 reference rankings;
- the strict reference score tolerance remains `1e-12`.

The implementation must fail closed when these checks do not hold. A ranking or metric mismatch must not be converted into a successful reproduction.

## Retained artifacts

Only artifacts required to execute or verify the final method are retained:

| Path | Role |
|---|---|
| `artifacts/source/<dataset>/` | frozen inputs, label sidecar, source references, service registry, and manifest |
| `artifacts/features/<dataset>/` | 90 per-case feature archives and their manifest |
| `artifacts/splits/<dataset>/` | assignments, fold membership, and split manifest |
| `artifacts/p4_g0/predictions/a2/<dataset>/` | immutable reference predictions and provenance used for identity checks |
| `artifacts/final_method/<dataset>/` | persisted fold state, predictions, metrics, checksums, and replay audit |

Development-stage Z0/Z1/Z3 runs, candidate-relative variants, postmortems, controls, diagnostics, external baselines, and thesis packaging are intentionally excluded from this streamlined method branch. Their Git history remains recoverable from the pre-cleanup commit.

## Validation commands

Run the complete retained test suite from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

Run a fresh fit and exact identity check without overwriting committed artifacts:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/run_final_method.py --dataset re2ob
PYTHONDONTWRITEBYTECODE=1 python scripts/run_final_method.py --dataset re2tt
```

Delete or move the corresponding ignored output directory before repeating a run. The script refuses to overwrite an existing result directory.

## Numerical portability limitation

The committed reference artifacts were produced under Python 3.8.20, NumPy 1.24.1, pandas 1.5.3, SciPy 1.10.1, and scikit-learn 1.2.1. Persisted-state replay and metric reconstruction are deterministic under the retained tests.

A fresh RE2-TT fit can be sensitive at the final floating-point identity boundary across numerical-library or BLAS builds. During the cleanup audit, rankings remained identical but the maximum absolute score difference was `1.2008172234345693e-12`, slightly above the frozen `1e-12` threshold. The run therefore correctly stopped with `STOP: FINAL METHOD REPLAY INVALID`. This is a score-level numerical portability limitation, not permission to relax the threshold or claim a successful exact replay.

## Evidence boundary

The final configuration was selected after internal P3/P4 outcomes had been observed. The committed replay verifies implementation identity; it is not a fresh confirmatory experiment. Results are limited to RE2-OB and RE2-TT under the retained candidate registries, folds, and known-root × known-fault new-repetition setup.
