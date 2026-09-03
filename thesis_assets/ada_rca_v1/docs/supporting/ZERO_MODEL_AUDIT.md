# P3-A2 Zero-Model Morphology Audit

Formal zero-model OOF runs are bound to Ada-RCA commit `f974c8c0bb6fe487ebcbe54b33d28276846a0708`, with the frozen representation commit `7cd6d418a114978b33838e788346febbeae71818`, feature artifact commit `4fdea9da691ca738ffb706d3cc2141c7cca6f796`, and split commit `bc414e62687043d7e91b114a86d11d066e497e7b`. Each run uses three-fold OOF, L2 Logistic Regression (`C=1.0`, `max_iter=5000`), and train-fold-only `StandardScaler`. No hyperparameter search was performed.

Every variant produced 90/90 predictions per dataset. Metrics below are recomputed from the committed `predictions.jsonl` artifacts.

## Headline results

| Variant | RE2-OB AC@1 | RE2-OB AC@3 | RE2-OB Avg@5 | RE2-TT AC@1 | RE2-TT AC@3 | RE2-TT Avg@5 |
|---|---:|---:|---:|---:|---:|---:|
| Z0 | 0.2667 | 0.7222 | 0.6711 | 0.0000 | 0.0556 | 0.0533 |
| Z1 | 0.8444 | 0.9556 | 0.9267 | 0.5778 | 0.7889 | 0.7600 |
| Z2 | 0.8556 | 0.9889 | 0.9533 | 0.7000 | 0.8556 | 0.8467 |
| Z3 | 0.8444 | 0.9667 | 0.9400 | 0.5556 | 0.7333 | 0.7044 |
| Z3-SHUFFLE | 0.5333 | 0.7667 | 0.7556 | 0.3111 | 0.4667 | 0.4422 |

`MRR` is stored in every metrics artifact as diagnostic only. Z2 is not a P3-G1 gate comparison; it is retained as the preregistered handcrafted-summary control.

## Fault-separated Avg@5

| Variant | CPU OB/TT | MEM OB/TT | DISK OB/TT | SOCKET OB/TT | DELAY OB/TT | LOSS OB/TT |
|---|---:|---:|---:|---:|---:|---:|
| Z0 | 0.6400 / 0.0800 | 0.6400 / 0.0000 | 0.7333 / 0.0667 | 0.6667 / 0.0667 | 0.7333 / 0.0000 | 0.6133 / 0.1067 |
| Z1 | 0.9600 / 0.7067 | 0.9200 / 0.7867 | 0.9733 / 1.0000 | 0.9467 / 0.8400 | 0.8933 / 0.6800 | 0.8667 / 0.5467 |
| Z2 | 0.9733 / 0.9733 | 0.9600 / 0.8800 | 1.0000 / 1.0000 | 0.9733 / 1.0000 | 0.9333 / 0.6000 | 0.8800 / 0.6267 |
| Z3 | 0.9467 / 0.7867 | 0.9333 / 0.4667 | 0.9733 / 1.0000 | 0.9733 / 0.7467 | 0.9467 / 0.6133 | 0.8667 / 0.6133 |
| Z3-SHUFFLE | 0.7867 / 0.2533 | 0.7867 / 0.3333 | 0.8000 / 1.0000 | 0.5867 / 0.4133 | 0.8800 / 0.4133 | 0.6933 / 0.2400 |

## Interpretation boundary

These are controlled internal variants, not reproduced external baselines. The table does not claim superiority over published RCAEval methods. The P3-G1 decision requires paired case-level bootstrap comparisons of Z3−Z1 and Z3−Z3-SHUFFLE; this document does not substitute for that gate.
