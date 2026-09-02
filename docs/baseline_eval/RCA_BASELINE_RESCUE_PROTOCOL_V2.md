# RCAEval Five-Baseline Completion Rescue Protocol V2

Status: **FROZEN — PERFORMANCE-BLIND EXECUTION RESCUE / INFRASTRUCTURE AMENDMENT**  
Date: 2026-09-03  
Supersedes: none; V1 and all V1.x evidence remain immutable

This document authorizes an execution-completeness rescue for exactly five
RCAEval baselines. It changes orchestration, input-integrity diagnostics,
recording, recovery, and post-lock reporting. It is not a performance-driven
method selection, parameter search, adapter search, or baseline algorithm
modification.

The machine-readable companion is
`artifacts/baseline_eval/rescue_protocol_v2.json`. Its SHA-256 is the V2
protocol digest bound by every V2 environment, record, method lock, global
lock, and evaluation artifact.

## 1. Frozen scientific boundary

Ada-RCA Scientific V1, its training, features, folds, ranking, frozen
predictions, metrics, `artifacts/p6_*`, and evidence-closure artifacts are
read-only. The pinned RCAEval checkout is read-only at commit
`5e96b700445bfb5c599e505ecf37d53bf847bbeb`.

V2 invokes the pinned RCAEval callables. It does not copy, reimplement, tune,
or replace any baseline algorithm. The only selected methods are:

`CIRCA`, `MicroCause`, `MicroRank`, `TraceRCA`, and `mmBARO`.

BARO is retained only as historical evidence and is not rerun. CausalRCA is
withdrawn/deferred by explicit user decision and is not reintroduced. RCD,
mmRCD, multi-source CIRCA, PDiagnose, and all other methods are out of scope.

## 2. Case universe and dataset reporting

The case universe is exactly the frozen 90 cases in each of `RE2-OB` and
`RE2-TT`. Each V2 method attempt covers both datasets in the frozen manifest
order. Dataset scores are always reported separately; a pooled 180-case
headline score is prohibited.

The source window remains the half-open `[t0-600s,t0+600s)` window. Existing
V1 metric, raw-trace, timestamp, candidate, and service-projection semantics
remain in force. Candidate completion is `NONE`.

## 3. MicroCause non-modification freeze

Real-case MicroCause calls use the exact pinned RCAEval implementation and
native parameters, including PCMCI `tau_max=10`, `pc_alpha=0.1`, link
`alpha_level=0.001`, `rho=0.2`, `lambda=0.5`, and native random walk
`1000 epochs × 1000 walk steps`. No parameter, graph, feature, ranking, or
random-walk change is allowed. The existing bounded random walk is permitted
only inside synthetic preflight and is never active in a real-case call.

## 4. Execution model

Each task container owns exactly one method and one V2 attempt spanning OB and
TT. The V2 attempt IDs are fixed to:

| Method | Attempt ID |
|---|---|
| CIRCA | `circa-a3-rescue-v2` |
| MicroCause | `microcause-a3-rescue-v2` |
| MicroRank | `microrank-a3-rescue-v2` |
| TraceRCA | `tracerca-a3-rescue-v2` |
| mmBARO | `mmbaro-a3-rescue-v2` |

Every task uses its own linked worktree, branch, environment manifest, record
directory, runtime summary, and method lock. V2 writes only below
`artifacts/baseline_eval/execution_v2/<method-scoped path>`. V1/A1/A2 paths are
never edited, resumed, or overwritten.

The scheduler supports requested worker counts 1, 4, 10, and 20. Actual
workers are `min(requested_workers, available_cpu_count)`. A requested count
is never silently exceeded. Each case executes in an independent child
process; a worker slot processes its assigned cases serially. Case assignment
is deterministic round-robin over the selected canonical order.

Each child starts with `PYTHONHASHSEED=20260830` and resets Python, NumPy, and
applicable Torch state to seed `20260830`. Numeric-library thread pools are
limited to one thread per case process:

