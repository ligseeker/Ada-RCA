# RCA Baseline Audit and Necessary Fix V1

## 1. Executive Summary

The frozen baseline evidence is operationally complete for the seven listed methods: each method/dataset has exactly 90 terminal records, no missing or duplicate case ID, and no blocking terminal status. The historical numerical table is reproducible under the current `unique_service` adapter and fixed 90-case denominator.

The audit nevertheless finds two scientific qualifications. First, the pinned RCAEval `Evaluator` class evaluates service slots without deduplicating before Top-K, while its historical `main.py` driver performs a separate deduplication step; therefore both frozen audit protocols are reported and are not selected by performance. Second, CausalRCA's service-level output is exactly degenerate within each dataset: one adapted ranking is repeated for all 90 cases. The pinned source contains a broad `except Exception` around PageRank, but the old records do not preserve the exception or adjacency, so the exact historical trigger is not confirmed.

Overall conclusion: the ordinary baseline rows are usable only with explicit protocol, partial-ranking, and failure disclosure. The current CausalRCA row is not safe as a normal model-performance claim.

## 2. Experiment Provenance

| Item | Evidence |
|---|---|
| Ada-RCA branch | evaluation/rcaeval-baselines |
| Audit source HEAD | 218eb30d74ddb0b18b201169f360e6c61a1480ea |
| RCAEval checkout | /home/zhangll24/RCA_project/RCAEval-clean |
| RCAEval pinned commit | 5e96b700445bfb5c599e505ecf37d53bf847bbeb |
| Input manifest | b8280866432cdd494825cf831d2a73d2fe157de0ecd8801347953172e1ab43ec |
| Global prediction lock | artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json (935d0a3e57e27cf3b8c0d267e6d114499846f7abbce1ffec3c34ad34a63f2200) |
| Dual evaluator commit | f88a7cb3e13af7ef1bc0a656ef519b8add03ee97 |
| CausalRCA Codex executions | 0 |

Dataset design is balanced by six fault types (15 cases each) and five root services (18 cases each) in both RE2-OB and RE2-TT. These equal-size strata can make fault-macro and case-micro arithmetic coincide; the fraction pattern alone is not proof of aggregation.

## 3. Denominator Audit

| Method | Dataset | Expected | Records | SUCCESS | METHOD_FAILURE | Blocking | Denominator | hit@1 | hit@3 | hit@5 |
|---|---|---|---|---|---|---|---|---|---|---|
| BARO | RE2-OB | 90 | 90 | 90 | 0 | 0 | 90 | 13 | 79 | 85 |
| BARO | RE2-TT | 90 | 90 | 90 | 0 | 0 | 90 | 60 | 74 | 78 |
| CIRCA | RE2-OB | 90 | 90 | 86 | 4 | 0 | 90 | 60 | 79 | 81 |
| CIRCA | RE2-TT | 90 | 90 | 80 | 10 | 0 | 90 | 50 | 63 | 65 |
| MicroCause | RE2-OB | 90 | 90 | 89 | 1 | 0 | 90 | 30 | 48 | 59 |
| MicroCause | RE2-TT | 90 | 90 | 83 | 7 | 0 | 90 | 13 | 21 | 28 |
| MicroRank | RE2-OB | 90 | 90 | 90 | 0 | 0 | 90 | 0 | 34 | 49 |
| MicroRank | RE2-TT | 90 | 90 | 75 | 15 | 0 | 90 | 7 | 29 | 29 |
| TraceRCA | RE2-OB | 90 | 90 | 90 | 0 | 0 | 90 | 14 | 58 | 86 |
| TraceRCA | RE2-TT | 90 | 90 | 75 | 15 | 0 | 90 | 51 | 60 | 63 |
| mmBARO | RE2-OB | 90 | 90 | 90 | 0 | 0 | 90 | 15 | 79 | 89 |
| mmBARO | RE2-TT | 90 | 90 | 89 | 1 | 0 | 90 | 62 | 73 | 78 |
| CausalRCA | RE2-OB | 90 | 90 | 90 | 0 | 0 | 90 | 0 | 18 | 54 |
| CausalRCA | RE2-TT | 90 | 90 | 90 | 0 | 0 | 90 | 0 | 0 | 0 |

