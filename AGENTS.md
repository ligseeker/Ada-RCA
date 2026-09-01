# Ada-RCA Baseline Evaluation Instructions

## Scope

This worktree is for the RCAEval confirmatory baseline evaluation on branch
`evaluation/rcaeval-baselines`. Treat it as a protocol-bound experiment, not as
an open-ended benchmark or model-development workspace.

Before changing evaluation code or running a method, read the applicable files
under `docs/baseline_eval/`, especially:

- `RCA_BASELINE_EXECUTION_STATUS.md`
- `RCA_BASELINE_PARALLEL_EXECUTION_AMENDMENT_V1_1.md`
- `RCA_BASELINE_TRACE_CSV_PARSER_AMENDMENT_V1_2.md`
- `RCA_BASELINE_CASE_PARALLELISM_AMENDMENT_V1_3.md`
- `RCA_BASELINE_PARALLEL_RUNBOOK_V1_1.md`
- `RCA_BASELINE_PROTOCOL_FREEZE_V1.md`
- `RCA_BASELINE_ADAPTER_SPEC_V1.md`
- `RCA_BASELINE_EXECUTION_MATRIX_V1.md`
- `RCA_BASELINE_FAILURE_POLICY_V1.md`
- `RCA_BASELINE_PERFORMANCE_FIREWALL_V1.md`

The committed protocol and machine-readable freezes are the scientific source
of truth. A convenient command or upstream default never overrides them.

`RCA_BASELINE_EXECUTION_STATUS.md` is the canonical operational handoff. At the
start of a new session, reconcile it with read-only Git, artifact-count,
environment, lock, and process checks before taking action.

## Progress handoff discipline

- After every completed central coordination task that changes code,
  environments, integrated execution records, locks, blockers, decisions, or
  the remaining plan, update
  `docs/baseline_eval/RCA_BASELINE_EXECUTION_STATUS.md` before handing off.
- An isolated parallel method task must not edit the canonical status document.
  It commits only its method-scoped environment, records, and lock; the central
  coordinator updates status after integrating that task's commits.
- Keep the handoff performance-blind before the global prediction lock: record
  only operational counts, statuses, runtimes, digests, paths, commits, tests,
  blockers, and next actions.
- Include the status update in the task's logical commit or in an immediate
  follow-up documentation commit. Push it when the active workflow authorizes
  pushing.
- If fresh read-only evidence disagrees with the handoff, stop execution,
  preserve artifacts, and correct the handoff. Never alter evidence merely to
  make the document agree.

## Repository and worktree discipline

- Preserve all pre-existing user changes. Inspect `git status` before editing,
  stage explicit paths, and keep unrelated modifications out of commits.
- Do not use destructive Git operations or delete execution artifacts to make a
  run look clean. Persisted failures and timeouts are evidence.
- Keep commits atomic: implementation, environment freeze, predictions, locks,
  and disclosure/metrics should remain reviewable as separate stages.
- Do not modify the pinned RCAEval source checkout. Use it read-only at
  `/home/zhangll24/RCA_project/RCAEval-clean`; its required commit is
  `5e96b700445bfb5c599e505ecf37d53bf847bbeb` and it must be clean.
- Use `PYTHONPATH` or the existing runner integration to import RCAEval. Do not
  copy-edit upstream algorithm code into this repository.

## Python environments

Virtual environments belong outside the project tree under `~/.venvs/`.

Common environment (BARO, CIRCA, MicroRank, TraceRCA, and mmBARO):

```bash
source ~/.venvs/ada-rca-baselines-common/bin/activate
```

MicroCause environment (isolated for its Tigramite compatibility):

```bash
source ~/.venvs/ada-rca-baselines-microcause/bin/activate
```

For scripts and formal freezes, prefer the absolute interpreter paths:

```text
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
/home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python
```

The project-local `.venv` is historical evidence for frozen BARO/CIRCA
attempts. Retain it, but do not treat it as the default for later methods.
Never recreate, upgrade, or mutate a method environment after its first real
confirmatory case. Resolve dependencies only with synthetic/preflight inputs,
then freeze and verify the environment before real execution.

## Tests and validation

Run the full suite with the common external environment:

```bash
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python \
  -m unittest discover -s tests -p 'test_*.py'
```

For a focused change, run the relevant test module first, then the full suite
before committing unless the change is documentation-only. Also run
`git diff --check` on edited paths.

Do not weaken tests, firewalls, frozen hashes, or validation gates to make a
run pass. Diagnose the mismatch and preserve its evidence.

## Confirmatory execution rules

The stable method registry/reporting order is:

