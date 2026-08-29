# Historical Model Inventory

Historical evidence is descriptive and was inspected after the V1 method had
already been developed. It is therefore `HISTORICAL-REFERENCE`, not an unbiased
baseline.

| Candidate | Historical stage | Dataset | Historical result | Representation | Scorer | Protocol | Replayable |
|---|---|---|---|---|---|---|---|
| B2 | P1 metric-change | RE2-OB | AC@1 0.8556; Avg@5 0.9333 | within-case metric change | no learned scorer | legacy P1 windows | No, Class B |
| C0-M | P2-G2 | RE2-OB | AC@1 0.9111; Avg@5 0.9756 | metric whole features | event logistic | 5-fold legacy nested OOF | No, Class B |
| C0-L | P2-G3 | RE2-OB | AC@1 0.2889; Avg@5 0.4667 | log whole features | event logistic | legacy extraction/folds | No, Class B |
| C0-T | P2-G3 | RE2-OB | AC@1 0.6222; Avg@5 0.8156 | trace whole features | event logistic | legacy extraction/folds | No, Class B |
| C1-I | P2-G3 | RE2-OB | AC@1 0.9778; Avg@5 0.9956 | metric+log+trace whole | event logistic | 5-fold legacy nested OOF | No, Class B |
| M1-S | P2-G4 | RE2-OB | AC@1 0.9667; Avg@5 0.9933 | whole + metric/trace stage | event logistic | 5-fold legacy nested OOF | No, Class B |
| Z0 | P3 | RE2-OB | AC@1 0.2667; Avg@5 0.6711 | magnitude only | event logistic | frozen 3-fold | Canonical source |
| Z1 | P3/P4 | RE2-OB | AC@1 0.8556; Avg@5 0.9511 | 32D absolute base | conditional logit | frozen 3-fold | Canonical source |
| Z2 | V1 | RE2-OB | AC@1 0.8778; Avg@5 0.9622 | 68D morphology | conditional logit | frozen 3-fold | Yes, V1 |
| Z3 | P3 | RE2-OB | AC@1 0.8444; Avg@5 0.9400 | flattened trajectory | event logistic | frozen 3-fold | Canonical source |

RE2-TT V1 values are AC@1 `0.7111`, Avg@5 `0.8511`; the old P2 artifacts did
not use the current TT case registry and are not directly comparable.