There are no skipped cases in the active evidence. `METHOD_FAILURE` is retained in the denominator and contributes five zero hits under the frozen utility policy. Missing, duplicate, foreign, or blocking records would stop evaluation; none are present.

The Avg@5 checks are true for all 14 method/dataset rows. The audit computes `sum(raw hit@1..hit@5)/(5*90)` and does not average rounded cells.

## 4. Regular Fraction Audit

| Displayed | Observed numerator/denominator examples |
|---|---|
| 0.1667 | 15/90 (mmBARO RE2-OB unique_service AC@1), 15/90 (mmBARO RE2-OB rcaeval_service_slot AC@1) |
| 0.2000 | 18/90 (CausalRCA RE2-OB unique_service AC@3), 18/90 (CausalRCA RE2-OB rcaeval_service_slot AC@3), 18/90 (MicroCause RE2-TT unique_service AC@2), 18/90 (MicroCause RE2-TT rcaeval_service_slot AC@2) |
| 0.3333 | 30/90 (MicroCause RE2-OB unique_service AC@1), 30/90 (MicroCause RE2-OB rcaeval_service_slot AC@1) |
| 0.4000 | 36/90 (CausalRCA RE2-OB unique_service AC@4), 36/90 (CausalRCA RE2-OB rcaeval_service_slot AC@4) |
| 0.6000 | 54/90 (CausalRCA RE2-OB unique_service AC@5), 54/90 (CausalRCA RE2-OB rcaeval_service_slot AC@5), 54/90 (MicroCause RE2-OB rcaeval_service_slot AC@5) |
| 0.6667 | 60/90 (BARO RE2-TT unique_service AC@1), 60/90 (BARO RE2-TT rcaeval_service_slot AC@1), 60/90 (CIRCA RE2-OB unique_service AC@1), 60/90 (CIRCA RE2-OB rcaeval_service_slot AC@1) |
| 0.8333 | 75/90 (CIRCA RE2-OB unique_service AC@2), 375/450 (CIRCA RE2-OB unique_service Avg@5), 75/90 (CIRCA RE2-OB rcaeval_service_slot AC@2), 375/450 (CIRCA RE2-OB rcaeval_service_slot Avg@5) |
| 0.8778 | 79/90 (BARO RE2-OB unique_service AC@3), 79/90 (BARO RE2-OB rcaeval_service_slot AC@3), 79/90 (CIRCA RE2-OB unique_service AC@3), 79/90 (CIRCA RE2-OB rcaeval_service_slot AC@3) |
| 0.9889 | 89/90 (mmBARO RE2-OB unique_service AC@5) |

For AC@K, the denominator is 90. For Avg@5, the denominator is 450. In particular, 0.3333 is 30/90, 0.6667 is 60/90, 0.1667 is 15/90, 0.8333 as an AC cell is 75/90, 0.8778 is 79/90, and 0.9889 is 89/90. The 0.8333 displayed Avg@5 occurrences, where present, are 375/450 and must not be misread as 75/90 without the metric name.

## 5. Evaluation Protocol Audit

`unique_service`: native ranking -> frozen longest-prefix/alias mapping -> first occurrence retained -> duplicate service removed -> unmapped item removed -> Top-K.

`rcaeval_service_slot`: native ranking -> pinned `main.py` entity projection (`x.split('_')[0].replace('-db','')`) at every native slot -> no service deduplication or local candidate filtering -> Top-K slot membership. This isolates the pinned `Evaluator.add_case` service-slot behavior. The local `frontendservice` alias belongs only to `unique_service`.

Static source review found that pinned `RCAEval/benchmark/evaluation.py` uses `service_ranks[:k]` without deduplication. It also found pinned `main.py` deduplicates `Node` services before calling that class. This driver/class distinction is recorded rather than silently resolved in favor of a higher score.

Synthetic test: `A_cpu, A_mem, B_cpu, C_cpu` with target `C` produces `A,B,C` and rank 3 under unique-service, versus `A,A,B,C` and rank 4 under service-slot.

## 6. Dual-protocol Results

