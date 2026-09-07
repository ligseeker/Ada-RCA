# Ada-RCA — RCAEval Seven-Baseline Final Composite Comparison

## Material Passport

- Material ID: `ada-rca-rcaeval-final-composite-v3`
- Type: `Experiment Result`
- Verification status: `VERIFIED`
- Scope: `FINAL_COMPOSITE_SEVEN_BASELINE_COMPARISON`

The previous six-baseline V2 evaluation remains immutable. BARO is incorporated
from its previously frozen V1 label-free prediction lock without rerunning
BARO. The final seven-baseline table is therefore a composite comparison
across frozen evidence tracks, not a claim that all seven baselines were
executed under one original pre-label global lock.

## Table A — Overall RCA Performance

| Method | OB AC@1 | OB AC@3 | OB AC@5 | OB Avg@5 | TT AC@1 | TT AC@3 | TT AC@5 | TT Avg@5 |
|---|---|---|---|---|---|---|---|---|
| BARO | 0.1444444444 | 0.8777777778 | 0.9444444444 | 0.7422222222 | 0.6666666667 | 0.8222222222 | 0.8666666667 | 0.8000000000 |
| CIRCA | 0.6666666667 | 0.8777777778 | 0.9000000000 | 0.8333333333 | 0.5555555556 | 0.7000000000 | 0.7222222222 | 0.6644444444 |
| MicroCause | 0.3333333333 | 0.5333333333 | 0.6555555556 | 0.5133333333 | 0.1444444444 | 0.2333333333 | 0.3111111111 | 0.2311111111 |
| MicroRank | 0.0000000000 | 0.3777777778 | 0.5444444444 | 0.3311111111 | 0.0777777778 | 0.3222222222 | 0.3222222222 | 0.2511111111 |
| TraceRCA | 0.1555555556 | 0.6444444444 | 0.9555555556 | 0.6266666667 | 0.5666666667 | 0.6666666667 | 0.7000000000 | 0.6555555556 |
| mmBARO | 0.1666666667 | 0.8777777778 | 0.9888888889 | 0.7622222222 | 0.6888888889 | 0.8111111111 | 0.8666666667 | 0.7977777778 |
| CausalRCA | 0.0000000000 | 0.2000000000 | 0.6000000000 | 0.2400000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| Ada-RCA | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 |

## Table B — Fault-Level Performance

