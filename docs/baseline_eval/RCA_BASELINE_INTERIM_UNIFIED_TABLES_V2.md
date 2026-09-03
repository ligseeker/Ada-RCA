# RCAEval Baseline Rescue V2 Interim Unified Evaluation Tables

Status: **PRE-LOCK INTERIM RECORD — NOT A METRIC UNLOCK**  
Snapshot date: 2026-09-03 (Asia/Shanghai)  
Central branch: `evaluation/rcaeval-baselines`  
Central snapshot: `6b7635a30e428271ce45da79e21b66e2c343cba3`

This document records the current V2 unified-table shape using only
performance-blind execution evidence. It is not the final confirmatory result
report.

## Scope and blank-cell policy

- Only the completed `RE2-OB` dataset is represented in the interim execution
  rows. `RE2-TT` is not counted or pooled; its Table A columns remain blank.
- CIRCA has a complete OB record set but its method attempt is incomplete in TT.
  It is therefore retained as an OB operational row only.
- MicroCause has no V2 real-case terminal records at this snapshot.
- MicroRank, TraceRCA, and mmBARO have complete OB execution records and
  complete V2 attempts; their corrected method-lock sidecars are integrity-valid.
- A blank cell means “not computed or not yet authorized”; it is not zero, a
  failed case, or a successful-subset estimate.
- Before the committed V2 global prediction lock, no labels are joined and no
  native/adapted ranking, root rank, correctness, AC@k, Avg@5, MRR, or paired
  difference is read or computed. Therefore all Table A and Table B metric
  cells are intentionally blank, including the frozen Ada-RCA reference row.
- Baseline MRR remains `NOT-IDENTIFIABLE` under the frozen protocol; it is not
  filled in Table A before metric unlock.

## Performance-blind execution snapshot

The following counts are terminal-status counts only. They are read from the
method-scoped V2 records and do not inspect prediction contents.

| Method | Dataset | Records | SUCCESS | METHOD_FAILURE | Blocking statuses | Current disposition |
|---|---|---:|---:|---:|---|---|
| CIRCA | RE2-OB | 90/90 | 86 | 4 | none observed | OB complete; method attempt pending TT resume |
| MicroCause | RE2-OB | 0/90 | 0 | 0 | — | real execution pending |
| MicroRank | RE2-OB | 90/90 | 90 | 0 | none | complete; corrected lock verified |
| TraceRCA | RE2-OB | 90/90 | 90 | 0 | none | complete; corrected lock verified |
| mmBARO | RE2-OB | 90/90 | 90 | 0 | none | complete; corrected lock verified |

## Table A — Overall RCA Performance

RE2-OB and RE2-TT are kept as separate columns. No current metric is
authorized before global-lock commit, so the cells are intentionally empty.

| Method | OB AC@1 | OB AC@3 | OB AC@5 | OB Avg@5 | TT AC@1 | TT AC@3 | TT AC@5 | TT Avg@5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CIRCA |  |  |  |  |  |  |  |  |
| MicroCause |  |  |  |  |  |  |  |  |
| MicroRank |  |  |  |  |  |  |  |  |
| TraceRCA |  |  |  |  |  |  |  |  |
| mmBARO |  |  |  |  |  |  |  |  |
| Ada-RCA |  |  |  |  |  |  |  |  |

## Table B — Fault-Level Performance

Fault labels are not joined at the pre-lock stage. The six pre-registered fault
categories are present for the completed-dataset scope, with result fields
blank until metric unlock.