| Method | Dataset | Metric | Old | Unique-service | RCAEval-slot | Delta (slot-unique) |
|---|---|---|---|---|---|---|
| BARO | RE2-OB | AC@1 | 0.1444444444 | 0.1444444444 | 0.1444444444 | 0.0000000000 |
| BARO | RE2-OB | AC@2 | 0.8222222222 | 0.8222222222 | 0.8222222222 | 0.0000000000 |
| BARO | RE2-OB | AC@3 | 0.8777777778 | 0.8777777778 | 0.8777777778 | 0.0000000000 |
| BARO | RE2-OB | AC@4 | 0.9222222222 | 0.9222222222 | 0.9111111111 | -0.0111111111 |
| BARO | RE2-OB | AC@5 | 0.9444444444 | 0.9444444444 | 0.9333333333 | -0.0111111111 |
| BARO | RE2-OB | Avg@5 | 0.7422222222 | 0.7422222222 | 0.7377777778 | -0.0044444444 |
| BARO | RE2-TT | AC@1 | 0.6666666667 | 0.6666666667 | 0.6666666667 | 0.0000000000 |
| BARO | RE2-TT | AC@2 | 0.7888888889 | 0.7888888889 | 0.7888888889 | 0.0000000000 |
| BARO | RE2-TT | AC@3 | 0.8222222222 | 0.8222222222 | 0.8222222222 | 0.0000000000 |
| BARO | RE2-TT | AC@4 | 0.8555555556 | 0.8555555556 | 0.8444444444 | -0.0111111111 |
| BARO | RE2-TT | AC@5 | 0.8666666667 | 0.8666666667 | 0.8555555556 | -0.0111111111 |
| BARO | RE2-TT | Avg@5 | 0.8000000000 | 0.8000000000 | 0.7955555556 | -0.0044444444 |
| CIRCA | RE2-OB | AC@1 | 0.6666666667 | 0.6666666667 | 0.6666666667 | 0.0000000000 |
| CIRCA | RE2-OB | AC@2 | 0.8333333333 | 0.8333333333 | 0.8333333333 | 0.0000000000 |
| CIRCA | RE2-OB | AC@3 | 0.8777777778 | 0.8777777778 | 0.8777777778 | 0.0000000000 |
| CIRCA | RE2-OB | AC@4 | 0.8888888889 | 0.8888888889 | 0.8888888889 | 0.0000000000 |
| CIRCA | RE2-OB | AC@5 | 0.9000000000 | 0.9000000000 | 0.9000000000 | 0.0000000000 |
| CIRCA | RE2-OB | Avg@5 | 0.8333333333 | 0.8333333333 | 0.8333333333 | 0.0000000000 |
| CIRCA | RE2-TT | AC@1 | 0.5555555556 | 0.5555555556 | 0.5555555556 | 0.0000000000 |
| CIRCA | RE2-TT | AC@2 | 0.6444444444 | 0.6444444444 | 0.6444444444 | 0.0000000000 |
| CIRCA | RE2-TT | AC@3 | 0.7000000000 | 0.7000000000 | 0.7000000000 | 0.0000000000 |
| CIRCA | RE2-TT | AC@4 | 0.7000000000 | 0.7000000000 | 0.7000000000 | 0.0000000000 |
| CIRCA | RE2-TT | AC@5 | 0.7222222222 | 0.7222222222 | 0.7222222222 | 0.0000000000 |
| CIRCA | RE2-TT | Avg@5 | 0.6644444444 | 0.6644444444 | 0.6644444444 | 0.0000000000 |
| MicroCause | RE2-OB | AC@1 | 0.3333333333 | 0.3333333333 | 0.3333333333 | 0.0000000000 |
| MicroCause | RE2-OB | AC@2 | 0.4666666667 | 0.4666666667 | 0.4666666667 | 0.0000000000 |
| MicroCause | RE2-OB | AC@3 | 0.5333333333 | 0.5333333333 | 0.5333333333 | 0.0000000000 |
| MicroCause | RE2-OB | AC@4 | 0.5777777778 | 0.5777777778 | 0.5666666667 | -0.0111111111 |
| MicroCause | RE2-OB | AC@5 | 0.6555555556 | 0.6555555556 | 0.6000000000 | -0.0555555556 |
| MicroCause | RE2-OB | Avg@5 | 0.5133333333 | 0.5133333333 | 0.5000000000 | -0.0133333333 |
| MicroCause | RE2-TT | AC@1 | 0.1444444444 | 0.1444444444 | 0.1444444444 | 0.0000000000 |
| MicroCause | RE2-TT | AC@2 | 0.2000000000 | 0.2000000000 | 0.2000000000 | 0.0000000000 |
| MicroCause | RE2-TT | AC@3 | 0.2333333333 | 0.2333333333 | 0.2333333333 | 0.0000000000 |
| MicroCause | RE2-TT | AC@4 | 0.2666666667 | 0.2666666667 | 0.2666666667 | 0.0000000000 |
| MicroCause | RE2-TT | AC@5 | 0.3111111111 | 0.3111111111 | 0.3111111111 | 0.0000000000 |
| MicroCause | RE2-TT | Avg@5 | 0.2311111111 | 0.2311111111 | 0.2311111111 | 0.0000000000 |
| MicroRank | RE2-OB | AC@1 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| MicroRank | RE2-OB | AC@2 | 0.1888888889 | 0.1888888889 | 0.1888888889 | 0.0000000000 |
| MicroRank | RE2-OB | AC@3 | 0.3777777778 | 0.3777777778 | 0.2333333333 | -0.1444444444 |
| MicroRank | RE2-OB | AC@4 | 0.5444444444 | 0.5444444444 | 0.2888888889 | -0.2555555556 |
| MicroRank | RE2-OB | AC@5 | 0.5444444444 | 0.5444444444 | 0.3444444444 | -0.2000000000 |
| MicroRank | RE2-OB | Avg@5 | 0.3311111111 | 0.3311111111 | 0.2111111111 | -0.1200000000 |
| MicroRank | RE2-TT | AC@1 | 0.0777777778 | 0.0777777778 | 0.0777777778 | 0.0000000000 |
| MicroRank | RE2-TT | AC@2 | 0.2111111111 | 0.2111111111 | 0.2111111111 | 0.0000000000 |
| MicroRank | RE2-TT | AC@3 | 0.3222222222 | 0.3222222222 | 0.2111111111 | -0.1111111111 |
| MicroRank | RE2-TT | AC@4 | 0.3222222222 | 0.3222222222 | 0.2111111111 | -0.1111111111 |
| MicroRank | RE2-TT | AC@5 | 0.3222222222 | 0.3222222222 | 0.3222222222 | 0.0000000000 |
| MicroRank | RE2-TT | Avg@5 | 0.2511111111 | 0.2511111111 | 0.2066666667 | -0.0444444444 |
| TraceRCA | RE2-OB | AC@1 | 0.1555555556 | 0.1555555556 | 0.1555555556 | 0.0000000000 |
| TraceRCA | RE2-OB | AC@2 | 0.5000000000 | 0.5000000000 | 0.3777777778 | -0.1222222222 |
| TraceRCA | RE2-OB | AC@3 | 0.6444444444 | 0.6444444444 | 0.4444444444 | -0.2000000000 |
| TraceRCA | RE2-OB | AC@4 | 0.8777777778 | 0.8777777778 | 0.5555555556 | -0.3222222222 |
| TraceRCA | RE2-OB | AC@5 | 0.9555555556 | 0.9555555556 | 0.5888888889 | -0.3666666667 |
| TraceRCA | RE2-OB | Avg@5 | 0.6266666667 | 0.6266666667 | 0.4244444444 | -0.2022222222 |
| TraceRCA | RE2-TT | AC@1 | 0.5666666667 | 0.5666666667 | 0.5666666667 | 0.0000000000 |
| TraceRCA | RE2-TT | AC@2 | 0.6666666667 | 0.6666666667 | 0.6333333333 | -0.0333333333 |
| TraceRCA | RE2-TT | AC@3 | 0.6666666667 | 0.6666666667 | 0.6666666667 | 0.0000000000 |
| TraceRCA | RE2-TT | AC@4 | 0.6777777778 | 0.6777777778 | 0.6666666667 | -0.0111111111 |
| TraceRCA | RE2-TT | AC@5 | 0.7000000000 | 0.7000000000 | 0.6777777778 | -0.0222222222 |
| TraceRCA | RE2-TT | Avg@5 | 0.6555555556 | 0.6555555556 | 0.6422222222 | -0.0133333333 |
| mmBARO | RE2-OB | AC@1 | 0.1666666667 | 0.1666666667 | 0.1666666667 | 0.0000000000 |
| mmBARO | RE2-OB | AC@2 | 0.8222222222 | 0.8222222222 | 0.8222222222 | 0.0000000000 |
| mmBARO | RE2-OB | AC@3 | 0.8777777778 | 0.8777777778 | 0.8777777778 | 0.0000000000 |
| mmBARO | RE2-OB | AC@4 | 0.9555555556 | 0.9555555556 | 0.9333333333 | -0.0222222222 |
| mmBARO | RE2-OB | AC@5 | 0.9888888889 | 0.9888888889 | 0.9555555556 | -0.0333333333 |
| mmBARO | RE2-OB | Avg@5 | 0.7622222222 | 0.7622222222 | 0.7511111111 | -0.0111111111 |
| mmBARO | RE2-TT | AC@1 | 0.6888888889 | 0.6888888889 | 0.6888888889 | 0.0000000000 |
| mmBARO | RE2-TT | AC@2 | 0.7888888889 | 0.7888888889 | 0.7888888889 | 0.0000000000 |
| mmBARO | RE2-TT | AC@3 | 0.8111111111 | 0.8111111111 | 0.8111111111 | 0.0000000000 |
| mmBARO | RE2-TT | AC@4 | 0.8333333333 | 0.8333333333 | 0.8222222222 | -0.0111111111 |
| mmBARO | RE2-TT | AC@5 | 0.8666666667 | 0.8666666667 | 0.8444444444 | -0.0222222222 |
| mmBARO | RE2-TT | Avg@5 | 0.7977777778 | 0.7977777778 | 0.7911111111 | -0.0066666667 |
| CausalRCA | RE2-OB | AC@1 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-OB | AC@2 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-OB | AC@3 | 0.2000000000 | 0.2000000000 | 0.2000000000 | 0.0000000000 |
| CausalRCA | RE2-OB | AC@4 | 0.4000000000 | 0.4000000000 | 0.4000000000 | 0.0000000000 |
| CausalRCA | RE2-OB | AC@5 | 0.6000000000 | 0.6000000000 | 0.6000000000 | 0.0000000000 |
| CausalRCA | RE2-OB | Avg@5 | 0.2400000000 | 0.2400000000 | 0.2400000000 | 0.0000000000 |
| CausalRCA | RE2-TT | AC@1 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | AC@2 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | AC@3 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | AC@4 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | AC@5 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |
| CausalRCA | RE2-TT | Avg@5 | 0.0000000000 | 0.0000000000 | 0.0000000000 | 0.0000000000 |