| Method | Dataset | Fault | Cases | AC@1 | AC@3 | AC@5 | Avg@5 |
|---|---|---|---|---|---|---|---|
| BARO | RE2-OB | CPU | 15 | 0.0000000000 | 0.8000000000 | 0.8666666667 | 0.6400000000 |
| BARO | RE2-OB | MEM | 15 | 0.3333333333 | 1.0000000000 | 1.0000000000 | 0.8666666667 |
| BARO | RE2-OB | DISK | 15 | 0.1333333333 | 1.0000000000 | 1.0000000000 | 0.8133333333 |
| BARO | RE2-OB | SOCKET | 15 | 0.0000000000 | 0.8000000000 | 0.8666666667 | 0.6666666667 |
| BARO | RE2-OB | DELAY | 15 | 0.0000000000 | 0.8000000000 | 0.9333333333 | 0.6666666667 |
| BARO | RE2-OB | LOSS | 15 | 0.4000000000 | 0.8666666667 | 1.0000000000 | 0.8000000000 |
| CIRCA | RE2-OB | CPU | 15 | 0.6000000000 | 0.8000000000 | 0.8000000000 | 0.7600000000 |
| CIRCA | RE2-OB | MEM | 15 | 0.8000000000 | 1.0000000000 | 1.0000000000 | 0.9600000000 |
| CIRCA | RE2-OB | DISK | 15 | 0.8666666667 | 0.8666666667 | 0.8666666667 | 0.8666666667 |
| CIRCA | RE2-OB | SOCKET | 15 | 0.6000000000 | 0.9333333333 | 0.9333333333 | 0.8533333333 |
| CIRCA | RE2-OB | DELAY | 15 | 0.4666666667 | 0.8000000000 | 0.8666666667 | 0.7066666667 |
| CIRCA | RE2-OB | LOSS | 15 | 0.6666666667 | 0.8666666667 | 0.9333333333 | 0.8533333333 |
| MicroCause | RE2-OB | CPU | 15 | 0.3333333333 | 0.4666666667 | 0.5333333333 | 0.4400000000 |
| MicroCause | RE2-OB | MEM | 15 | 0.3333333333 | 0.5333333333 | 0.6000000000 | 0.4800000000 |
| MicroCause | RE2-OB | DISK | 15 | 0.4000000000 | 0.7333333333 | 0.8000000000 | 0.6933333333 |
| MicroCause | RE2-OB | SOCKET | 15 | 0.2000000000 | 0.3333333333 | 0.6666666667 | 0.4000000000 |
| MicroCause | RE2-OB | DELAY | 15 | 0.4000000000 | 0.6666666667 | 0.7333333333 | 0.6133333333 |
| MicroCause | RE2-OB | LOSS | 15 | 0.3333333333 | 0.4666666667 | 0.6000000000 | 0.4533333333 |
| MicroRank | RE2-OB | CPU | 15 | 0.0000000000 | 0.4000000000 | 0.6000000000 | 0.3600000000 |
| MicroRank | RE2-OB | MEM | 15 | 0.0000000000 | 0.4000000000 | 0.6000000000 | 0.3600000000 |
| MicroRank | RE2-OB | DISK | 15 | 0.0000000000 | 0.4000000000 | 0.6000000000 | 0.3600000000 |
| MicroRank | RE2-OB | SOCKET | 15 | 0.0000000000 | 0.4000000000 | 0.6000000000 | 0.3600000000 |
| MicroRank | RE2-OB | DELAY | 15 | 0.0000000000 | 0.4000000000 | 0.6000000000 | 0.3600000000 |
| MicroRank | RE2-OB | LOSS | 15 | 0.0000000000 | 0.2666666667 | 0.2666666667 | 0.1866666667 |
| TraceRCA | RE2-OB | CPU | 15 | 0.0666666667 | 0.8000000000 | 1.0000000000 | 0.6933333333 |
| TraceRCA | RE2-OB | MEM | 15 | 0.0000000000 | 0.5333333333 | 1.0000000000 | 0.5733333333 |
| TraceRCA | RE2-OB | DISK | 15 | 0.2000000000 | 0.7333333333 | 1.0000000000 | 0.6933333333 |
| TraceRCA | RE2-OB | SOCKET | 15 | 0.1333333333 | 0.7333333333 | 1.0000000000 | 0.6800000000 |
| TraceRCA | RE2-OB | DELAY | 15 | 0.4000000000 | 0.5333333333 | 0.8666666667 | 0.6000000000 |
| TraceRCA | RE2-OB | LOSS | 15 | 0.1333333333 | 0.5333333333 | 0.8666666667 | 0.5200000000 |
| mmBARO | RE2-OB | CPU | 15 | 0.0000000000 | 0.8000000000 | 0.9333333333 | 0.6666666667 |
| mmBARO | RE2-OB | MEM | 15 | 0.4666666667 | 1.0000000000 | 1.0000000000 | 0.8933333333 |
| mmBARO | RE2-OB | DISK | 15 | 0.0666666667 | 1.0000000000 | 1.0000000000 | 0.8000000000 |
| mmBARO | RE2-OB | SOCKET | 15 | 0.0000000000 | 0.8666666667 | 1.0000000000 | 0.7200000000 |
| mmBARO | RE2-OB | DELAY | 15 | 0.0000000000 | 0.7333333333 | 1.0000000000 | 0.6800000000 |
| mmBARO | RE2-OB | LOSS | 15 | 0.4666666667 | 0.8666666667 | 1.0000000000 | 0.8133333333 |
| CausalRCA | RE2-OB | CPU | 15 | 0.0000000000 | 0.2000000000 | 0.6000000000 | 0.2400000000 |
| CausalRCA | RE2-OB | MEM | 15 | 0.0000000000 | 0.2000000000 | 0.6000000000 | 0.2400000000 |
| CausalRCA | RE2-OB | DISK | 15 | 0.0000000000 | 0.2000000000 | 0.6000000000 | 0.2400000000 |
| CausalRCA | RE2-OB | SOCKET | 15 | 0.0000000000 | 0.2000000000 | 0.6000000000 | 0.2400000000 |
| CausalRCA | RE2-OB | DELAY | 15 | 0.0000000000 | 0.2000000000 | 0.6000000000 | 0.2400000000 |
| CausalRCA | RE2-OB | LOSS | 15 | 0.0000000000 | 0.2000000000 | 0.6000000000 | 0.2400000000 |
| Ada-RCA | RE2-OB | CPU | 15 | 1.0000000000 | 1.0000000000 | 1.0000000000 | 1.0000000000 |
| Ada-RCA | RE2-OB | MEM | 15 | 0.8666666667 | 1.0000000000 | 1.0000000000 | 0.9733333333 |
| Ada-RCA | RE2-OB | DISK | 15 | 1.0000000000 | 1.0000000000 | 1.0000000000 | 1.0000000000 |
| Ada-RCA | RE2-OB | SOCKET | 15 | 0.8000000000 | 1.0000000000 | 1.0000000000 | 0.9600000000 |
| Ada-RCA | RE2-OB | DELAY | 15 | 0.8000000000 | 1.0000000000 | 1.0000000000 | 0.9466666667 |
| Ada-RCA | RE2-OB | LOSS | 15 | 0.8000000000 | 0.9333333333 | 0.9333333333 | 0.8933333333 |
| BARO | RE2-TT | CPU | 15 | 0.4666666667 | 0.8000000000 | 0.8666666667 | 0.7200000000 |
| BARO | RE2-TT | MEM | 15 | 0.9333333333 | 1.0000000000 | 1.0000000000 | 0.9866666667 |
| BARO | RE2-TT | DISK | 15 | 1.0000000000 | 1.0000000000 | 1.0000000000 | 1.0000000000 |
| BARO | RE2-TT | SOCKET | 15 | 0.6000000000 | 0.8666666667 | 0.9333333333 | 0.8266666667 |
| BARO | RE2-TT | DELAY | 15 | 0.4666666667 | 0.6666666667 | 0.6666666667 | 0.6266666667 |
| BARO | RE2-TT | LOSS | 15 | 0.5333333333 | 0.6000000000 | 0.7333333333 | 0.6400000000 |
| CIRCA | RE2-TT | CPU | 15 | 0.4000000000 | 0.6000000000 | 0.6000000000 | 0.5333333333 |
| CIRCA | RE2-TT | MEM | 15 | 0.8000000000 | 0.9333333333 | 0.9333333333 | 0.8933333333 |
| CIRCA | RE2-TT | DISK | 15 | 0.8000000000 | 0.8000000000 | 0.8000000000 | 0.8000000000 |
| CIRCA | RE2-TT | SOCKET | 15 | 0.8000000000 | 0.8666666667 | 0.8666666667 | 0.8400000000 |
| CIRCA | RE2-TT | DELAY | 15 | 0.2000000000 | 0.4000000000 | 0.4666666667 | 0.3600000000 |
| CIRCA | RE2-TT | LOSS | 15 | 0.3333333333 | 0.6000000000 | 0.6666666667 | 0.5600000000 |
| MicroCause | RE2-TT | CPU | 15 | 0.0666666667 | 0.2000000000 | 0.2000000000 | 0.1733333333 |
| MicroCause | RE2-TT | MEM | 15 | 0.0666666667 | 0.1333333333 | 0.2666666667 | 0.1333333333 |
| MicroCause | RE2-TT | DISK | 15 | 0.2000000000 | 0.2666666667 | 0.4000000000 | 0.2666666667 |
| MicroCause | RE2-TT | SOCKET | 15 | 0.3333333333 | 0.4000000000 | 0.4666666667 | 0.4133333333 |
| MicroCause | RE2-TT | DELAY | 15 | 0.1333333333 | 0.2000000000 | 0.3333333333 | 0.2400000000 |
| MicroCause | RE2-TT | LOSS | 15 | 0.0666666667 | 0.2000000000 | 0.2000000000 | 0.1600000000 |
| MicroRank | RE2-TT | CPU | 15 | 0.0666666667 | 0.4000000000 | 0.4000000000 | 0.2933333333 |
| MicroRank | RE2-TT | MEM | 15 | 0.1333333333 | 0.2666666667 | 0.2666666667 | 0.2266666667 |
| MicroRank | RE2-TT | DISK | 15 | 0.0000000000 | 0.3333333333 | 0.3333333333 | 0.2133333333 |
| MicroRank | RE2-TT | SOCKET | 15 | 0.0666666667 | 0.2666666667 | 0.2666666667 | 0.2133333333 |
| MicroRank | RE2-TT | DELAY | 15 | 0.0666666667 | 0.3333333333 | 0.3333333333 | 0.2800000000 |
| MicroRank | RE2-TT | LOSS | 15 | 0.1333333333 | 0.3333333333 | 0.3333333333 | 0.2800000000 |
| TraceRCA | RE2-TT | CPU | 15 | 0.6000000000 | 0.6666666667 | 0.6666666667 | 0.6533333333 |
| TraceRCA | RE2-TT | MEM | 15 | 0.4000000000 | 0.5333333333 | 0.5333333333 | 0.5066666667 |
| TraceRCA | RE2-TT | DISK | 15 | 0.7333333333 | 0.8666666667 | 0.8666666667 | 0.8400000000 |
| TraceRCA | RE2-TT | SOCKET | 15 | 0.4000000000 | 0.5333333333 | 0.6000000000 | 0.5200000000 |
| TraceRCA | RE2-TT | DELAY | 15 | 0.7333333333 | 0.8000000000 | 0.9333333333 | 0.8266666667 |
| TraceRCA | RE2-TT | LOSS | 15 | 0.5333333333 | 0.6000000000 | 0.6000000000 | 0.5866666667 |
| mmBARO | RE2-TT | CPU | 15 | 0.4666666667 | 0.8000000000 | 0.8666666667 | 0.7466666667 |
| mmBARO | RE2-TT | MEM | 15 | 0.9333333333 | 1.0000000000 | 1.0000000000 | 0.9866666667 |
| mmBARO | RE2-TT | DISK | 15 | 1.0000000000 | 1.0000000000 | 1.0000000000 | 1.0000000000 |
| mmBARO | RE2-TT | SOCKET | 15 | 0.6000000000 | 0.7333333333 | 0.8666666667 | 0.7333333333 |
| mmBARO | RE2-TT | DELAY | 15 | 0.4666666667 | 0.6666666667 | 0.6666666667 | 0.6133333333 |
| mmBARO | RE2-TT | LOSS | 15 | 0.6666666667 | 0.6666666667 | 0.8000000000 | 0.7066666667 |
| CausalRCA | RE2-TT | CPU | 15 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | MEM | 15 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | DISK | 15 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | SOCKET | 15 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | DELAY | 15 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | LOSS | 15 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| Ada-RCA | RE2-TT | CPU | 15 | 0.8000000000 | 1.0000000000 | 1.0000000000 | 0.9600000000 |
| Ada-RCA | RE2-TT | MEM | 15 | 0.8666666667 | 0.9333333333 | 1.0000000000 | 0.9200000000 |
| Ada-RCA | RE2-TT | DISK | 15 | 1.0000000000 | 1.0000000000 | 1.0000000000 | 1.0000000000 |
| Ada-RCA | RE2-TT | SOCKET | 15 | 0.8666666667 | 1.0000000000 | 1.0000000000 | 0.9733333333 |
| Ada-RCA | RE2-TT | DELAY | 15 | 0.4000000000 | 0.6666666667 | 0.8666666667 | 0.6666666667 |
| Ada-RCA | RE2-TT | LOSS | 15 | 0.3333333333 | 0.6000000000 | 0.7333333333 | 0.5866666667 |

