# RCAEval Confirmatory Baseline Execution Status and Handoff

Status: **IN PROGRESS — CIRCA INCOMPLETE**  
State revision: `2026-08-31.1`  
Last operational audit: 2026-08-31, Asia/Shanghai  
Branch: `evaluation/rcaeval-baselines`  
Last synchronized substantive commit: `1a7718c`

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
7. `RCA_BASELINE_PERFORMANCE_FIREWALL_V1.md`; and
8. `RCA_BASELINE_ENVIRONMENTS.md`.

## 2. Frozen repository and provenance

| Item | Frozen/current value | Status |
|---|---|---|
| Required branch | `evaluation/rcaeval-baselines` | PASS |
| Current remote state at audit | local `1a7718c`; matched `origin/evaluation/rcaeval-baselines` | PASS |
| Required starting HEAD | `54b403ff0441c318817818abeda13526652ae1d2` | ancestor present |
| Ada-RCA Scientific V1 | `bed295326e567395e725caa82840a534dcc0b1de` | immutable |
| Evidence-closure reference | `9342e06db91945be2e44703437229ba45b18bda8` | frozen |
| RCAEval checkout | `/home/zhangll24/RCA_project/RCAEval-clean` | clean |
| RCAEval commit | `5e96b700445bfb5c599e505ecf37d53bf847bbeb` | PASS |
| Protocol digest | `aa4f03363e1347a4b4e3c6427fd846be80452f025c3a6d08042ed6f6de0a849e` | frozen |
| Input-manifest digest | `b8280866432cdd494825cf831d2a73d2fe157de0ecd8801347953172e1ab43ec` | frozen |

The only observed worktree modification at the last audit was an uncommitted
`.gitignore` change. It adds:

```gitignore
artifacts/baseline_eval/execution_v1/
artifacts/features/
```

Its ownership was not established, so it has been preserved and excluded from
all baseline commits. It is a material workflow risk because it ignores future
environment manifests, records, and prediction locks, and because formal
environment freezing requires a clean worktree. Resolve it explicitly before
the next formal environment freeze; do not silently discard it.

## 3. Environment migration status

Environment migration is complete. New virtual environments live outside all
project worktrees under `~/.venvs/`.

| Method | Environment/interpreter | Python | Key dependency | Current state |
|---|---|---|---|---|
| BARO | project `.venv/bin/python` | 3.10.20 | historical frozen stack | environment valid; execution complete |
| CIRCA | project `.venv/bin/python` | 3.10.20 | historical frozen stack | environment valid; attempt incomplete; never migrate mid-attempt |
| MicroCause | `~/.venvs/ada-rca-baselines-microcause/bin/python` | 3.10.20 | `tigramite==4.2.2.1` | migration and read-only preflight complete; formal freeze pending CIRCA lock |
| MicroRank | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | Tigramite 5.2.10.1 in common stack | read-only preflight complete; formal freeze pending |
| TraceRCA | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | common stack | read-only preflight complete; formal freeze pending |
| mmBARO | `~/.venvs/ada-rca-baselines-common/bin/python` | 3.10.20 | common stack | read-only preflight complete; formal freeze pending |
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
| Sequential execution harness | `e056958` | complete |
| Frozen input manifest | `5b3d944` | complete |
| BARO environment freeze | `5018f5d` | complete |
| BARO label-free prediction lock | `fbfb6e6` | complete |
| CIRCA environment freeze | `d5d837e` | complete |
| Later-baseline preflight hardening | `5ae9ebb` | complete |
| External environment documentation | `1529f4b` | complete and merged into this branch |
| Read-only later-method environment preflight | `6b01649` | complete |
| Environment/preflight guide update | `1a7718c` | complete |
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

The full suite most recently passed with `175` tests. This does not replace a
fresh full-suite run after future code changes.

## 5. Confirmatory execution coverage

Only operational state is recorded here. No prediction contents, labels, root
ranks, or metrics may be added before the global prediction lock.

| Method | Dataset | Records | SUCCESS | METHOD_FAILURE | ADAPTER_FAILURE | DATA_FAILURE | TIMEOUT | Method lock |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BARO | RE2-OB | 90/90 | 90 | 0 | 0 | 0 | 0 | valid |
| BARO | RE2-TT | 90/90 | 90 | 0 | 0 | 0 | 0 | valid |
| CIRCA | RE2-OB | 90/90 | 86 | 4 | 0 | 0 | 0 | absent |
| CIRCA | RE2-TT | 9/90 | 3 | 1 | 0 | 0 | 5 | absent |
| MicroCause | — | 0 | — | — | — | — | — | absent |
| MicroRank | — | 0 | — | — | — | — | — | absent |
| TraceRCA | — | 0 | — | — | — | — | — | absent |
| mmBARO | — | 0 | — | — | — | — | — | absent |
| CausalRCA | — | 0 | — | — | — | — | — | deferred |

