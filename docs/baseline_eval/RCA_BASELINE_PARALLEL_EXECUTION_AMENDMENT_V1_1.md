# RCAEval Baseline Parallel Execution Amendment V1.1

Status: **AUTHORIZED — PERFORMANCE-BLIND EXECUTION-ONLY AMENDMENT**  
Date: 2026-08-31  
Supersedes: the cross-method serialization rule in the V1 execution harness
and operational handoff

## 1. Scope and invariants

This amendment authorizes different RCAEval baseline methods to run in
parallel. It changes orchestration only. The frozen datasets, case order,
adapters, windows, seeds, timeout, failure policy, candidate projection,
denominators, metric legality, RCAEval source commit, and Ada-RCA V1 remain
unchanged. The V1 protocol digest and protocol-bundle digest therefore remain
valid, including for the completed BARO run and the in-progress legacy CIRCA
attempt.

`METHOD_ORDER` remains the stable registry and reporting order. It is not an
execution dependency. MicroCause, MicroRank, TraceRCA, and mmBARO may be
frozen and run without a committed lock from the preceding registry entry.
CausalRCA remains cancelled by the recorded user decision; RCD and all
context-only methods remain unauthorized.

## 2. Isolation contract

Each concurrent method must run in its own task container and Git working copy,
starting from the same committed parallel-harness revision. A task owns exactly
one method and may write only its method-scoped paths:

- `artifacts/baseline_eval/execution_v1/environments/<method>.json`;
- `artifacts/baseline_eval/execution_v1/records/<method>/<attempt-id>/...`; and
- `artifacts/baseline_eval/execution_v1/locks/<method>_prediction_lock.json`.

Frozen inputs, the input manifest, protocol artifacts, Ada-RCA artifacts, and
`/home/zhangll24/RCA_project/RCAEval-clean` are read-only. A worker task must
not create the global prediction lock, join labels, evaluate results, edit the
canonical execution-status document, or write another method's paths.

Different methods use different process-lock files and may overlap. Two
processes for the same method may not overlap, even in different working
copies on the same host. Within a method, RE2-OB and RE2-TT remain one
canonical attempt, use one frozen environment, and execute in frozen dataset
and case order.

Container separation must also provide enough CPU and memory for each method.
If the platform shares and throttles physical resources, reduce the number of
simultaneous tasks rather than changing the 3,600-second timeout or retrying
based on outcomes. Resource or framework failures remain evidence under the
frozen failure policy.

## 3. Environment and provenance

The task must activate the method-specific external environment, run the
read-only preflight, freeze the method environment, and commit that manifest
before the first real case. Every method's 180 records must share the same
attempt ID, environment/input/protocol digests, candidate registries, and
execution commit. Resume is legal only in the same task working copy at the
exact original execution commit.

The branch name is operational metadata, not scientific identity. A clean
branch or detached task checkout is valid when it descends from the required
starting commit and contains this committed amendment. The recorded execution
commit and artifact digests remain authoritative.

## 4. Parallel merge and global barrier

Each task produces two reviewable commits: first the method environment
manifest, then the method records plus method prediction lock. Because all
owned artifact paths are method-scoped, those commits can be integrated into
the central evaluation branch without data-path overlap. Resolve no conflict
by discarding or regenerating execution evidence.

After all method commits are integrated, the central coordinator verifies
every method lock and terminal-record digest, records the non-executed
CausalRCA disposition, updates the canonical status document, and creates the
global prediction lock. Label joins and metrics remain forbidden until that
global lock is committed. Parallel completion order must not influence method
selection, reruns, adapters, or reporting order.

## 5. Legacy CIRCA attempt

The existing `circa-a1-20260830` attempt remains bound to its original
environment and execution commit. It may be resumed only under its existing
recovery rules. Its legacy global process lock does not block newly authorized
methods running in separate containers, and the new harness must not rewrite
or migrate any CIRCA record.

Final decision: `BASELINE_CROSS_METHOD_PARALLEL_EXECUTION_AUTHORIZED_V1_1`.