Fault denominators are taken from the frozen label mapping and verified before
reporting; RE2-OB and RE2-TT are never pooled.

## Table C — Execution Robustness / Evidence Track

The rows retain each track's own status taxonomy. BARO's V1 schema did not
record V2-only `ENVIRONMENT_FAILURE`, `INPUT_INTEGRITY_FAILURE`, or
`PROCESS_CRASH/OOM` fields; `N/A (V1 schema)` means not present in that schema,
not zero. The six inherited rows are copied from the immutable V2 JSON.

| Method | Dataset | Evidence track | Cases | SUCCESS | METHOD_FAILURE | DATA_FAILURE | ADAPTER_FAILURE | ENVIRONMENT_FAILURE | INPUT_INTEGRITY_FAILURE | PROCESS_CRASH/OOM | TIMEOUT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BARO | RE2-OB | V1_LOCKED_COMPLETE | 90 | 90 | 0 | 0 | 0 | N/A (V1 schema) | N/A (V1 schema) | N/A (V1 schema) | 0 |
| CIRCA | RE2-OB | V2_RESCUE_LOCKED | 90 | 86 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| MicroCause | RE2-OB | V2_RESCUE_LOCKED | 90 | 89 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| MicroRank | RE2-OB | V2_RESCUE_LOCKED | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| TraceRCA | RE2-OB | V2_RESCUE_LOCKED | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mmBARO | RE2-OB | V2_RESCUE_LOCKED | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| CausalRCA | RE2-OB | V2_CPU_EXTENSION_LOCKED | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| BARO | RE2-TT | V1_LOCKED_COMPLETE | 90 | 90 | 0 | 0 | 0 | N/A (V1 schema) | N/A (V1 schema) | N/A (V1 schema) | 0 |
| CIRCA | RE2-TT | V2_RESCUE_LOCKED | 90 | 80 | 10 | 0 | 0 | 0 | 0 | 0 | 0 |
| MicroCause | RE2-TT | V2_RESCUE_LOCKED | 90 | 83 | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| MicroRank | RE2-TT | V2_RESCUE_LOCKED | 90 | 75 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |
| TraceRCA | RE2-TT | V2_RESCUE_LOCKED | 90 | 75 | 15 | 0 | 0 | 0 | 0 | 0 | 0 |
| mmBARO | RE2-TT | V2_RESCUE_LOCKED | 90 | 89 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| CausalRCA | RE2-TT | V2_CPU_EXTENSION_LOCKED | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Table D — Protocol / Output Comparability

