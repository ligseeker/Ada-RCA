# Ada-RCA Baseline Evaluation Instructions

## Scope

This worktree is for the RCAEval confirmatory baseline evaluation on branch
`evaluation/rcaeval-baselines`. Treat it as a protocol-bound experiment, not as
an open-ended benchmark or model-development workspace.

Before changing evaluation code or running a method, read the applicable files
under `docs/baseline_eval/`, especially:

- `RCA_BASELINE_PROTOCOL_FREEZE_V1.md`
- `RCA_BASELINE_ADAPTER_SPEC_V1.md`
- `RCA_BASELINE_EXECUTION_MATRIX_V1.md`
- `RCA_BASELINE_FAILURE_POLICY_V1.md`
- `RCA_BASELINE_PERFORMANCE_FIREWALL_V1.md`

The committed protocol and machine-readable freezes are the scientific source
of truth. A convenient command or upstream default never overrides them.

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

The frozen method sequence is:

```text
BARO -> CIRCA -> MicroCause -> MicroRank -> TraceRCA -> mmBARO -> CausalRCA
```

Apply these rules:

- Run only one baseline method at a time. No cross-method execution overlap.
- Do not start method N+1 until method N has complete terminal records, a valid
  prediction lock, and integrity verification.
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

As of 2026-08-31, BARO has a frozen prediction lock. The CIRCA attempt stopped
without a lock after 99 of 180 records; the last persisted record is a
`TIMEOUT`. No CIRCA process is currently assumed to be running. Re-audit the
records, process state, frozen environment, and Git identity before discussing
recovery, and do not restart it automatically.

The environment-management documentation is saved separately on branch
`chore/baseline-env-management` at commit `efbe691`; do not assume it has been
merged into this branch. The two activation commands above remain the working
environment map.