The old values identity-check against the recomputed unique-service values for every reported metric. This is evidence that the current table is not a successful-case-only or post-hoc fraction calculation. The slot protocol lowers some Top-K values where duplicate operations/indicators occupy native slots; for CausalRCA the pinned entity projection happens to match the local service projection in these records.

## 7. Protocol Difference Cases

The complete case-level list is stored in `artifacts/baseline_eval/audit_fix_v1/protocol_difference_cases.jsonl` (1207 rows). A difference row is emitted when the two projected rankings differ or any hit@K differs. Typical affected cases:

| Method | Dataset | Case | Root | Unique rank | Slot rank | Affected K | Unique prefix | Slot prefix |
|---|---|---|---|---|---|---|---|---|
| BARO | RE2-OB | re2ob-da48e150772a24fd | currencyservice | 5 | 6 | [5] | ['redis', 'cartservice', 'checkoutservice', 'frontend', 'currencyservice'] | ['redis', 'cartservice', 'checkoutservice', 'frontend', 'redis'] |
| BARO | RE2-OB | re2ob-f874f110aae8efa9 | currencyservice | 4 | 5 | [4] | ['redis', 'checkoutservice', 'frontend', 'currencyservice', 'recommendationservice'] | ['redis', 'checkoutservice', 'frontend', 'redis', 'currencyservice'] |
| BARO | RE2-TT | re2tt-6a0d1ebf31fb52a6 | ts-auth-service | 4 | 6 | [4, 5] | ['ts-price-service', 'ts-ticketinfo-service', 'ts-basic-service', 'ts-auth-service', 'ts-admin-basic-info-service'] | ['ts-price-service', 'ts-price-service', 'ts-ticketinfo-service', 'ts-price-service', 'ts-basic-service'] |
| MicroCause | RE2-OB | re2ob-79fcefff48aef53b | checkoutservice | 5 | 7 | [5] | ['recommendationservice', 'currencyservice', 'shippingservice', 'cartservice', 'checkoutservice'] | ['recommendationservice', 'currencyservice', 'shippingservice', 'shippingservice', 'cartservice'] |
| MicroCause | RE2-OB | re2ob-1d19cc60d7a6adc1 | checkoutservice | 5 | 6 | [5] | ['currencyservice', 'emailservice', 'frontend', 'shippingservice', 'checkoutservice'] | ['currencyservice', 'emailservice', 'emailservice', 'frontend', 'shippingservice'] |
| MicroCause | RE2-OB | re2ob-bb4a5b75716772f9 | emailservice | 5 | 6 | [5] | ['currencyservice', 'cartservice', 'productcatalogservice', 'paymentservice', 'emailservice'] | ['currencyservice', 'cartservice', 'productcatalogservice', 'paymentservice', 'currencyservice'] |
| MicroCause | RE2-OB | re2ob-048f2e7d7bfbc927 | emailservice | 4 | 6 | [4, 5] | ['currencyservice', 'cartservice', 'checkoutservice', 'emailservice', 'adservice'] | ['currencyservice', 'cartservice', 'cartservice', 'cartservice', 'checkoutservice'] |
| MicroCause | RE2-OB | re2ob-4f85dadf2507c3ca | productcatalogservice | 5 | 7 | [5] | ['currencyservice', 'recommendationservice', 'checkoutservice', 'adservice', 'productcatalogservice'] | ['currencyservice', 'recommendationservice', 'checkoutservice', 'recommendationservice', 'adservice'] |

