# RCAEval Confirmatory Baseline Execution Status and Handoff

Status: **IN PROGRESS — CIRCA/MICROCAUSE A2 PREFLIGHTS REPAIRED; LAUNCH READY**
State revision: `2026-09-01.4`
Last operational audit: 2026-09-01 17:03, Asia/Shanghai
Branch: `evaluation/rcaeval-baselines`  
Last synchronized central commit: `c1c7a96`

This is the canonical operational handoff for the RCAEval confirmatory
baseline work. Read it at the start of every new session and update it after
every completed task that changes code, environments, artifacts, execution
coverage, locks, blockers, or the next plan.

The frozen protocol documents remain authoritative for scientific semantics.
If this status document conflicts with committed artifacts or a fresh read-only
audit, stop execution, resolve the discrepancy without inspecting prediction
contents, and update this document.

## 1. Required reading order

1. repository-root `AGENTS.md`;
2. this status and handoff document;
3. `RCA_BASELINE_PROTOCOL_FREEZE_V1.md`;
4. `RCA_BASELINE_ADAPTER_SPEC_V1.md`;
5. `RCA_BASELINE_EXECUTION_MATRIX_V1.md`;
6. `RCA_BASELINE_FAILURE_POLICY_V1.md`;
7. `RCA_BASELINE_PERFORMANCE_FIREWALL_V1.md`;
8. `RCA_BASELINE_PARALLEL_EXECUTION_AMENDMENT_V1_1.md`;
9. `RCA_BASELINE_TRACE_CSV_PARSER_AMENDMENT_V1_2.md`;
10. `RCA_BASELINE_CASE_PARALLELISM_AMENDMENT_V1_3.md`;
11. `RCA_BASELINE_PARALLEL_RUNBOOK_V1_1.md`; and
12. `RCA_BASELINE_ENVIRONMENTS.md`.

## 2. Frozen repository and provenance

| Item | Frozen/current value | Status |
|---|---|---|
| Required branch | `evaluation/rcaeval-baselines` | PASS |
| Push state for this revision | V1.3 acceleration is local | PENDING PUSH |
| Required starting HEAD | `54b403ff0441c318817818abeda13526652ae1d2` | ancestor present |
| Ada-RCA Scientific V1 | `bed295326e567395e725caa82840a534dcc0b1de` | immutable |
| Evidence-closure reference | `9342e06db91945be2e44703437229ba45b18bda8` | frozen |
| RCAEval checkout | `/home/zhangll24/RCA_project/RCAEval-clean` | clean |
| RCAEval commit | `5e96b700445bfb5c599e505ecf37d53bf847bbeb` | PASS |
| Protocol digest | `aa4f03363e1347a4b4e3c6427fd846be80452f025c3a6d08042ed6f6de0a849e` | frozen |
| Input-manifest digest | `b8280866432cdd494825cf831d2a73d2fe157de0ecd8801347953172e1ab43ec` | frozen |

The `.gitignore` change was re-audited. It does **not** add ignore patterns; it
only removes the final newline from the existing `artifacts/cache/` line. On
2026-08-31 the user explicitly accepted this state and authorized selective
future ignore additions only for files that are not execution evidence. The
change is included in recovery-readiness commit `3bedcb5`. The CIRCA execution
records remain intentionally untracked evidence until a valid method lock can
be produced; they are not ignored.

## 3. Environment migration status

Environment migration is complete. New virtual environments live outside all
project worktrees under `~/.venvs/`.

| Method | Environment/interpreter | Python | Key dependency | Current state |
|---|---|---|---|---|
| BARO | project `.venv/bin/python` | 3.10.20 | historical frozen stack | environment valid; execution complete |
| CIRCA | project `.venv/bin/python` | 3.10.20 | historical frozen stack | A1 retained; repaired A2 preflight passes; four-worker launch ready |
| MicroCause | `~/.venvs/ada-rca-baselines-microcause/bin/python` | 3.10.20 | `tigramite==4.2.2.1` | A1 retained; repaired A2 preflight passes; four-worker launch ready |
| MicroRank | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | Tigramite 5.2.10.1 in common stack | frozen on task branch; A1 retained; repaired A2 ready |
| TraceRCA | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | common stack | repaired A2 complete and method-locked on task branch |
| mmBARO | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | common stack | repaired A2 complete and method-locked on task branch |
| CausalRCA | no active confirmatory environment | — | saved GPU amendment only | explicitly deferred; do not freeze or run |