| Method | Dataset | Fault | Cases | AC@1 | AC@3 | AC@5 | Avg@5 |
|---|---|---|---:|---:|---:|---:|---:|
| CIRCA | RE2-OB | CPU |  |  |  |  |  |
| CIRCA | RE2-OB | MEM |  |  |  |  |  |
| CIRCA | RE2-OB | DISK |  |  |  |  |  |
| CIRCA | RE2-OB | SOCKET |  |  |  |  |  |
| CIRCA | RE2-OB | DELAY |  |  |  |  |  |
| CIRCA | RE2-OB | LOSS |  |  |  |  |  |
| MicroCause | RE2-OB | CPU |  |  |  |  |  |
| MicroCause | RE2-OB | MEM |  |  |  |  |  |
| MicroCause | RE2-OB | DISK |  |  |  |  |  |
| MicroCause | RE2-OB | SOCKET |  |  |  |  |  |
| MicroCause | RE2-OB | DELAY |  |  |  |  |  |
| MicroCause | RE2-OB | LOSS |  |  |  |  |  |
| MicroRank | RE2-OB | CPU |  |  |  |  |  |
| MicroRank | RE2-OB | MEM |  |  |  |  |  |
| MicroRank | RE2-OB | DISK |  |  |  |  |  |
| MicroRank | RE2-OB | SOCKET |  |  |  |  |  |
| MicroRank | RE2-OB | DELAY |  |  |  |  |  |
| MicroRank | RE2-OB | LOSS |  |  |  |  |  |
| TraceRCA | RE2-OB | CPU |  |  |  |  |  |
| TraceRCA | RE2-OB | MEM |  |  |  |  |  |
| TraceRCA | RE2-OB | DISK |  |  |  |  |  |
| TraceRCA | RE2-OB | SOCKET |  |  |  |  |  |
| TraceRCA | RE2-OB | DELAY |  |  |  |  |  |
| TraceRCA | RE2-OB | LOSS |  |  |  |  |  |
| mmBARO | RE2-OB | CPU |  |  |  |  |  |
| mmBARO | RE2-OB | MEM |  |  |  |  |  |
| mmBARO | RE2-OB | DISK |  |  |  |  |  |
| mmBARO | RE2-OB | SOCKET |  |  |  |  |  |
| mmBARO | RE2-OB | DELAY |  |  |  |  |  |
| mmBARO | RE2-OB | LOSS |  |  |  |  |  |
| Ada-RCA | RE2-OB | CPU |  |  |  |  |  |
| Ada-RCA | RE2-OB | MEM |  |  |  |  |  |
| Ada-RCA | RE2-OB | DISK |  |  |  |  |  |
| Ada-RCA | RE2-OB | SOCKET |  |  |  |  |  |
| Ada-RCA | RE2-OB | DELAY |  |  |  |  |  |
| Ada-RCA | RE2-OB | LOSS |  |  |  |  |  |

## Table C — Execution Robustness

Only `RE2-OB` is shown because the interim scope excludes incomplete dataset
rows. `METHOD_FAILURE` is kept separate from infrastructure failures. An empty
MicroCause row means no completed OB dataset is available yet.

| Method | Dataset | Cases | SUCCESS | METHOD_FAILURE | DATA_FAILURE | ADAPTER_FAILURE | ENVIRONMENT_FAILURE | INPUT_INTEGRITY_FAILURE | PROCESS_CRASH/OOM | TIMEOUT |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CIRCA | RE2-OB | 90 | 86 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| MicroCause | RE2-OB |  |  |  |  |  |  |  |  |  |
| MicroRank | RE2-OB | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| TraceRCA | RE2-OB | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| mmBARO | RE2-OB | 90 | 90 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Table D — Protocol / Output Comparability

This table is protocol metadata and is not a performance result.

| Method | Input | Supervision | Native granularity | Service projection | Complete service ranking | MRR legality |
|---|---|---|---|---|---|---|
| CIRCA | metric | case-wise unsupervised | indicator | partial service projection | NO | NOT-IDENTIFIABLE |
| MicroCause | metric | case-wise unsupervised | indicator | partial service projection | NO | NOT-IDENTIFIABLE |
| MicroRank | raw trace | case-wise unsupervised | operation | partial service projection | NO | NOT-IDENTIFIABLE |
| TraceRCA | raw trace | case-wise unsupervised | operation | partial service projection | NO | NOT-IDENTIFIABLE |
| mmBARO | multi-source | case-wise unsupervised | indicator | partial service projection | NO | NOT-IDENTIFIABLE |
| Ada-RCA | Metrics + Logs + Traces | root-supervised cross-case training | native service ranking | native service ranking | YES | FROZEN/NATIVE |

## Unlock condition and next update

This interim document must not be used as the final comparison table. After
CIRCA and MicroCause produce complete integrity-valid method locks, the central
coordinator must integrate all five locks, create and commit
`artifacts/baseline_eval/execution_v2/prediction_lock_v2.json`, and only then
run the V2 evaluator. The final evaluator will write Table A, Table B, Table C,
Table D, and paired bootstrap outputs with RE2-OB and RE2-TT reported
separately.