## 8. Method Source and Execution Audit

All six non-CausalRCA methods use the pinned source digests recorded in the active locks. The local worker passes the frozen windowed inputs and preserves native ranking direction; it does not reverse rankings or inject labels. BARO uses the upstream RobustScaler and descending score sort. mmBARO uses the upstream multi-modal metric/log/trace paths and RobustScaler. CIRCA calls the upstream PC/RHT path and the pinned source hard-codes `pc_default(..., dataset="ob")`, including when the local runner supplies TT; this is an upstream behavior/limitation, not a local silent substitution. MicroCause sorts its gamma score descending. MicroRank constructs `serviceName_methodName`, sorts descending, and returns up to `top_max + 6 = 11`. TraceRCA uses support/confidence/Ji and descending Ji sort.

| Method | Source digest matches | Audit interpretation |
|---|---|---|
| BARO | True | native source inspected; no ranking-direction rewrite in local worker |
| CIRCA | True | native source inspected; no ranking-direction rewrite in local worker |
| MicroCause | True | native source inspected; no ranking-direction rewrite in local worker |
| MicroRank | True | native source inspected; no ranking-direction rewrite in local worker |
| TraceRCA | True | native source inspected; no ranking-direction rewrite in local worker |
| mmBARO | True | native source inspected; no ranking-direction rewrite in local worker |
| CausalRCA | True | native source inspected; no ranking-direction rewrite in local worker |

