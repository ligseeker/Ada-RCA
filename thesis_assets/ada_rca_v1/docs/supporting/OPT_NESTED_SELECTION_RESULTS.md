# Nested Selection Results

The one-shot run uses the frozen three-fold outer assignments and deterministic
three-fold inner selection. Tree rankers were unavailable, so every selected
configuration is R0 conditional logit.

| Dataset | Outer fold | Representation | Ranker | Lambda | Inner Avg@5 | Outer test cases |
|---|---:|---|---|---:|---:|---:|
| RE2-OB | 0 | FULL-Z2 | R0 | 1.0 | 0.9367 | 30 |
| RE2-OB | 1 | FULL-Z2 | R0 | 0.1 | 0.9700 | 30 |
| RE2-OB | 2 | FULL-Z2 | R0 | 1.0 | 0.9467 | 30 |
| RE2-TT | 0 | M+TL | R0 | 0.1 | 0.8433 | 30 |
| RE2-TT | 1 | M+TL | R0 | 0.1 | 0.8800 | 30 |
| RE2-TT | 2 | M+TL | R0 | 0.1 | 0.8500 | 30 |

No inner selection event ID intersects the corresponding outer-test event IDs.
All 180 outer predictions are complete, finite, and written once.
