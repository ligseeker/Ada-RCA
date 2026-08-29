# P6-E4R Human-Reviewed Tier-A Integration Resolution Protocol

Date: 2026-08-29  
Branch: `exp/p6-baselines`  
Phase: P6-E4R — Human-Reviewed Tier-A Integration Resolution

## 1. Scope

This document is a human-authorized resolution layer over the historical
P6-E4 qualification. The historical protocol, report, and P6-G1 decision are
immutable; their result remains `P6-G1 = PARTIAL — AWAITING HUMAN REVIEW`.

This round performs non-performance integration resolution only. No formal
P6-E5 reproduction is authorized by this protocol.

## 2. Scientific Boundary

- Tier-A membership remains BARO, TraceRCA, and mmBARO.
- No Tier-B promotion or substitution is permitted.
- Ada-RCA, Z2, conditional-logit scoring, lambda, splits, registries, and
  prior scientific conclusions are unchanged.
- No RCAEval algorithm source is modified and no algorithm-semantic baseline
  patch is allowed.
- No published or reproduced performance value was inspected or used for an
  integration decision.

## 3. Human Resolution

### BARO

BARO remains `READY`. Its previously frozen integration semantics are retained.

### TraceRCA

TraceRCA is `EXECUTION_QUALIFIED_WITH_NATIVE_F-A`. The `KeyError` observed for
`ts-order-service_mem/2` is accepted as an unchanged upstream F-A algorithmic
failure caused by a post-event operation absent from `normal_slo`. It is not
F-B and must not be repaired, filtered, or replaced. Future formal execution
must preserve the case and apply the separately frozen P6-E5 failure policy.

### mmBARO

The proposed `re2-ob -> mm-ob` and `re2-tt -> mm-tt` aliases are rejected.
Smoke execution uses official identifiers `re2-ob` and `re2-tt` only. Under
the pinned implementation, the authorized score inputs are metric and derived
log time series. Trace time series, raw logs, raw spans, and `cluster_info` are
not score modalities. The entering state is:

`PENDING_OFFICIAL_RE2_PATH_SMOKE`

## 4. Qualification and Firewall

The frozen smoke manifest is reused without reselection. No root label,
correctness, ranking metric, evaluator, comparison, or published result may
enter path selection, input interpretation, status assignment, or output
mapping. Native failures remain explicit; dummy rankings and candidate
completion are forbidden.

## 5. Entry Statuses

| Method | Entry status |
|---|---|
| BARO | `READY` |
| TraceRCA | `EXECUTION_QUALIFIED_WITH_NATIVE_F-A` |
| mmBARO | `PENDING_OFFICIAL_RE2_PATH_SMOKE` |

## 6. Exit Rule

P6-G1H is evaluated separately from historical P6-G1. It can be GO only when
BARO is READY, TraceRCA is execution-qualified with explicit native F-A
handling, mmBARO is ready on the official RE2 metric+log path (or has an
equivalent explicit native F-A state), the firewall passes, and clean RCAEval
remains unchanged.
