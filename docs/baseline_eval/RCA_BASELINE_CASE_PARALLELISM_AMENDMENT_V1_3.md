# RCAEval Within-Method Case Parallelism Amendment V1.3

Status: **AUTHORIZED — PERFORMANCE-BLIND ORCHESTRATION-ONLY ACCELERATION**
Date: 2026-09-01
Scope: CIRCA and MicroCause confirmatory execution

## 1. Motivation

The CIRCA and MicroCause A1 attempts reached the RE2-TT dataset with recent
per-case wall times concentrated near the frozen 3,600-second deadline. The
existing harness owns one method-level process lock but dispatches exactly one
case worker at a time. Consequently, independent cases consume their deadlines
serially even though their predictive inputs and outputs are disjoint.

The user authorized within-method case parallelism on 2026-09-01. This
amendment changes orchestration and runtime accounting only. It does not change
the baseline implementations, inputs, preprocessing, candidate registries,
seeds, native output validation, adapters, timeout, failure policy, or metric
rules.

## 2. A1 disposition and A2 identity

The active `circa-a1-20260830` and `microcause-a1-20260831` processes must be
stopped before any A2 process starts. Every A1 terminal record present after
the original process has stopped is immutable execution evidence. A1 records
must not be deleted, overwritten, retried, or resumed under V1.3.

The authorized replacement attempts start from case 1:

- `circa-a2-20260901`;
- `microcause-a2-20260901`.

Both A2 attempts use exactly four case-worker slots. A new execution commit is
required, while each method reuses its unchanged frozen Python environment.
Each frozen environment identity includes its assigned worktree's absolute
`PYTHONPATH`. Therefore, after A1 stops and its evidence is committed, the
coordinator must merge V1.3 into that same assigned worktree and may rename its
task branch for A2. Moving A2 to a new worktree path or rewriting the
environment manifest is prohibited.

## 3. Deterministic parallel scheduler

One top-level runner continues to own the existing shared method lock. The
runner preloads four method servers sequentially within that lock, avoiding
unsafe simultaneous cold imports in pinned third-party libraries; after all
four report ready, their case workers run concurrently. Canonical cases
remain ordered as RE2-OB followed by RE2-TT and by each frozen manifest order;
case at zero-based canonical index `i` is assigned to worker slot `i mod 4`.
Each slot processes its assigned shard serially, while the four slots execute
concurrently.

Every case still runs in a fresh forked child, is seeded with canonical seed
`20260830`, receives the same read-only inputs, writes only its unique atomic
record path, and is independently terminated at 3,600 seconds. There is no
retry or work stealing. A framework failure stops further scheduling and all
records already written remain evidence.

Different methods may continue to overlap in their separate linked worktrees.
No second top-level runner for the same method may overlap with an A2 runner.

## 4. Runtime accounting

Every A2 terminal case record includes:

- `start_timestamp` and `end_timestamp` in UTC;
- monotonic `wall_time_seconds` covering that case worker's legal input load,
  native call, adapter, and record construction, or the parent-observed timeout;
- `execution_worker_count` fixed to `4`;
- `execution_worker_slot` in `0..3`.

After all 180 terminal records exist, the runner writes an attempt runtime
summary under `artifacts/baseline_eval/execution_v1/runtimes/`. The summary
contains the runner's actual wall time, the sum of all case wall times, dataset
subtotals, and one operational timing row per case. The method prediction lock
binds the summary path and SHA-256 digest. These runtime fields are operational
only and may not contain labels, rankings, roots, or evaluation metrics.

## 5. CPU and GPU controls

The frozen worker environment remains CPU-only for these methods:
`CUDA_VISIBLE_DEVICES` stays empty and OMP, MKL, OpenBLAS, and NumExpr remain
limited to one thread per case worker. GPU execution is not authorized because
the pinned PCMCI and PC paths have no frozen GPU implementation. Four-way
case-process parallelism supplies the acceleration without changing native
algorithm semantics.

Each A2 container must have at least four dedicated CPU cores and sufficient
memory for four simultaneous cases. If the platform cannot provide those
resources, do not silently lower worker count or alter the timeout; stop before
real execution and amend the protocol.

Final decision: `CIRCA_MICROCAUSE_FOUR_WAY_CASE_PARALLELISM_AUTHORIZED_V1_3`.
