# GLOBAL-OPT Configuration Results

`GLOBAL-OPT` fixes one representation/ranker family shared across datasets:
`FULL-Z2 + R0-ConditionalLogit`, lambda 1.0, train-fold-only scaling, no
ensemble. It is the conservative shared-family track and is numerically the
same frozen V1 configuration.

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |

Equal-dataset means: AC@1 `0.7944444444`, Avg@5 `0.9066666667`, MRR
`0.8674766848`. This track has no optimization gain over V1.