Ada-RCA is a root-supervised, cross-case-trained method with a native complete
service ranking. The RCAEval baselines are primarily case-wise unsupervised
methods whose native indicator or operation outputs are projected to partial
service rankings. Baseline MRR is therefore `NOT-IDENTIFIABLE`; no candidate
completion is performed.

| Method | Input | Supervision | Native granularity | Service projection | Complete service ranking | MRR legality | Evidence track |
|---|---|---|---|---|---|---|---|
| BARO | metric | case-wise unsupervised | indicator | partial service projection | NO | NOT-IDENTIFIABLE | V1_LOCKED_COMPLETE |
| CIRCA | metric | case-wise unsupervised | indicator | partial service projection | NO | NOT-IDENTIFIABLE | V2_RESCUE_LOCKED |
| MicroCause | metric | case-wise unsupervised | indicator | partial service projection | NO | NOT-IDENTIFIABLE | V2_RESCUE_LOCKED |
| MicroRank | raw trace | case-wise unsupervised | operation | partial service projection | NO | NOT-IDENTIFIABLE | V2_RESCUE_LOCKED |
| TraceRCA | raw trace | case-wise unsupervised | operation | partial service projection | NO | NOT-IDENTIFIABLE | V2_RESCUE_LOCKED |
| mmBARO | multi-source | case-wise unsupervised | indicator | partial service projection | NO | NOT-IDENTIFIABLE | V2_RESCUE_LOCKED |
| CausalRCA | metric | case-wise unsupervised | indicator | partial service projection | NO | NOT-IDENTIFIABLE | V2_CPU_EXTENSION_LOCKED |
| Ada-RCA | Metrics + Logs + Traces | root-supervised cross-case training | native service ranking | native service ranking | YES | FROZEN/NATIVE | FROZEN_ADA_SCIENTIFIC_V1 |

