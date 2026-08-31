# RCAEval Confirmatory Baseline Execution Status and Handoff

Status: **IN PROGRESS — RAW-TRACE PARSER REPAIR VALIDATED**
State revision: `2026-09-01.1`
Last operational audit: 2026-09-01, Asia/Shanghai
Branch: `evaluation/rcaeval-baselines`  
Last synchronized central commit: `ec66f6c` (V1.2 repair pending commit)

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
10. `RCA_BASELINE_PARALLEL_RUNBOOK_V1_1.md`; and
11. `RCA_BASELINE_ENVIRONMENTS.md`.

## 2. Frozen repository and provenance

| Item | Frozen/current value | Status |
|---|---|---|
| Required branch | `evaluation/rcaeval-baselines` | PASS |
| Push state for this revision | V1.1 is local at `ec66f6c`; V1.2 repair is pending commit | PENDING REVIEW / MERGE / PUSH |
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
| CIRCA | project `.venv/bin/python` | 3.10.20 | historical frozen stack | environment valid; attempt incomplete; never migrate mid-attempt |
| MicroCause | `~/.venvs/ada-rca-baselines-microcause/bin/python` | 3.10.20 | `tigramite==4.2.2.1` | frozen on task branch; A1 incomplete |
| MicroRank | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | Tigramite 5.2.10.1 in common stack | frozen on task branch; A1 retained, repaired A2 required |
| TraceRCA | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | common stack | frozen on task branch; A1 parser crash, repaired A2 required |
| mmBARO | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | common stack | frozen on task branch; A1 parser crash, repaired A2 required |
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
| Raw-trace CSV parser repair and V1.2 amendment | this revision | implementation and regression validation complete; commit pending |
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

## 5. Confirmatory execution coverage

Only operational state is recorded here. No prediction contents, labels, root
ranks, or metrics may be added before the global prediction lock.

| Method | Dataset | Records | SUCCESS | METHOD_FAILURE | ADAPTER_FAILURE | DATA_FAILURE | TIMEOUT | Method lock |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BARO | RE2-OB | 90/90 | 90 | 0 | 0 | 0 | 0 | valid |
| BARO | RE2-TT | 90/90 | 90 | 0 | 0 | 0 | 0 | valid |
| CIRCA | RE2-OB | 90/90 | 86 | 4 | 0 | 0 | 0 | absent |
| CIRCA | RE2-TT | 10/90 | 3 | 1 | 0 | 0 | 6 | absent |
| MicroCause A1 | RE2-OB | 6/90 | 5 | 0 | 0 | 1 | 0 | absent |
| MicroCause A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent |
| MicroRank A1 | RE2-OB | 12/90 | 12 | 0 | 0 | 0 | 0 | absent; retain |
| MicroRank A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; retain |
| TraceRCA A1 | RE2-OB | 59/90 | 59 | 0 | 0 | 0 | 0 | absent; retain |
| TraceRCA A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; retain |
| mmBARO A1 | RE2-OB | 59/90 | 57 | 0 | 0 | 2 | 0 | absent; retain |
| mmBARO A1 | RE2-TT | 0/90 | 0 | 0 | 0 | 0 | 0 | absent; retain |
| CausalRCA | — | 0 | — | — | — | — | — | deferred |

BARO lock verification: `EXECUTION_COMPLETE`, 180 terminal record digests,
both 90-case denominators valid, environment unchanged.

CIRCA attempt: `circa-a1-20260830`. Provenance-consistent recovery started at
2026-08-31 19:31:48 Asia/Shanghai from the original repository path on branch
`recovery/circa-a1-20260830` at exact execution commit `d5d837e`. Before the
resume, all 99 existing records were revalidated and a separate recovery copy
was confirmed byte-identical. The first missing case reached the frozen
3,600-second deadline and was persisted as `TIMEOUT`, bringing coverage to
100/180. At the latest audit a CIRCA recovery runner/server was observed; the
attempt still has no prediction lock. Do not launch a duplicate. The V1.1
amendment permits different methods to run in isolated containers while CIRCA
remains incomplete.

## 6. Current blockers and decisions required

### B1. CIRCA recovery — independent incomplete task

The existing CIRCA attempt is incomplete but its environment remains valid.
It no longer gates other methods under the V1.1 parallel amendment.

Before any recovery action, re-audit:

- branch and Git identity;
- process/tmux state;
- exact record counts and terminal-status counts only;
- CIRCA environment digest and current environment identity;
- input/protocol/RCAEval identities; and
- absence of a CIRCA prediction lock.