Activation commands:

```bash
source ~/.venvs/ada-rca-baselines-common/bin/activate
source ~/.venvs/ada-rca-baselines-microcause/bin/activate
```

The project-local `.venv` remains part of the historical BARO/CIRCA evidence
and must not be removed or replaced. Full activation, recreation, and routing
details are in `RCA_BASELINE_ENVIRONMENTS.md`.

## 4. Implementation and validation completed

| Work item | Commit | State |
|---|---|---|
| Frozen adapter/protocol audit | `b777f15` through `f7dcd8d` | complete |
| Performance firewall | `54b403f`, `2d9e96e` | complete |
| Original sequential execution harness | `e056958` | superseded for cross-method scheduling only |
| Parallel execution amendment and method-isolated harness | this revision | complete; task launch pending |
| Frozen input manifest | `5b3d944` | complete |
| BARO environment freeze | `5018f5d` | complete |
| BARO label-free prediction lock | `fbfb6e6` | complete |
| CIRCA environment freeze | `d5d837e` | complete |
| Later-baseline preflight hardening | `5ae9ebb` | complete |
| External environment documentation | `1529f4b` | complete and merged into this branch |
| Read-only later-method environment preflight | `6b01649` | complete |
| Environment/preflight guide update | `1a7718c` | complete |
| Canonical execution status/handoff | `a5ea541` | complete |
| Later-baseline execution-integrity hardening | `c51d37a` | complete |
| Later-baseline data/graph contract validation | `0d0efcf` | complete |
| Raw-trace CSV parser repair and V1.2 amendment | `f072c2a` | complete; central and affected task branches integrated |
| Four-way case scheduler, runtime summary, and V1.3 amendment | this revision | implementation complete; A1 stop and A2 launch pending |
| Frozen-environment/preflight stabilization | `c1c7a96` | complete; merged as `83e2df7` (CIRCA) and `60a346a` (MicroCause) |
| Deferred CausalRCA GPU work | branch `wip/causalrca-gpu-amendment`, commit `89db7ec` | saved only; not authorized for execution |

The read-only command below performs dependency identity collection, two
synthetic predictions, clean-checkout import verification, and OB/TT schema
checks. It writes no artifact and does not authorize real execution:

```bash
python scripts/run_baseline_confirmatory.py preflight-environment \
  --method <METHOD> \
  --python <ABSOLUTE_EXTERNAL_PYTHON>
```

Verified synthetic fingerprints:

| Method | Fingerprint | State |
|---|---|---|
| MicroCause | `594e370ebd9cbc7da54d97e8cd3d6fc0084961fd08bdb8ca3ef31b6e1df5a0ea` | two-run PASS |
| MicroRank | `8495edcc420230bc760d43bba175cec747bf2c0edda21ef5b5a80c4450e2a491` | two-run PASS |
| TraceRCA | `b56fedf7a64308ce1ba3f915712b3672ae029c060e319ff1d942628751dfb125` | two-run PASS |
| mmBARO | `233b5ca861daaaab6f39198b5244a1f858b6a753a74a1bed1812527029eaec49` | two-run PASS |

All four read-only preflights were repeated after `0d0efcf`; their fingerprints
remained identical to the values above. The stricter BARO method-lock verifier
also passed against all 180 frozen terminal records. Adapter-only input loading
for one opaque MicroRank case per dataset passed the real trace schema, digest,
timestamp-unit, and canonical-window checks without invoking the method.

The full suite for the V1.2 parser-repair revision passed with `193` tests.
This includes the actual 365,484-by-11 crashing trace in a subprocess, parser
scope enforcement, both amendment digests, same-method exclusion, different-
method concurrent locks, disjoint artifact paths, and shared Git-common lock
placement. The original failing case also reached `SUCCESS` for TraceRCA and
mmBARO with the repaired code; prediction contents were not inspected.