```text
BARO -> CIRCA -> MicroCause -> MicroRank -> TraceRCA -> mmBARO -> CausalRCA
```

The V1.1 execution amendment authorizes MicroCause, MicroRank, TraceRCA, and
mmBARO to run concurrently in separate task containers. The containers share
one filesystem, so each task must use the dedicated linked Git worktree and
unique branch created by the central coordinator before launch.
Apply these rules:

- Assign exactly one method to each task. Never let two containers enter the
  same worktree path, share a Git index, or write the same method output path.
- Worker containers must not create/remove worktrees or switch task branches.
  The coordinator owns worktree creation and later commit integration.
- Different methods may overlap. Two runs of the same method may not overlap.
- Per-method process locks live in the repository's shared Git common
  directory; container-local `/tmp` is not an execution lock authority.
- Treat registry order as reporting order only; a method does not depend on a
  preceding method's prediction lock.
- Worker tasks write only their method environment, records, and method lock.
  The central coordinator alone integrates commits, updates the status, and
  creates the global prediction lock.
- Every RE2-OB and RE2-TT method run has 90 canonical cases per dataset.
- The per-case timeout is 3,600 seconds. There is no automatic retry. Preserve
  `METHOD_FAILURE`, `ADAPTER_FAILURE`, `DATA_FAILURE`, and `TIMEOUT` records.
- Use seed `20260830` for Python, NumPy, and applicable Torch state, and start
  workers with `PYTHONHASHSEED=20260830`.
- Never substitute dummy, alphabetical, registry-order, input-column-order, or
  random rankings for failed native output.
- Candidate completion is `NONE`; baseline MRR is `NOT-IDENTIFIABLE` under V1.
- Confirm the frozen Git identity, environment manifest, input manifest, and
  clean pinned RCAEval checkout before a formal run.
- Load the logical `traces` CSV role with Pandas' Python engine as frozen by
  V1.2. Other CSV roles retain their existing parser behavior.
- Retain the incomplete MicroRank, TraceRCA, and mmBARO A1 attempts. Do not
  resume or overwrite them after the V1.2 repair; start the authorized A2
  attempt from case 1 under one repaired execution commit.
- Retain and never resume the incomplete CIRCA and MicroCause A1 attempts once
  their external processes have stopped. V1.3 authorizes only their new A2
  attempts to use exactly four deterministic case-worker slots under one
  top-level method lock; no second runner for either method may overlap.
- Every V1.3 case record retains its own timestamps and monotonic wall time.
  Commit the completed attempt runtime summary together with the 180 records
  and method lock.

Container isolation must include adequate CPU and memory allocation. If
physical-resource throttling occurs, reduce task concurrency; do not change
timeouts or rerun based on observed results.

CausalRCA is currently deferred by explicit user decision. Do not freeze or
run it unless the user explicitly restores it as a baseline. Its saved GPU
work is isolated on branch `wip/causalrca-gpu-amendment` at commit `89db7ec`.
RCD remains blocked, and PDiagnose, multi-source CIRCA, and mmRCD remain
context-only; do not execute them as confirmatory baselines without a new,
committed protocol authorization.

## Performance and label firewall

Until a method's predictions are locked and integrity-verified, restrict
inspection and reporting to operational facts such as case counts, status
counts, elapsed time, resource use, and error categories.

- Do not inspect or print root labels beside predictions.
- Do not inspect real-case native or adapted rankings, top-k contents, metric
  values, or aggregate performance while resolving execution issues.
- Do not use observed performance to choose dependencies, adapters, seeds,
  retry behavior, preprocessing, or method inclusion.
- Join labels and compute/disclose metrics only through the frozen post-lock
  stage.
- Ada-RCA V1 is immutable: do not change its Z2/features, Conditional Logit,
  lambda, folds, candidate registries, root mappings, predictions, or metrics.

## Current execution checkpoint

The current checkpoint, method coverage, environment migration, blockers, and
complete remaining plan are maintained in
`docs/baseline_eval/RCA_BASELINE_EXECUTION_STATUS.md`. Do not rely on a copied
conversation summary when that committed handoff and fresh read-only evidence
are available.

As of the latest 2026-09-01 read-only audit, BARO has a valid frozen prediction
lock and CIRCA has 100 of 180 terminal records but no lock. A CIRCA recovery
process was observed, so never launch a duplicate without a fresh process
audit. TraceRCA and mmBARO A1 both stopped after 59 records at the same native
CSV-parser crash; V1.2 authorizes repaired A2 attempts and also requires
MicroRank to restart prospectively under the same repaired commit.
