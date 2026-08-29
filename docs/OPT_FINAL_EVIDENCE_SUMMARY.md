# Final Optimization Evidence Summary

## Final comparison

| Method | OB AC@1 | OB Avg@5 | OB MRR | TT AC@1 | TT Avg@5 | TT MRR | Mean AC@1 | Mean Avg@5 | Mean MRR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| V1-SCIENTIFIC | .8778 | .9622 | .9315 | .7111 | .8511 | .8035 | .7944 | .9067 | .8675 |
| HIST-BEST-REPLAYED-REFERENCE | .9778 | .9956 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| GLOBAL-OPT | .8778 | .9622 | .9315 | .7111 | .8511 | .8035 | .7944 | .9067 | .8675 |
| PER-DATASET-OPT | .8556 | .9511 | .9157 | .7889 | .8578 | .8392 | .8222 | .9044 | .8775 |

The historical row is post-hoc descriptive reference, not an unbiased
comparator. The nested rows are development-controlled nested OOF estimates,
not untouched external generalization estimates.

## Pareto view

V1/GLOBAL has Avg@5 `0.9067`, AC@1 `0.7944`; PER-DATASET has Avg@5 `0.9044`,
AC@1 `0.8222`. The mean Avg@5 difference is `-0.0022`, within the practical
equivalence threshold `1/90 = 0.0111`, while AC@1 is higher for PER-DATASET.
Dataset-level trade-off remains material: OB decreases and TT increases.

## Shortcut and leakage audit

Feature names contain no root/fault/service identity tokens. Candidate sets and
tie order are canonical and complete. StandardScaler is fitted inside each
outer-train fit; inner and outer event IDs are disjoint. Stable service-specific
coverage/availability patterns may still act as telemetry fingerprints, so the
result is not evidence of pure causal morphology. Fault type is diagnostic only.

## Negative results

The shared-family track did not improve V1. Dataset-specific selection improved
TT but reduced OB and did not improve equal-dataset Avg@5. Tree rankers and
ensembles were unavailable, not silently replaced. No rescue search was run.
