# RCAEval Baseline Rescue V2.2 Implementation Amendment

Status: **FROZEN IMPLEMENTATION CORRECTION — PERFORMANCE-BLIND**  
Date: 2026-09-03 (Asia/Shanghai)

This amendment records infrastructure corrections discovered while exercising
the frozen V2 rescue implementation. It is an execution-rescue amendment, not
a performance-driven method change. It does not replace or alter the V2.1
scientific protocol, its dataset scope, its metric definitions, its candidate
semantics, or its protocol digest.

## 1. Scientific boundary

The following remain frozen:

- the five-method scope: CIRCA, MicroCause, MicroRank, TraceRCA, and mmBARO;
- RE2-OB and RE2-TT, with 90 cases per dataset and separate reporting;
- the pinned RCAEval checkout and commit;
- all native baseline algorithms, parameters, graph/ranking behavior, and
  label-independent adapters;
- Ada-RCA Scientific V1, frozen predictions, and evidence artifacts;
- the performance firewall and the requirement for a committed global
  prediction lock before any label join or metric computation.

In particular, MicroCause real-case execution still uses the pinned native
`1000 epochs x 1000 walk steps`. Only the synthetic preflight's already
authorized bounded smoke input remains bounded; no native real-case parameter
is changed.

## 2. Corrections

### 2.1 V2 preflight and server startup are genuinely no-timeout

The V2 protocol/environment synthetic preflight previously inherited a 900
second subprocess timeout. A cold import of a pinned native module can exceed
that interval even though no real case is being killed. V2 now passes
`timeout=None` for both synthetic preflight calls. The V2 case server's native
import readiness wait also uses an unbounded wait. The real-case server already
uses `process.join()` with no case wall-clock timeout.

The V2 CLI still requires an explicit `--no-timeout` (or equivalent
`--case-timeout none`) for real execution. Heartbeats and resource fields remain
observational and never kill a long-running case.

The V1 compatibility helper retains its historical default when called outside
the V2 path; this amendment does not rewrite V1 execution behavior or evidence.

### 2.2 Nested blocking-status validity

V2 stores blocking status counts under dataset keys. The previous lock builder
tested the outer mapping for truthiness, so even
`{"re2ob": {}, "re2tt": {}}` was incorrectly classified as
`INTEGRITY_INVALID`. Validity now depends only on nonzero counts of
`DATA_FAILURE`, `ADAPTER_FAILURE`, `ENVIRONMENT_FAILURE`,
`INPUT_INTEGRITY_FAILURE`, `PROCESS_CRASH/OOM`, or `TIMEOUT`.

`METHOD_FAILURE` remains a legal terminal observation and does not by itself
invalidate a method lock. It remains zero utility only at the post-lock metric
stage.

### 2.3 Immutable lock re-attestation

A method lock produced by the pre-correction builder is historical evidence and
is not overwritten. After the complete terminal record set and runtime summary
are verified, the corrected attestation is written to the distinct sidecar:

`artifacts/baseline_eval/execution_v2/locks/<method>_prediction_lock_reissued_v2.json`

The sidecar binds the original lock's internal `lock_digest`, preserves the
record/runtime/source/environment bindings, and is selected as the active lock
only after it passes full verification. The earlier reissue sidecar, if
present, is also retained as immutable evidence. The global lock binds the
active corrected sidecar path and its file digest; no prediction content is
opened by this repair.

## 3. Performance-blind operational disposition

At amendment recording time:

| Method | V2 operational state | Disposition |
|---|---|---|
| CIRCA | OB 90 terminal (86 `SUCCESS`, 4 `METHOD_FAILURE`); TT 1 terminal (`METHOD_FAILURE`); 89 cases missing; no runtime or lock | resume missing cases after container memory increase, on the original attempt commit |
| MicroCause | V2 synthetic preflight passed after the no-timeout correction; V2 environment frozen; no real case records | run determinism preflight, then the authorized no-timeout full attempt |
| MicroRank | 180 terminal records; OB 90 `SUCCESS`; TT 75 `SUCCESS` and 15 `METHOD_FAILURE` | no rerun; corrected immutable lock sidecar verified |
| TraceRCA | 180 terminal records; OB 90 `SUCCESS`; TT 75 `SUCCESS` and 15 `METHOD_FAILURE` | no rerun; corrected immutable lock sidecar verified |
| mmBARO | 180 terminal records; OB 90 `SUCCESS`; TT 89 `SUCCESS` and 1 `METHOD_FAILURE` | no rerun; corrected immutable lock sidecar verified |

These are status counts only. No root labels, rankings, correctness values,
AC/Avg@5, MRR, or method comparison was inspected for this disposition.

## 4. Required next transition

1. CIRCA must resume only missing records with the same
   `circa-a3-rescue-v2` attempt and the exact execution commit recorded in its
   attempt metadata. Existing terminal records, including
   `METHOD_FAILURE`, are not retried.
2. MicroCause must use its frozen isolated environment, deterministic
   worker-count preflight, and native real-case invocation without a timeout.
3. MicroRank, TraceRCA, and mmBARO do not rerun their complete attempts. Their
   corrected sidecars may be integrated after central verification.
4. A global prediction lock remains prohibited until all five active method
   locks are complete and integrity-valid. Metric evaluation remains prohibited
   until that lock is committed.

The exact operational commands are maintained in
`RCA_BASELINE_RESCUE_RUNBOOK_V2.md` and the canonical status handoff.