The V1.3 preflight repair passed the full suite with `203` tests. It resolves
the frozen user-site visibility profile from the complete committed environment
identity instead of inheriting a container's ambient `PYTHONNOUSERSITE` value.
The MicroCause synthetic-only random walk is bounded to 10 epochs and 100 steps;
the two-run fingerprint remains the frozen `594e370e...` value, while the exact
preflight completed in 12.1 seconds. CIRCA's exact two-run preflight completed
in 9.0 seconds. Real case invocations retain the native 1,000-by-1,000
MicroCause random walk.

## 5. Confirmatory execution coverage

Only operational state is recorded here. No prediction contents, labels, root
ranks, or metrics may be added before the global prediction lock.

| Method | Dataset | Records | SUCCESS | METHOD_FAILURE | ADAPTER_FAILURE | DATA_FAILURE | TIMEOUT | Method lock |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BARO | RE2-OB | 90/90 | 90 | 0 | 0 | 0 | 0 | valid |
| BARO | RE2-TT | 90/90 | 90 | 0 | 0 | 0 | 0 | valid |
| CIRCA A1 | RE2-OB | 90/90 | 86 | 4 | 0 | 0 | 0 | absent; retained |
| CIRCA A1 | RE2-TT | 27/90 | 8 | 2 | 0 | 0 | 17 | absent; retained |
| CIRCA A2 | RE2-OB | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; four-worker launch pending |
| CIRCA A2 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; four-worker launch pending |
| MicroCause A1 | RE2-OB | 90/90 | 87 | 1 | 0 | 2 | 0 | absent; retained |
| MicroCause A1 | RE2-TT | 10/90 | 0 | 0 | 0 | 0 | 10 | absent; retained |
| MicroCause A2 | RE2-OB | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; four-worker launch pending |
| MicroCause A2 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; four-worker launch pending |
| MicroRank A1 | RE2-OB | 59/90 | 59 | 0 | 0 | 0 | 0 | absent; retained |
| MicroRank A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; retain |
| MicroRank A2 | RE2-OB | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; ready |
| MicroRank A2 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; ready |
| TraceRCA A1 | RE2-OB | 59/90 | 59 | 0 | 0 | 0 | 0 | absent; retain |
| TraceRCA A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; retain |
| TraceRCA A2 | RE2-OB | 90/90 | 90 | 0 | 0 | 0 | 0 | valid on task branch |
| TraceRCA A2 | RE2-TT | 90/90 | 75 | 15 | 0 | 0 | 0 | valid on task branch |
| mmBARO A1 | RE2-OB | 59/90 | 57 | 0 | 0 | 2 | 0 | absent; retain |
| mmBARO A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; retain |
| mmBARO A2 | RE2-OB | 90/90 | 87 | 1 | 0 | 2 | 0 | valid on task branch |
| mmBARO A2 | RE2-TT | 90/90 | 90 | 0 | 0 | 0 | 0 | valid on task branch |
| CausalRCA | — | 0 | — | — | — | — | — | deferred |

BARO lock verification: `EXECUTION_COMPLETE`, 180 terminal record digests,
both 90-case denominators valid, environment unchanged.

CIRCA A1 and MicroCause A1 are stopped and committed as immutable evidence in
their assigned task worktrees. No A2 records or method locks exist, and no
runner process was observed at the latest audit.

## 6. Current blockers and decisions required

### B1. External A1 stop/archive — resolved

The user stopped both external A1 runners. CIRCA A1 is preserved in `ee98d7f`
and MicroCause A1 in `95dd037`. V1.3 and the preflight repair are merged into
the same path-bound worktrees. Their exact global and environment preflights
pass, so each A2 may now start from case 1 with exactly `--workers 4`. Never
resume either A1 and never overlap two top-level runners for the same method.

### B2. `.gitignore` decision — resolved

The user accepted the current no-final-newline state. It does not ignore the
execution artifact tree. Future ignore rules may be added selectively only for
non-evidence files; terminal records, locks, manifests, and execution logs must
remain visible to Git and the integrity workflow.

### B3. CausalRCA disposition — user decision recorded

On 2026-08-31 the user explicitly cancelled CausalRCA from the current
confirmatory baseline execution. Do not freeze or run it. Before the global
lock, encode this decision in a dedicated performance-blind protocol amendment
or equivalent protocol-level disposition. It must not be represented as a
technical method failure. The saved GPU implementation remains isolated on
`wip/causalrca-gpu-amendment` at `89db7ec` and is not part of this execution.