`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, and
`NUMEXPR_NUM_THREADS=1`.

## 5. No-timeout and monitoring policy

V2 real-case execution is explicitly no-timeout: `timeout_seconds = None`.
There is no wall-clock kill, pseudo-infinite timeout, automatic retry, work
stealing, or performance-based termination. A task container may still be
stopped externally.

Every terminal record includes method, dataset, opaque case ID, attempt ID,
worker ID/slot, child PID, UTC start and finish timestamps, monotonic elapsed
seconds, terminal status, environment digest, source-record digests, and
native-module digest. Peak RSS and CPU time are recorded when the platform
provides them. A non-killing heartbeat may report active worker/process state.

## 6. Resume and immutability

The first V2 invocation creates immutable attempt metadata containing the
execution commit, environment/input/protocol digests, worker configuration,
and no-timeout policy. `--resume` is legal only for that same attempt, same
worktree, same execution commit, same environment, same input manifest, same
worker configuration, and before a method lock exists.

Resume validates every existing terminal record and schedules only missing
case IDs. Existing `SUCCESS`, `METHOD_FAILURE`, `DATA_FAILURE`,
`ADAPTER_FAILURE`, `ENVIRONMENT_FAILURE`, `INPUT_INTEGRITY_FAILURE`, and
`PROCESS_CRASH/OOM` records are never rerun. `METHOD_FAILURE` is never
automatically retried. A completed old attempt or lock is never modified.

## 7. V2 terminal semantics

Every scheduled case has exactly one terminal record. V2 distinguishes:

| Status | Meaning in V2 evaluation |
|---|---|
| `SUCCESS` | Valid native output, legal service projection, persisted record |
| `METHOD_FAILURE` | Legal input reached pinned native method, which raised, returned invalid/empty output, or triggered an audited native fallback; contributes zero utility in the robustness-adjusted 90-case view |
| `DATA_FAILURE` | Source is unreadable, malformed, schema-invalid, nonnumeric/nonfinite, or has an empty canonical window |
| `ADAPTER_FAILURE` | Native output is valid but cannot be legally projected/persisted under the frozen service adapter |
| `ENVIRONMENT_FAILURE` | Runtime/dependency/deterministic-control/preflight environment failure |
| `INPUT_INTEGRITY_FAILURE` | Case/source/manifest/provenance identity or digest mismatch |
| `PROCESS_CRASH/OOM` | Child process exited abnormally, including signal crash or OOM-like termination |
| `TIMEOUT` | Historical compatibility status only; V2 no-timeout runs must not create it |

`DATA_FAILURE`, `ADAPTER_FAILURE`, `ENVIRONMENT_FAILURE`, and
`INPUT_INTEGRITY_FAILURE` are invalid/incomplete for formal comparison and
block the affected method × dataset evaluation. `PROCESS_CRASH/OOM` is
reported separately and also blocks formal evaluation by default. It is never
silently converted to `METHOD_FAILURE` or zero. `TIMEOUT` is likewise a block
if present in a V2 attempt.

## 8. Failure-free input rescue decisions

The two historical mmBARO OB `DATA_FAILURE` cases are diagnosed using path,
existence, byte size, SHA-256, frozen manifest expectation, parser, schema,
dtype, numeric/finiteness, timestamp units, canonical-window, and derived
telemetry checks. The source is not regenerated and the manifest is not
rewritten. If a V2 run reports any remaining data/integrity defect, no global
lock or metric evaluation is legal until the defect is repaired by a new
protocol-preserving attempt.

The historical MicroRank/TraceRCA TT failure sets are compared using only
opaque case identity and label-free operation-set diagnostics. A trace-closure
probe found no additional operation evidence in the affected frozen sources,
and the unseen post-event operation condition persists. V2 therefore does not
adopt trace closure or an extended normal-SLO history. The canonical trace
adapter and pinned native SLO semantics remain unchanged; legitimate native
`KeyError`/other method failures remain `METHOD_FAILURE`.

## 9. Lock barrier and performance firewall

V2 method locks bind all 180 terminal-record digests, attempt metadata,
environment and source digests, candidate registries, RCAEval commit, adapter
version, worker configuration, and no-timeout policy. The central V2 global
prediction lock is created only after all five method locks are integrated and
verified with integrity-valid status counts. It binds the five lock digests and
attempt IDs and contains no labels or metrics.

No root label, root rank, correctness, AC, Avg@5, MRR, method difference, or
prediction content may be printed during execution, diagnosis, preflight, or
lock creation. Digests, lengths, statuses, exception classes, sanitized error
categories, timestamps, and resource facts are allowed. Label joins are
performed only by the post-lock evaluator after the committed V2 global lock.

## 10. Unified evaluation

The primary table reports, separately for OB and TT:

`AC@1`, `AC@3`, `AC@5`, and `Avg@5`.

For a dataset with `N=90`, a `SUCCESS` case uses the first-five adapted
service prefix; a legal `METHOD_FAILURE` uses zero utility. AC@2 and AC@4
may be retained internally. Baseline MRR is always
`NOT-IDENTIFIABLE`; no candidate completion or artificial full ranking is
allowed. Ada-RCA values are loaded from and identity-checked against frozen
Scientific V1 evidence; Ada-RCA is not retrained.

Fault-level output is separate for CPU, MEM, DISK, SOCKET, DELAY, and LOSS,
with case count, AC@1, AC@3, AC@5, and Avg@5. A missing fault category is
`N/A`, never a zero or divide-by-zero omission.

The robustness table reports at least SUCCESS, METHOD_FAILURE, DATA_FAILURE,
ADAPTER_FAILURE, and PROCESS_CRASH/OOM, with environment, input-integrity,
and historical timeout statuses retained when present. Paired fault-stratified
bootstrap is available only after the V2 global lock, with 10,000 resamples and
seed `20260827`, primary `Δ Avg@5`, secondary `Δ AC@1`, and OB/TT analyzed
separately.

## 11. Required execution order

`five full executions → five method locks → central integration → committed
V2 global prediction lock → label join → metric evaluation → report`.

This V2 amendment ends in the state `V2_RESCUE_CODE_READY — FIVE
TASK-CONTAINER EXECUTIONS PENDING`; it does not claim baseline completion or
performance results.