BARO lock verification: `EXECUTION_COMPLETE`, 180 terminal record digests,
both 90-case denominators valid, environment unchanged.

CIRCA attempt: `circa-a1-20260830`. It stopped after 99/180 persisted terminal
records. Its last persisted case is terminal and is not eligible for retry.
There is no CIRCA prediction lock and no baseline runner, worker, or tmux
session currently running. Do not restart or resume it automatically.

## 6. Current blockers and decisions required

### B1. CIRCA sequence gate

MicroCause cannot be formally frozen or executed until CIRCA has a committed,
integrity-valid method-level prediction lock. The existing CIRCA attempt is
incomplete but its environment remains valid.

Before any recovery action, re-audit:

- branch and Git identity;
- process/tmux state;
- exact record counts and terminal-status counts only;
- CIRCA environment digest and current environment identity;
- input/protocol/RCAEval identities; and
- absence of a CIRCA prediction lock.

Resuming the same attempt may only continue missing cases with the same frozen
environment and attempt ID. It must not rerun or replace any persisted failure
or timeout. Because automatic restart was explicitly prohibited, obtain a new
explicit user instruction before running:

```bash
./.venv/bin/python scripts/run_baseline_confirmatory.py run-method \
  --method CIRCA \
  --attempt-id circa-a1-20260830 \
  --resume
```

If a systematic framework defect is established instead, retain the entire
attempt and follow the new-attempt protocol. Do not decide this from prediction
correctness or performance.

### B2. Uncommitted `.gitignore`

The current change both dirties the worktree and ignores the execution artifact
tree. Before a formal transition, determine whether it should be committed,
revised to allow required manifests/locks/records, or intentionally removed.
Do not resolve it by losing existing execution evidence.

### B3. CausalRCA disposition

CausalRCA is deferred. Its GPU implementation is saved separately, but neither
its environment nor execution is currently authorized. Before the global lock,
the user must explicitly decide whether to restore it under a committed
protocol amendment or assign a legitimate method-level blocked disposition.
Do not infer either decision.

## 7. Remaining sequential plan

The following order is mandatory. A later real method must not overlap an
earlier method.

### P0 — Resolve repository transition readiness

- Reconcile the uncommitted `.gitignore` without deleting evidence.
- Verify the branch, protocol bundle, input manifest, Ada-RCA frozen paths, and
  clean pinned RCAEval checkout.
- Re-run the full unit test suite after any code change.
- Update this document with the resolution and current HEAD.

### P1 — Complete and lock CIRCA

- Obtain explicit user authorization for resume or another protocol-valid
  disposition.
- If resumed, continue only the 81 missing RE2-TT cases under
  `circa-a1-20260830` and the already frozen project `.venv`.
- Preserve the five existing timeouts and all other terminal records.
- Verify exactly 90 unique records per dataset, one status per case, identical
  environment/protocol/input digests, and clean RCAEval.
- Create and commit `locks/circa_prediction_lock.json` with the records.
- Suggested commit: `eval: freeze label-free CIRCA predictions`.
- Update this document with final operational counts and lock commit.

### P2 — Freeze, execute, and lock MicroCause

- Require the committed CIRCA lock first.
- Re-run read-only preflight with the MicroCause external interpreter.
- Freeze `environments/microcause.json` and commit it before any real case.
- Suggested environment commit: `eval: freeze MicroCause execution environment`.
- Run RE2-OB 90 cases, then RE2-TT 90 cases, using one attempt and the same
  frozen environment; no automatic retries.
- Audit denominator and digests, create the method lock, and commit records plus
  lock as `eval: freeze label-free MicroCause predictions`.
- Update this document after the environment freeze and again after the method
  lock.

### P3 — Freeze, execute, and lock MicroRank

- Require the committed MicroCause lock.
- Use the common external interpreter and fixed `PYTHONHASHSEED=20260830`.
- Repeat preflight, environment-freeze commit, OB then TT execution, integrity
  audit, prediction lock, prediction commit, and status-document update.

### P4 — Freeze, execute, and lock TraceRCA

- Require the committed MicroRank lock.
- Use the common external interpreter.
- Preserve raw trace microseconds, span-end filtering, and `t0*1_000_000`.
- Repeat the same environment-freeze, execution, lock, commit, and documentation
  sequence.

### P5 — Freeze, execute, and lock mmBARO

- Require the committed TraceRCA lock.
- Use the common external interpreter and official `mm-ob` / `mm-tt` keys.
- Preserve the frozen modality-specific native preprocessing.
- Repeat the same environment-freeze, execution, lock, commit, and documentation
  sequence.

### P6 — Resolve CausalRCA

- Keep deferred unless the user explicitly restores it.
- If restored, first commit the required protocol/GPU amendment and revalidate
  determinism and environment semantics before any formal freeze.
- Otherwise record only a protocol-legitimate method-level blocked disposition;
  user deferral alone must not be silently rewritten as a technical failure.
- Update this document with the decision and evidence location.

### P7 — Global prediction lock

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