### B4. Cross-method concurrency — authorized

The user explicitly authorized different baselines to run concurrently in
separate task containers provided their experiment data cannot interfere. The
committed V1.1 amendment provides method-scoped environment, record, lock, and
branch ownership. Because containers share the filesystem, the coordinator
must pre-create one linked Git worktree and unique branch per method; two
containers must never use the same path. The harness stores per-method process
locks below the shared Git common directory rather than container-local
`/tmp`. Registry order is reporting order only. Each container must still have
adequate CPU and memory; reduce task concurrency if the platform does not
isolate physical resources.

### B5. Raw-trace native parser crash — repaired; A2 required

TraceRCA and mmBARO A1 deterministically stopped after 59 records on
`re2ob-f30e2feeaa5218b8`. Both child workers exited on signal 11 inside Pandas
2.3.3's C CSV parser while loading the valid raw trace source. The same file
has 365,484 rows and 11 fields per row and loads with Pandas' Python engine.

V1.2 limits the repair to `pandas.read_csv(..., engine="python")` for the
logical `traces` role. The package environment and all scientific semantics
remain unchanged. TraceRCA and mmBARO A1 must be archived and never resumed;
MicroRank A1 is also restarted prospectively because it shares the loader and
one attempt cannot mix execution commits. Authorized IDs are
`microrank-a2-20260901`, `tracerca-a2-20260901`, and
`mmbaro-a2-20260901`.

Central repair commit `f072c2a` passed 193 tests and global preflight. A1
evidence commits are `3c4c0d5` plus `8b1a15f` (MicroRank 59 records),
`37e288e` (TraceRCA 59 records), and `414140c` (mmBARO 59 records). Repair
cherry-picks are `2a66e75`, `65878d8`, and `7650588`, respectively.

The original MicroRank failure is now confirmed at the same opaque case and
same C-parser signal-11 path. A performance-blind repaired execution of that
full case reached `SUCCESS`; the A1 tail is committed, the task worktree is
clean, and both global and environment preflights pass. MicroRank A2 may start.
MicroCause does not load the raw `traces` role; all 180 frozen
`simple_metrics` CSVs loaded successfully with its isolated environment, so
its active A1 is not restarted for V1.2.
TraceRCA A2 commit `c7c8265` and mmBARO A2 commit `643cde4` each contain 180
terminal records and a method lock that passes `verify_method_lock`; central
integration remains pending.

## 7. Remaining parallel plan

MicroCause, MicroRank, TraceRCA, and mmBARO are independent worker tracks.
CIRCA recovery is a fifth independent legacy track. Central integration and
the global prediction lock remain a barrier after all tracks finish.

### P0 — Resolve repository transition readiness

- Completed: user accepted the `.gitignore` byte state; CIRCA evidence remains
  unignored and preserved.
- Completed: branch, protocol bundle, input manifest, Ada-RCA frozen paths, and
  clean pinned RCAEval checkout passed their preflights.
- Completed: the current full suite passed all 203 tests.
- Completed: both A1 attempts are archived and both A2 worktrees contain the
  same central repair commit.

### P0A — Finish performance-blind later-adapter hardening

- Completed in `0d0efcf`: structural graph-output validation for MicroCause
  and the other graph methods without changing native algorithms or ranking
  semantics.
- Completed in `0d0efcf`: real-input schema/type checks so pre-invocation
  malformed telemetry is consistently classified as `DATA_FAILURE`.
- Add symmetric deterministic synthetic tests for MicroCause, TraceRCA, and
  mmBARO where their method-specific environments permit it.
- Keep this work synthetic/schema-only; do not schedule a real later-method
  case and do not alter the frozen CIRCA attempt.

### P1 — Stop/archive CIRCA A1, then execute four-worker A2

- Completed: A1 stopped and its 117 terminal records are committed without a
  method lock; V1.3 and `c1c7a96` are merged into the same worktree.
- Completed: both preflights pass against the unchanged CIRCA environment.
- Next: start `circa-a2-20260901 --workers 4` from case 1.
- Commit all 180 records, the runtime summary, and method lock together.

### P2 — Stop/archive MicroCause A1, then execute four-worker A2