Resuming the same attempt may only continue missing cases with the same frozen
environment, attempt ID, and exact execution commit `d5d837e`. It must not
rerun or replace any persisted failure or timeout. The current branch HEAD
cannot legally issue that resume. A controlled recovery must either execute in
the original committed code context while preserving and re-verifying the 99
records, or retain the attempt and follow a reviewed new-attempt disposition.
On 2026-08-31 the user explicitly authorized recovery and allowed a full rerun
only if the provenance-consistent resume path proves impractical. Because all
99 persisted records validate and no systematic framework defect has been
established, the selected path is same-attempt recovery at exact commit
`d5d837e`. An isolated worktree copy was byte-for-byte verified, but the frozen
environment identity binds the original repository path through `PYTHONPATH`.
The formal resume therefore runs from the original path on the dedicated
recovery branch. The environment gate was not bypassed or modified.

The historical command below is valid only from the exact original execution
commit context after a fresh read-only audit and explicit user authorization:

```bash
./.venv/bin/python scripts/run_baseline_confirmatory.py run-method \
  --method CIRCA \
  --attempt-id circa-a1-20260830 \
  --resume
```

If a systematic framework defect is established instead, retain the entire
attempt and follow the new-attempt protocol. Do not decide this from prediction
correctness or performance.

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

## 7. Remaining parallel plan

MicroCause, MicroRank, TraceRCA, and mmBARO are independent worker tracks.
CIRCA recovery is a fifth independent legacy track. Central integration and
the global prediction lock remain a barrier after all tracks finish.

### P0 — Resolve repository transition readiness

- Completed: user accepted the `.gitignore` byte state; CIRCA evidence remains
  unignored and preserved.
- Verify the branch, protocol bundle, input manifest, Ada-RCA frozen paths, and
  clean pinned RCAEval checkout.
- Re-run the full unit test suite after any code change.
- Update this document with the resolution and current HEAD.

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

### P1 — Complete and lock CIRCA independently

- Completed: explicit user authorization obtained for provenance-consistent
  resume, with a full rerun permitted only if that path proves impractical.
- Completed: recovery ran from the original repository path on branch
  `recovery/circa-a1-20260830` at exact commit `d5d837e` and paused at 100/180.
- Continue only missing RE2-TT cases under `circa-a1-20260830`, the already
  frozen project `.venv`, and the original execution commit.
- Preserve the five existing timeouts and all other terminal records.
- Verify exactly 90 unique records per dataset, one status per case, identical
  environment/protocol/input digests, and clean RCAEval.
- Create and commit `locks/circa_prediction_lock.json` with the records.
- Suggested commit: `eval: freeze label-free CIRCA predictions`.
- Update this document with final operational counts and lock commit.

### P2 — Continue and lock MicroCause in its own task

- Keep `microcause-a1-20260831` on its original execution commit and committed
  frozen MicroCause environment; V1.2 does not affect this method.
- Continue only through the same exact-commit resume procedure if the task was
  interrupted; never replace its existing terminal records.
- Complete RE2-OB 90 cases, then RE2-TT 90 cases under the same attempt and
  frozen environment; no automatic retries.
- Audit denominator and digests, create the method lock, and commit records plus
  lock as `eval: freeze label-free MicroCause predictions`.
- Return the two task commit IDs to the central coordinator; do not edit this
  document from the worker task.

### P3 — Archive MicroRank A1, execute repaired A2, and lock

- Commit the incomplete `microrank-a1-20260831` directory as immutable
  execution evidence; do not resume it.
- Integrate the committed V1.2 repair into the existing task branch and reuse
  the unchanged committed environment manifest.
- Run preflight, then start `microrank-a2-20260901` from case 1 under the common
  interpreter and fixed `PYTHONHASHSEED=20260830`.
- Commit the complete A2 records and method lock.

### P4 — Archive TraceRCA A1, execute repaired A2, and lock

- Commit the incomplete `tracerca-a1-20260831` directory as immutable evidence;
  do not resume it.
- Integrate V1.2, reuse the unchanged frozen environment, and run preflight.
- Start `tracerca-a2-20260901` from case 1 with the common interpreter.
- Preserve raw trace microseconds, span-end filtering, and `t0*1_000_000`.
- Commit the complete A2 records and method lock.

### P5 — Archive mmBARO A1, execute repaired A2, and lock

- Commit the incomplete `mmbaro-a1-20260831` directory as immutable evidence;
  do not resume it.
- Integrate V1.2, reuse the unchanged frozen environment, and run preflight.
- Start `mmbaro-a2-20260901` from case 1 with the common interpreter and
  official `mm-ob` / `mm-tt` keys.
- Preserve the frozen modality-specific native preprocessing.
- Commit the complete A2 records and method lock.

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
