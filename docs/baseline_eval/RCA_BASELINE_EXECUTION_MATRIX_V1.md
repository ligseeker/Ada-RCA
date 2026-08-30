# RCAEval Baseline Execution Matrix V1

Status: **FROZEN; PARTIAL AUTHORIZATION; USER REVIEW REQUIRED**  
Date: 2026-08-30  
RCAEval: `5e96b700445bfb5c599e505ecf37d53bf847bbeb`

`AUTHORIZED_FOR_CONFIRMATORY_EXECUTION` means the semantic gate is complete.
It does not authorize execution during B0/B1. Full execution starts only after
the user reviews this committed freeze.

## 1. Execution matrix

| Method | Family | Provenance | Dataset | Environment | Adapter status | Timestamp status | Output status | Metric legality | Compatibility tier | Execution authorization |
|---|---|---|---|---|---|---|---|---|---|---|
| BARO | robust statistical metric ranking | official RCAEval `e2e/baro.py` | RE2-OB; RE2-TT | `.venv`, Python 3.10.20 | VALIDATED | seconds, proven | retained indicator list; scores not returned | AC@1/3/5, Avg@5 adapted; MRR not identifiable | P2 | `AUTHORIZED_FOR_CONFIRMATORY_EXECUTION` |
| CIRCA | PC graph + RHT | official RCAEval `e2e/circa.py` | RE2-OB; RE2-TT | `.venv`, Python 3.10.20 | VALIDATED; fallback detector mandatory | seconds, proven | graph + partial indicator list; scores discarded | AC@1/3/5, Avg@5 adapted; MRR not identifiable | P2 | `AUTHORIZED_FOR_CONFIRMATORY_EXECUTION` |
| MicroCause | temporal PCMCI + random walk | official RCAEval `e2e/microcause.py`; recorded upstream lineage | RE2-OB; RE2-TT | `.venv`, Python 3.10.20 | VALIDATED; label-independent SLI | seconds, proven | graph + retained indicator list; scores not returned | AC@1/3/5, Avg@5 adapted; MRR not identifiable | P2 | `AUTHORIZED_FOR_CONFIRMATORY_EXECUTION` |
| MicroRank | trace PageRank + spectrum | official RCAEval `e2e/microrank.py`; MicroRank lineage | RE2-OB; RE2-TT | `.venv`, Python 3.10.20 | VALIDATED | raw `startTime`/`duration` µs; `t0` s; conversion proven | operation list capped at 11, not 5; scores not returned | first-five AC@1/3/5, Avg@5 adapted; MRR not identifiable | P2 | `AUTHORIZED_FOR_CONFIRMATORY_EXECUTION` |
| TraceRCA | trace latency support/confidence | official RCAEval `e2e/tracerca.py`; original-source ambiguity disclosed | RE2-OB; RE2-TT | `.venv`, Python 3.10.20 | VALIDATED | raw `startTime`/`duration` µs; `t0` s; conversion proven | partial observed-operation list; scores not returned | AC@1/3/5, Avg@5 adapted; MRR not identifiable | P2 | `AUTHORIZED_FOR_CONFIRMATORY_EXECUTION` |
| mmBARO | multi-source robust anomaly ranking | official RCAEval `e2e/baro.py::mmbaro` | RE2-OB; RE2-TT | `.venv`, Python 3.10.20 | VALIDATED; official `mm-ob/mm-tt` keys | derived `time` and `t0` seconds, proven | cross-modality indicator list; scores not returned | AC@1/3/5, Avg@5 adapted; MRR not identifiable | P2 | `AUTHORIZED_FOR_CONFIRMATORY_EXECUTION` |
| CausalRCA | neural graph + PageRank | official RCAEval `e2e/causalrca.py` | RE2-OB; RE2-TT | `.venv`, Python 3.10.20, deterministic CPU | VALIDATED; empty-graph detector mandatory | seconds, proven | graph + retained indicator list; empty-graph column order invalid | AC@1/3/5, Avg@5 adapted; MRR not identifiable | P2 | `AUTHORIZED_FOR_CONFIRMATORY_EXECUTION` |
| RCD | distribution-change localized PC | official RCAEval `e2e/rcd.py` | RE2-OB; RE2-TT | required Python-3.8 lock environment not frozen | ADAPTER SPECIFIED; ENVIRONMENT UNRESOLVED | seconds, proven | partial selected-indicator list | AC@1/3/5, Avg@5 semantically adapted if later authorized; MRR not identifiable | P2 | `BLOCKED_PENDING_SEMANTIC_AUDIT` |
| PDiagnose | rule-based metric/log/trace service score | official RCAEval hard-coded demo only | hard-coded OB demo; TT unresolved | none authorized | NO GENERAL CALLABLE | mixed; log window not comparable | printed service ordering only | all not identifiable under V1 | P3 | `CONTEXT_ONLY` |
| multi-source CIRCA | requested multi-source graph | no pinned callable implementation | RE2-OB; RE2-TT | none | NO IMPLEMENTATION | unresolved | unresolved | all not identifiable | P3 | `CONTEXT_ONLY` |
| mmRCD | nominal multi-source RCD; metric-only computation | official RCAEval `e2e/mmrcd.py` | RE2-OB; RE2-TT | no selected environment | role-incompatible/redundant | derived seconds | partial metric-indicator list | all not identifiable in its excluded multi-source role | P3 | `CONTEXT_ONLY` |