- Completed: A1 stopped and its 100 terminal records are committed without a
  method lock; V1.3 and `c1c7a96` are merged into the same worktree.
- Completed: both preflights pass against the unchanged MicroCause environment;
  the two-run synthetic fingerprint is unchanged.
- Next: start `microcause-a2-20260901 --workers 4` from case 1.
- Commit all 180 records, the runtime summary, and method lock together.

### P3 — Archive MicroRank A1, execute repaired A2, and lock

- A1 is completely archived by `3c4c0d5` plus `8b1a15f`; never resume it.
- V1.2 is integrated as `2a66e75`, the environment is unchanged, and both
  preflights pass.
- Run preflight, then start `microrank-a2-20260901` from case 1 under the common
  interpreter and fixed `PYTHONHASHSEED=20260830`.
- Commit the complete A2 records and method lock.

### P4 — Archive TraceRCA A1, execute repaired A2, and lock

- A1 remains immutable evidence and must not be resumed.
- A2 is complete and method-locked in task commit `c7c8265`; preserve raw
  trace microseconds, span-end filtering, and `t0*1_000_000`.
- Integrate the verified task commit centrally.

### P5 — Archive mmBARO A1, execute repaired A2, and lock

- A1 remains immutable evidence and must not be resumed.
- A2 is complete and method-locked in task commit `643cde4`; preserve the
  official `mm-ob` / `mm-tt` keys and frozen modality-specific preprocessing.
- Integrate the verified task commit centrally.

### P6 — Record CausalRCA cancellation

- Do not freeze or execute CausalRCA in the current confirmatory baseline.
- Add a dedicated performance-blind protocol amendment or protocol-level
  withdrawal disposition before the global lock.
- Keep the saved GPU branch and commit as non-executed context only.
- Update this document with the amendment path and commit.

### P7 — Global prediction lock

- Integrate every worker's environment commit before its prediction commit;
  worker-owned paths must remain disjoint.
- Require a committed, valid disposition for every method in the frozen order.
- Verify all method locks and terminal record digests.
- Create and commit `prediction_lock_v1.json`.
- Suggested commit: `eval: freeze complete label-free RCAEval baseline execution`.
- No label join is legal before this commit.

### P8 — Post-lock evaluation and reporting

- Join labels only after the committed global prediction lock.
- Never rerun a baseline during evaluation.
- Keep every failure in the 90-case dataset denominator with zero top-k utility.
- Report AC@1, AC@3, AC@5, and Avg@5; baseline MRR remains
  `NOT-IDENTIFIABLE`.
- Generate diagnostics and the P1/P2 scientific-disclosure report.
- Commit evaluation and reporting separately.
- Update this document with final artifact paths, commits, tests, push state,
  limitations, and final decision.

## 8. Safe new-session audit commands

Run these before taking action in a new conversation:

```bash
git status --short --branch
git log --oneline -12
git -C /home/zhangll24/RCA_project/RCAEval-clean status --short --branch
git -C /home/zhangll24/RCA_project/RCAEval-clean rev-parse HEAD
find artifacts/baseline_eval/execution_v1/environments -maxdepth 1 -type f -printf '%f\n' | sort
find artifacts/baseline_eval/execution_v1/locks -maxdepth 1 -type f -printf '%f\n' | sort
ps -eo pid,etimes,cmd | rg 'run_baseline_confirmatory|baseline_eval.server|baseline_eval.worker'
tmux list-sessions
```

Record inspection during B2-E/B2-L must select only opaque identity, terminal
status, lengths, counts, runtimes, and digests. Never print native/adapted
ranking contents or join labels while auditing progress.

## 9. Mandatory end-of-task synchronization

After every completed task:

1. update the state revision and audit date at the top of this file;
2. update repository/environment state if it changed;
3. update the execution coverage and lock status using operational fields only;
4. mark completed plan items and rewrite the immediate next action;
5. record new artifact paths, test results, commit subjects, and push state;
6. run `git diff --check` on edited files;
7. include this document in the task's logical commit, or make an immediate
   follow-up documentation commit; and
8. push the branch when the active workflow authorizes pushing.

If a task is purely diagnostic and changes no repository or execution state,
update this document only when the diagnosis changes a blocker, decision, or
next action. Do not add prediction contents, labels, ranks, or pre-lock metrics
to this handoff.