## 9. MicroRank专项审计

The pinned implementation returns at most 11 native operations because `top_max=5` is used in a `index < top_max + 6` prefix. The active records preserve 11-operation outputs where successful, and the runner records `NATIVE_TOP_K_TRUNCATION` separately from no observed telemetry.

| Dataset | Native lengths | Truncation cases | Root in first 5 | Root anywhere | Top-1 miss/Top-3 hit case | Truncation example | Dedup outcome example |
|---|---|---|---|---|---|---|---|
| RE2-OB | {11: 90} | 41 | 31 | 49 | re2ob-cec5183e3f5418cf | re2ob-9e575f44de987a1a | re2ob-a84cfdf477d8bf62 |
| RE2-TT | {11: 75} | 46 | 29 | 29 | re2tt-e44ccb97e7cc1570 | re2tt-783d045c8102f972 | re2tt-2782358136a64e6c |

For RE2-OB, at least one case has a Top-1 miss but Top-3 hit, and a separate case has native truncation evidence. The full case rows in the JSONL contain the exact rankings. Therefore MicroRank OB AC@1=0 is caused by the real case-level native predictions under the frozen service projection; it is not an evaluator bug. Deduplication can change later Top-K outcomes, but it cannot turn a zero Top-1 hit count into a nonzero one.

