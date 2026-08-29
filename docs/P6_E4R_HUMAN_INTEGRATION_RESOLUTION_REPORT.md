# P6-E4R Human-Reviewed Tier-A Integration Resolution Report

Date: 2026-08-29  
Branch: `exp/p6-baselines`  
Scope: human-reviewed non-performance resolution on RE2-OB and RE2-TT

## A. Historical State

The historical P6-E4 protocol, report, and P6-G1 decision remain unchanged.
Their recorded result is `P6-G1 = PARTIAL — AWAITING HUMAN REVIEW`.

## B. Human Resolution

Human review retained BARO as READY, accepted TraceRCA execution qualification
with its native F-A, and rejected the unsupported `re2-*` to `mm-*` aliases.
No Tier-A membership change, Tier-B promotion, Ada-RCA modification, or
algorithm-semantic baseline patch occurred.

## C. BARO

BARO remains `READY` under the historical evidence: clean pinned callable,
frozen half-open `[t0-600,t0+600)` metric window, deterministic indicator to
service projection, and 12/12 successful repeat executions. Historical BARO
semantics were not changed.

## D. TraceRCA

TraceRCA is `EXECUTION_QUALIFIED_WITH_NATIVE_F-A`. Timestamp semantics remain
seconds for `inject_time`, microseconds for `startTime`, `duration`, and
`startTime + duration`, with conversion factor `1_000_000`. The frozen span-end
window and explicit operation-to-service projection remain unchanged.

The two failures for `ts-order-service_mem/2` are the unchanged upstream
`KeyError` caused by a post-event operation absent from `normal_slo`. They are
raw F-A algorithmic failures, not F-B unsupported-input claims. No filtering,
default SLO, window enlargement, fabricated ranking, or source patch was used.

## E. mmBARO Alias Decision

`re2-ob -> mm-ob` and `re2-tt -> mm-tt` were rejected. The smoke used only the
official identifiers `re2-ob` and `re2-tt`; `dataset_alias_used` is false in
every record. The frozen manifest was reused without reselection.

## F. mmBARO Modalities

Under the unchanged pinned implementation, the score-active modalities are
exactly **metric + derived-log time series**. Trace-error and trace-latency
series, raw logs, raw spans, and `cluster_info` are not used by the score.
This path is not tri-modal and is not described as metric+log+trace BARO.

## G. mmBARO Smoke

Six manifest cases (three per dataset) were each run twice, for 12 executions.
All executions succeeded with legal service-projected output, zero unknown
mapping count, no candidate completion, and deterministic repeat checksums.
The resulting status is:

`mmBARO = READY_OFFICIAL_RE2_METRIC_LOG`

Artifacts are under `artifacts/p6_e4r/mmbaro/`.

## H. Failure Policy

`docs/P6_E5_BASELINE_FAILURE_POLICY.md` was frozen before this smoke. It keeps
F-A distinct from F-B, treats unreconstructable F-C as NR/NOT RUN, treats F-D
as INVALID requiring adapter repair, and stops on F-E data-integrity failure.
The strict all-case robustness view remains the future primary view; a
successful-output subset can only be a secondary diagnostic.

## I. Performance Firewall

PASS. No AC@k, Avg@5, MRR, root rank, correctness, Ada-RCA delta, bootstrap,
leaderboard, or formal runtime comparison was computed. Qualification code has
no root-label or performance-evaluator dependency, and no result-based adapter
choice was made.

## J. Tests

The complete repository suite passed: **84 passed** in the isolated `rcaeval`
environment. The P6-E4R-specific and historical P6-E4 baseline tests passed
without changing historical artifacts.

## K. Deviations / Unknowns

- The symmetric raw-span window remains explicitly documented as an adapter
  assumption because RCAEval has no generic TraceRCA runner window.
- TraceRCA's accepted native F-A remains a future formal-run failure case;
  this report does not execute formal reproduction.
- No upstream alias evidence was needed or accepted after human rejection.

## L. Status Per Method

| Method | P6-E4R status |
|---|---|
| BARO | `READY` |
| TraceRCA | `EXECUTION_QUALIFIED_WITH_NATIVE_F-A` |
| mmBARO | `READY_OFFICIAL_RE2_METRIC_LOG` |

Formal P6-E5 performance reproduction remains unauthorized and unexecuted.
