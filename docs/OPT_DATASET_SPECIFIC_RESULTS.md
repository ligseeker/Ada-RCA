# PER-DATASET-OPT Results

Each dataset may select a different representation family and regularization
inside its own outer-train data.

| Dataset | Selected family | Fold lambdas | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---|---|---:|---:|---:|---:|---:|
| RE2-OB | FULL-Z2 | 1.0, 0.1, 1.0 | 0.8555555556 | 0.9777777778 | 0.9888888889 | 0.9511111111 | 0.9157407407 |
| RE2-TT | M+TL | 0.1, 0.1, 0.1 | 0.7888888889 | 0.8555555556 | 0.9000000000 | 0.8577777778 | 0.8392494434 |

Equal-dataset means: AC@1 `0.8222222222`, Avg@5 `0.9044444444`, MRR
`0.8774950921`. The TT gain is accompanied by an OB regression.