## 10. CausalRCA Static Audit

No CausalRCA case was executed by Codex. The source audit confirms that `causalrca.py` thresholds the learned graph, transposes/absolutizes it, then calls PageRank in a `try` block. Any `Exception` from PageRank returns `node_names` as `ranks`; the exception scope is broader than the source comment `# empty graph`. The top-level pinned `rca` wrapper also catches any `Exception` and returns a preprocessed column-order ranking.

| Dataset | Native unique digests | Adapted unique digests | Fixed adapted root positions | OB/TT exact result explanation |
|---|---|---|---|---|
| RE2-OB | 69 | 1 | {'checkoutservice': {'3': 18}, 'currencyservice': {'4': 18}, 'emailservice': {'5': 18}, 'productcatalogservice': {'8': 18}, 'recommendationservice': {'9': 18}} | five roots x 18 cases; positions are fixed after service projection |
| RE2-TT | 80 | 1 | {'ts-auth-service': {'9': 18}, 'ts-order-service': {'35': 18}, 'ts-route-service': {'47': 18}, 'ts-train-service': {'57': 18}, 'ts-travel-service': {'60': 18}} | five roots x 18 cases; positions are fixed after service projection |

RE2-OB adapted root positions are checkoutservice=3, currencyservice=4, emailservice=5, productcatalogservice=8, recommendationservice=9. Thus hit counts are 0/90, 0/90, 18/90, 36/90, 54/90 for AC@1..5, exactly 0, 0, 0.2, 0.4, 0.6. RE2-TT positions are 9, 35, 47, 57, and 60, so all five roots are outside Top-5 and AC@1/3/5 are all 0. The native rankings have 69 and 80 unique persisted digests, respectively, but the adapted service ranking has one digest in each dataset; the degeneration relevant to the reported service metric is confirmed.

The frozen records contain no `adj` or `node_names`, so adjacency and exact PageRank score vectors cannot be reconstructed. Offline name-only reconstruction from current manifest-bound inputs is retained in `causalrca_static_audit.json`; mismatches are not converted into invented runtime facts.

## 11. CausalRCA Evidence Level

| Level | Conclusion |
|---|---|
| CONFIRMED | Active CausalRCA records are SUCCESS at 90+90, and adapted rankings are fixed within each dataset; the OB/TT score pattern follows the measured fixed root positions exactly. |
| HIGHLY LIKELY | The fixed-order output is caused by the pinned PageRank exception fallback or the broad wrapper fallback, because both source fallbacks return column order; old artifacts lack runtime trigger evidence. |
| UNKNOWN | Exact historical exception type/message, adjacency shape/density, PageRank score vector, and whether the inner or outer fallback fired for each case. |

## 12. Per-baseline Verdict

| Method | Verdict | Evidence | Model rerun | Evaluator recomputation | Paper use |
|---|---|---|---|---|---|
| BARO | NO_EVIDENCE_OF_IMPLEMENTATION_ERROR | Pinned RobustScaler/descending path; old equals unique recomputation; 90/90 success. | No | Done | SAFE WITH PROTOCOL DISCLOSURE |
| CIRCA | IMPLEMENTATION_VALID_METHOD_PERFORMANCE_LOW | Pinned PC/RHT path; TT `dataset=ob` hard-code is upstream; failures remain 90 denominator. | No | Done | SAFE WITH PROTOCOL DISCLOSURE |
| MicroCause | IMPLEMENTATION_VALID_METHOD_PERFORMANCE_LOW | Native low hits and persisted METHOD_FAILUREs explain the counts; no ranking substitution. | No | Done | SAFE WITH PROTOCOL DISCLOSURE |
| MicroRank | IMPLEMENTATION_VALID_METHOD_PERFORMANCE_LOW | OB Top-1 zero is real case-level output; top_max+6 truncation and operation duplicates are explicit. | No | Done | SAFE WITH PROTOCOL DISCLOSURE |
| TraceRCA | IMPLEMENTATION_VALID_METHOD_PERFORMANCE_LOW | Pinned SLO/support/confidence/Ji descending path; service-slot sensitivity and TT failures disclosed. | No | Done | SAFE WITH PROTOCOL DISCLOSURE |
| mmBARO | NO_EVIDENCE_OF_IMPLEMENTATION_ERROR | Pinned multi-modal RobustScaler path; old equals unique recomputation; failures/statuses explicit. | No | Done | SAFE WITH PROTOCOL DISCLOSURE |
| CausalRCA | HIGHLY_SUSPECT | Fixed adapted ranking; broad PageRank/wrapper fallbacks; exact trigger absent from records. | Diagnostic first; full rerun before repaired claim | Done; protocol-independent here | NOT SAFE |