## 2. Window audit

| Method | Native window behavior | Classification | Material disclosure |
|---|---|---|---|
| BARO | supplied 600-second pre and post segments; split at `t0` | `WINDOW-ALIGNED` | separate pre/post constant filtering |
| CIRCA | supplied canonical source window; RHT reloads `t0-120` through `t0+300` | `WINDOW-COMPATIBLE-WITH-NATIVE-INTERNAL-PROCESSING` | native internal subwindow and literal PC dataset `ob` on TT |
| MicroCause | consumes the supplied full 1,200-second series | `WINDOW-ALIGNED` | no explicit pre/post split; label-independent SLI |
| MicroRank | exact source spans filtered by span end; native end-time split | `WINDOW-COMPATIBLE-WITH-NATIVE-INTERNAL-PROCESSING` | raw spans, no 15-second binning |
| TraceRCA | exact source spans filtered by span end; native end-time split | `WINDOW-COMPATIBLE-WITH-NATIVE-INTERNAL-PROCESSING` | raw spans, no 15-second binning |
| mmBARO | canonical source intervals; metric stride and trace-error trim retained | `WINDOW-COMPATIBLE-WITH-NATIVE-INTERNAL-PROCESSING` | modality-specific native preprocessing |
| CausalRCA | consumes supplied full metric interval | `WINDOW-ALIGNED` | per-case full-window self-training |
| RCD | supplied pre/post metric segments split at `t0` | `WINDOW-ALIGNED` | environment still blocked |
| PDiagnose | metric/trace split but log uses whole file | `WINDOW-NOT-COMPARABLE` | no callable path |
| multi-source CIRCA | no implementation | `WINDOW-NOT-COMPARABLE` | unresolved |
| mmRCD | metric-only pre/post split | `WINDOW-ALIGNED` for actual metric path | not a valid multi-source representative |

## 3. Metric legality matrix

| Method | AC@1 | AC@3 | AC@5 | Avg@5 | MRR | Reason |
|---|---|---|---|---|---|---|
| Ada-RCA V1 | NATIVE | NATIVE | NATIVE | NATIVE | NATIVE | complete frozen service permutation |
| BARO | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | NOT-IDENTIFIABLE | indicator projection; no legal complete service order |
| CIRCA | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | NOT-IDENTIFIABLE | partial indicator projection |
| MicroCause | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | NOT-IDENTIFIABLE | retained indicators do not guarantee all legal services |
| MicroRank | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | NOT-IDENTIFIABLE | first-five prefix of capped operation output |
| TraceRCA | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | NOT-IDENTIFIABLE | observed-operation projection |
| mmBARO | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | NOT-IDENTIFIABLE | cross-modality indicator projection |
| CausalRCA | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | NOT-IDENTIFIABLE | retained indicators do not guarantee all legal services |
| RCD | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | ADAPTED-BUT-VALID | NOT-IDENTIFIABLE | semantic legality only; execution remains blocked |
| PDiagnose | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | no general callable/canonical window |
| multi-source CIRCA | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | no implementation |
| mmRCD | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | NOT-IDENTIFIABLE | excluded nominal role consumes metrics only |

## 4. Compatibility tiers

| Method set | Tier | Reason |
|---|---|---|
| Ada-RCA V1 | P1 | native service-level complete ranking under the frozen task |
| BARO, CIRCA, MicroCause, MicroRank, TraceRCA, mmBARO, CausalRCA, RCD | P2 | case-level root-ranking utility is comparable, but supervision, native granularity, preprocessing, candidate coverage, or output completeness differs |
| PDiagnose, multi-source CIRCA, mmRCD | P3 | no unbiased quantitative row in the requested role |

## 5. Frozen authorization

May proceed after user review: **BARO, CIRCA, MicroCause, MicroRank, TraceRCA,
mmBARO, and CausalRCA**.

May not proceed: **RCD** pending a compatible frozen Python-3.8 environment;
**PDiagnose, multi-source CIRCA, and mmRCD** are context-only.

Final decision: `BASELINE_PROTOCOL_FROZEN_PARTIAL_AUTHORIZATION`.