## Table E — Evidence Provenance

| Method | Execution generation | Evidence track | Prediction lock | Evaluation source |
|---|---|---|---|---|
| BARO | V1 execution / V3 evaluation | V1_LOCKED_COMPLETE | artifacts/baseline_eval/execution_v1/locks/baro_prediction_lock.json | BARO V1 records; new post-scope evaluation |
| CIRCA | V2_RESCUE_LOCKED | V2_RESCUE_LOCKED | artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json | immutable execution_v2/evaluation_causalrca JSON |
| MicroCause | V2_RESCUE_LOCKED | V2_RESCUE_LOCKED | artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json | immutable execution_v2/evaluation_causalrca JSON |
| MicroRank | V2_RESCUE_LOCKED | V2_RESCUE_LOCKED | artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json | immutable execution_v2/evaluation_causalrca JSON |
| TraceRCA | V2_RESCUE_LOCKED | V2_RESCUE_LOCKED | artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json | immutable execution_v2/evaluation_causalrca JSON |
| mmBARO | V2_RESCUE_LOCKED | V2_RESCUE_LOCKED | artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json | immutable execution_v2/evaluation_causalrca JSON |
| CausalRCA | V2_CPU_EXTENSION_LOCKED | V2_CPU_EXTENSION_LOCKED | artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json | immutable execution_v2/evaluation_causalrca JSON |
| Ada-RCA | frozen user-method evidence | FROZEN_ADA_SCIENTIFIC_V1 | frozen Ada-RCA Scientific V1 evidence | artifacts/final_method/*/metrics.json and provenance.json |

BARO is `V1_LOCKED_COMPLETE`; CIRCA, MicroCause, MicroRank, TraceRCA, and
mmBARO are `V2_RESCUE_LOCKED`; CausalRCA is `V2_CPU_EXTENSION_LOCKED`; and
Ada-RCA is frozen Scientific V1 user-method evidence.

## Statistical Comparison — Paired Fault-Stratified Bootstrap

The BARO rows below are the only newly computed statistical rows. The primary
estimand is Ada-RCA minus BARO `Avg@5`, and the secondary estimand is Ada-RCA
minus BARO `AC@1`. RE2-OB and RE2-TT are analyzed separately with
`10000` resamples and seed `20260827`.

| Dataset | Delta Avg@5 | 95% CI Avg@5 | Delta AC@1 | 95% CI AC@1 |
|---|---|---|---|---|
| RE2-OB | 0.2200000000 | [0.17333333333333314, 0.26666666666666633] | 0.7333333333 | [0.6555555555555556, 0.8111111111111111] |
| RE2-TT | 0.0511111111 | [-0.004444444444444449, 0.10888888888888888] | 0.0444444444 | [-0.05555555555555555, 0.14444444444444443] |

The six inherited baseline bootstrap rows are copied from
`artifacts/baseline_eval/execution_v2/evaluation_causalrca/paired_bootstrap_v2.json`
and pass exact identity checks; they are not reinterpreted or recomputed.

## Scientific Limitations and Claim Boundary

- BARO is a complete V1 locked execution; the other five rescue baselines are
  V2 rescue evidence; CausalRCA is a V2 CPU additive extension.
- BARO was not rerun, and the existing six-method V2 outputs were not
  recomputed or overwritten.
- Metric semantics are aligned where legally identifiable, but execution
  provenance, native granularity, preprocessing, candidate coverage, and
  output completeness are not identical.
- Baseline MRR is unavailable because no audited RCAEval baseline guarantees a
  complete legal service ranking.
- Ada-RCA is supervised cross-case service ranking, whereas the RCAEval
  baselines are mostly case-wise unsupervised partial rankings.
- This evidence does not support an SOTA, universally superior, same-protocol
  superiority, causal superiority, unseen-system generalization, or unseen-root
  generalization claim.

The supported statement is limited to comparison under the frozen RE2-OB and
RE2-TT case universes and the legally aligned top-k service-projection metrics
against seven reproduced RCAEval baselines: BARO, CIRCA, MicroCause, MicroRank,
TraceRCA, mmBARO, and CausalRCA.

## Repository Provenance

- Branch at report generation: `evaluation/rcaeval-baselines`
- HEAD at report generation: `ad6b03ca794df30a2e83adb26344f689ad9282f9`
- Scope-freeze commit: `bf6349e342fa2e1ffbb1348bccbf852821503bec`
- BARO lock commit: `fbfb6e6e1f112f93fe544f8b6c71aca4f5b336f7`
- Six-method V2 combined lock commit: `2778c64f137601f307e21e735e2ad23a3e14eda6`
- Final comparison code commit: `60770dab33b22dc27f862c5aa9405b8bf608b613`
- Input manifest: `b8280866432cdd494825cf831d2a73d2fe157de0ecd8801347953172e1ab43ec`
- RCAEval: `5e96b700445bfb5c599e505ecf37d53bf847bbeb`

Final status: `SEVEN_BASELINE_FINAL_COMPOSITE_COMPARISON_READY`