## 13. Paper Safety

SAFE means the numerical row can be used only if the frozen protocol is stated. SAFE WITH PROTOCOL DISCLOSURE is recommended for all ordinary baselines because native outputs are partial rankings, service projection is not a complete candidate completion, failures remain in the denominator, and the pinned evaluator class/driver have distinct deduplication stages. CausalRCA is NOT SAFE as a normal model-performance claim until a manual diagnostic and, if a valid repaired method is desired, a separately authorized 180-case rerun produce runtime-backed records.

## 14. Required Reruns

No ordinary baseline rerun is required for this audit. CausalRCA requires the prepared manual diagnostic to identify the runtime trigger. A full 180-case CausalRCA rerun is not needed to establish that the frozen service output is degenerate, but it is required before publishing a new repaired CausalRCA result. Any such rerun needs a new authorized lock/attempt and must not overwrite the historical records.

## 15. CausalRCA Manual Commands

The following commands are prepared but were not executed by Codex. They use the frozen common environment, the manifest-bound clean RCAEval checkout, one diagnostic process (no `--workers` option), seed/hash controls, and `/tmp` output so a manual diagnostic cannot silently enter the committed confirmatory tree. The selected cases come from `causalrca_diagnostics_schema.json`.

### Command A — RE2-OB diagnostic

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
source ~/.venvs/ada-rca-baselines-common/bin/activate
PYTHONHASHSEED=20260830 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/home/zhangll24/RCA_project/RCAEval-clean:/home/zhangll24/RCA_project/Ada-RCA-v2-causalrca python scripts/baseline_eval/run_causalrca_diagnostic.py --dataset re2ob --case-file artifacts/baseline_eval/audit_fix_v1/causalrca_diagnostics_schema.json --output /tmp/causalrca_diagnostic_re2ob.json 2>&1 | tee /tmp/causalrca_diagnostic_re2ob.log
```

### Command B — RE2-TT diagnostic

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
source ~/.venvs/ada-rca-baselines-common/bin/activate
PYTHONHASHSEED=20260830 PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 PYTHONPATH=/home/zhangll24/RCA_project/RCAEval-clean:/home/zhangll24/RCA_project/Ada-RCA-v2-causalrca python scripts/baseline_eval/run_causalrca_diagnostic.py --dataset re2tt --case-file artifacts/baseline_eval/audit_fix_v1/causalrca_diagnostics_schema.json --output /tmp/causalrca_diagnostic_re2tt.json 2>&1 | tee /tmp/causalrca_diagnostic_re2tt.log
```

No full-rerun commands are supplied in this report because the exact diagnostic result and a new authorized execution/lock identity are not yet known. Existing `scripts/run_baseline_rescue_v2.py run` is the real V2 runner, but reusing the frozen CausalRCA attempt would violate the no-overwrite/no-resume evidence rule.

## 16. Artifacts, Tests, and Commits

Artifacts: `artifacts/baseline_eval/audit_fix_v1/` contains the provenance, denominator, dual-protocol, protocol-difference, regular-fraction, CausalRCA static audit, and diagnostic schema files. The full native rankings/ground truth used after the existing locks are joined are in the JSONL/case-level JSON artifacts; historical records and locks are unchanged.

Tests include fixed-denominator, failure-zero-utility, duplicate-service synthetic evaluation, PageRank success/exception instrumentation, empty/non-empty graph cases, fallback classification, and the existing performance firewall. The final command/result is recorded in the handoff after artifact generation.
