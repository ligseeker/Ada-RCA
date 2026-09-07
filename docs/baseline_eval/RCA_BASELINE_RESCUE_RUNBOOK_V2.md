# RCAEval V2 Rescue Runbook: Five Baselines and CausalRCA CPU Extension

Status: `V2_RESCUE_CODE_READY — CAUSALRCA CPU EXTENSION AUTHORIZED`

This runbook is the operational companion to
`RCA_BASELINE_RESCUE_PROTOCOL_V2.md`. It is performance-blind. Do not
join labels, inspect native/adapted ranking contents, or run `evaluate-v2`
before a committed V2 global prediction lock exists.

Pinned RCAEval: `/home/zhangll24/RCA_project/RCAEval-clean`,
commit `5e96b700445bfb5c599e505ecf37d53bf847bbeb`. Frozen input-manifest
digest: `b8280866432cdd494825cf831d2a73d2fe157de0ecd8801347953172e1ab43ec`.
V2.1 protocol digest:
`dbba81fae2b879bc77084bd6cc07c207c4a9f30dc5a286eb6b1533b0144429de`.

CausalRCA is restored only through the additive CPU extension
`docs/baseline_eval/RCA_BASELINE_CAUSALRCA_CPU_CASE_PARALLELISM_AMENDMENT_V1.md`.
Its machine-readable digest is
`fe46fc498507370563452aa3b31fa65938f5a23c6850586a22afcafa0787551b`.
The extension has its own method-scoped execution root and does not alter the
five-method V2 protocol or its existing evidence.

The final unified table uses the additive combined protocol
`RCA_BASELINE_RESCUE_PROTOCOL_V2_CAUSALRCA_COMBINED`, digest
`24419f179d44ee09f082a23173a0d35c5ec2d3d5592cd93ff9a2afe1d0591e54`, and
binds all six method locks before evaluation. Its dedicated procedure is also
recorded in `RCA_BASELINE_V2_CAUSALRCA_COMBINED_LOCK_AMENDMENT_V1.md`.

## 1. Coordinator creates isolated task worktrees

Run once from the clean central worktree after the final V2 code commit. Worker
containers must not create worktrees or switch branches.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
git worktree add /home/zhangll24/RCA_project/Ada-RCA-v2-circa -b eval/rescue-v2-circa evaluation/rcaeval-baselines
git worktree add /home/zhangll24/RCA_project/Ada-RCA-v2-microcause -b eval/rescue-v2-microcause evaluation/rcaeval-baselines
git worktree add /home/zhangll24/RCA_project/Ada-RCA-v2-microrank -b eval/rescue-v2-microrank evaluation/rcaeval-baselines
git worktree add /home/zhangll24/RCA_project/Ada-RCA-v2-tracerca -b eval/rescue-v2-tracerca evaluation/rcaeval-baselines
git worktree add /home/zhangll24/RCA_project/Ada-RCA-v2-mmbaro -b eval/rescue-v2-mmbaro evaluation/rcaeval-baselines
```

All five paths must be distinct. The only values to fill are the task-worktree
paths. The exact interpreters are fixed in the method sections.

## 2. Execution rules

The A preflight runs synthetic protocol/environment checks, commits the method
environment manifest, and then runs an opaque deterministic subset selected by
SHA-256(case_id) at requested workers 1, 10, and 20. Any status or native/adapted
digest mismatch is a stop condition. Do not run a full attempt after a failed
determinism preflight.

Choose exactly one of B (10 cores) or C (20 cores) for a method. Do not run both
for the same attempt: the attempt freezes worker configuration. D must use the
same worker count as the selected full run. Existing terminal records, including
`METHOD_FAILURE`, are never retried.

## 2.1 Current post-launch recovery commands

The task worktrees already exist and contain post-launch evidence. Use these
commands for the current state; do not restart a completed method.

### CIRCA: continue the interrupted attempt after increasing container memory

The CIRCA attempt is bound to commit
`76830b2cbfe6e67a8dab7f91dfb7fa0f044c663f`. Keep that task worktree at this
commit until the missing-only resume finishes. This command runs only cases
without a terminal record:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-circa
source /home/zhangll24/.venvs/ada-rca-baselines-common/bin/activate
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
test "$(git branch --show-current)" = "eval/rescue-v2-circa"
test "$(git rev-parse HEAD)" = "76830b2cbfe6e67a8dab7f91dfb7fa0f044c663f"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method CIRCA --python "$RESCUE_PYTHON" --attempt-id circa-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume --resume-policy missing-only --log-file /tmp/ada-rca-rescue-v2-circa-heartbeat.jsonl --heartbeat-seconds 30
```

After the resume reaches 180 terminal records, commit only the CIRCA V2
attempt evidence. The central coordinator will re-attest the old lock with the
corrected V2 lock builder; do not overwrite the original lock:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-circa
git add artifacts/baseline_eval/execution_v2/attempts/circa/circa-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/records/circa/circa-a3-rescue-v2 artifacts/baseline_eval/execution_v2/runtimes/circa/circa-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/locks/circa_prediction_lock.json
git commit -m "eval(CIRCA): complete V2 rescue attempt"
```

### MicroCause: retry preflight, then start the fresh V2 attempt

MicroCause's environment is already frozen at task commit `113b9c6`. The V2
protocol preflight now has no subprocess timeout. Run the deterministic
preflight, then the fresh full attempt:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microcause
source /home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/activate
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
test "$(git branch --show-current)" = "eval/rescue-v2-microcause"
test "$(git rev-parse HEAD)" = "113b9c6c2d778f984284573aa2c07c1a7848de75"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py determinism-preflight --method MicroCause --python "$RESCUE_PYTHON" --cases-per-dataset 5 --worker-counts 1,10,20
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method MicroCause --python "$RESCUE_PYTHON" --attempt-id microcause-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-microcause-heartbeat.jsonl --heartbeat-seconds 30
```

For an interrupted MicroCause container, use the same interpreter and worker
configuration with this missing-only resume command:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microcause
source /home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/activate
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
test "$(git branch --show-current)" = "eval/rescue-v2-microcause"
test "$(git rev-parse HEAD)" = "113b9c6c2d778f984284573aa2c07c1a7848de75"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method MicroCause --python "$RESCUE_PYTHON" --attempt-id microcause-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume --resume-policy missing-only --log-file /tmp/ada-rca-rescue-v2-microcause-heartbeat.jsonl --heartbeat-seconds 30
```

### MicroRank, TraceRCA, and mmBARO: verify only

These three attempts already have 180 terminal records and corrected immutable
lock sidecars. Do not run a fresh or resume execution. Verify their active
sidecars from their task worktrees:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microrank
source /home/zhangll24/.venvs/ada-rca-baselines-common/bin/activate
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python scripts/run_baseline_rescue_v2.py verify-method-lock --method MicroRank --attempt-id microrank-a3-rescue-v2
cd /home/zhangll24/RCA_project/Ada-RCA-v2-tracerca
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python scripts/run_baseline_rescue_v2.py verify-method-lock --method TraceRCA --attempt-id tracerca-a3-rescue-v2
cd /home/zhangll24/RCA_project/Ada-RCA-v2-mmbaro
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python scripts/run_baseline_rescue_v2.py verify-method-lock --method mmBARO --attempt-id mmbaro-a3-rescue-v2
```

## 2.2 CausalRCA CPU case-level extension

Attempt: `causalrca-cpu-a1-rescue-v2`<br>
Task branch: `eval/rescue-v2-causalrca`<br>
Interpreter: `/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python`

The coordinator creates this new worktree once from the committed extension
implementation; the worker container must not create or switch worktrees:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
git worktree add /home/zhangll24/RCA_project/Ada-RCA-v2-causalrca -b eval/rescue-v2-causalrca evaluation/rcaeval-baselines
```

### A. Environment / protocol / determinism preflight

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-causalrca
test "$(git branch --show-current)" = "eval/rescue-v2-causalrca"
test -z "$(git status --porcelain)"
test "$(git -C /home/zhangll24/RCA_project/RCAEval-clean rev-parse HEAD)" = "5e96b700445bfb5c599e505ecf37d53bf847bbeb"
test -z "$(git -C /home/zhangll24/RCA_project/RCAEval-clean status --porcelain)"
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py protocol-preflight --method CausalRCA --python "$RESCUE_PYTHON" > /tmp/ada-rca-rescue-v2-causalrca-cpu-protocol.json
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py freeze-environment --method CausalRCA --python "$RESCUE_PYTHON"
git add artifacts/baseline_eval/execution_v2_causalrca_cpu/environments/causalrca.json
git commit -m "env(CausalRCA): freeze CPU V2 extension environment"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py determinism-preflight --method CausalRCA --python "$RESCUE_PYTHON" --cases-per-dataset 5 --worker-counts 1,10,20 > /tmp/ada-rca-rescue-v2-causalrca-cpu-determinism.json
```

### B. 10-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-causalrca
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method CausalRCA --python "$RESCUE_PYTHON" --attempt-id causalrca-cpu-a1-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-causalrca-cpu-heartbeat.jsonl --heartbeat-seconds 30
```

### C. Interrupted-container resume

Keep the same commit, environment, and `--workers 10` value. Only missing
terminal records are scheduled:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-causalrca
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method CausalRCA --python "$RESCUE_PYTHON" --attempt-id causalrca-cpu-a1-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume --resume-policy missing-only --log-file /tmp/ada-rca-rescue-v2-causalrca-cpu-heartbeat.jsonl --heartbeat-seconds 30
```

### D. Commit and verify the method lock

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-causalrca
git add artifacts/baseline_eval/execution_v2_causalrca_cpu/attempts/causalrca/causalrca-cpu-a1-rescue-v2.json artifacts/baseline_eval/execution_v2_causalrca_cpu/records/causalrca/causalrca-cpu-a1-rescue-v2 artifacts/baseline_eval/execution_v2_causalrca_cpu/runtimes/causalrca/causalrca-cpu-a1-rescue-v2.json artifacts/baseline_eval/execution_v2_causalrca_cpu/locks/causalrca_prediction_lock.json
git commit -m "eval(CausalRCA): complete CPU V2 extension attempt"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py verify-method-lock --method CausalRCA --attempt-id causalrca-cpu-a1-rescue-v2
```

This method lock is an additive execution artifact. The existing
`create-global-lock-v2` command still creates the frozen five-method global
lock; CausalRCA requires a later explicit combined-lock integration before it
can be included in any label-join or metric command.

## 3.1 CIRCA

Attempt: `circa-a3-rescue-v2`
Task branch: `eval/rescue-v2-circa`
Interpreter: `/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python`

### A. Environment / protocol / determinism preflight

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-circa
test "$(git branch --show-current)" = "eval/rescue-v2-circa"
test -z "$(git status --porcelain)"
test "$(git -C /home/zhangll24/RCA_project/RCAEval-clean rev-parse HEAD)" = "5e96b700445bfb5c599e505ecf37d53bf847bbeb"
test -z "$(git -C /home/zhangll24/RCA_project/RCAEval-clean status --porcelain)"
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py protocol-preflight --method CIRCA --python "$RESCUE_PYTHON" > /tmp/ada-rca-rescue-v2-circa-protocol.json
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py freeze-environment --method CIRCA --python "$RESCUE_PYTHON"
git add artifacts/baseline_eval/execution_v2/environments/circa.json
git commit -m "env(CIRCA): freeze V2 rescue environment"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py determinism-preflight --method CIRCA --python "$RESCUE_PYTHON" --cases-per-dataset 5 --worker-counts 1,10,20 > /tmp/ada-rca-rescue-v2-circa-determinism.json
```

### B. 10-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-circa
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method CIRCA --python "$RESCUE_PYTHON" --attempt-id circa-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-circa-heartbeat.jsonl --heartbeat-seconds 30
```

### C. 20-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-circa
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method CIRCA --python "$RESCUE_PYTHON" --attempt-id circa-a3-rescue-v2 --workers 20 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-circa-heartbeat.jsonl --heartbeat-seconds 30
```

### D. Interrupted-container resume

Use the command matching B or C; the worker count must not change.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-circa
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method CIRCA --python "$RESCUE_PYTHON" --attempt-id circa-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume --resume-policy missing-only --log-file /tmp/ada-rca-rescue-v2-circa-heartbeat.jsonl --heartbeat-seconds 30
```

For a 20-core initial run, replace only `--workers 10` with
`--workers 20`. No terminal record is overwritten or retried.

### E. Commit and verify method lock

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-circa
git add artifacts/baseline_eval/execution_v2/attempts/circa/circa-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/records/circa/circa-a3-rescue-v2 artifacts/baseline_eval/execution_v2/runtimes/circa/circa-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/locks/circa_prediction_lock.json
git commit -m "eval(CIRCA): complete V2 rescue attempt"
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python scripts/run_baseline_rescue_v2.py verify-method-lock --method CIRCA --attempt-id circa-a3-rescue-v2
```

The final verification must report `execution_validity=INTEGRITY_VALID`. A
blocking status produces an invalid method lock and stops global-lock creation.
## 3.2 MicroCause

Attempt: `microcause-a3-rescue-v2`
Task branch: `eval/rescue-v2-microcause`
Interpreter: `/home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python`

### A. Environment / protocol / determinism preflight

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microcause
test "$(git branch --show-current)" = "eval/rescue-v2-microcause"
test -z "$(git status --porcelain)"
test "$(git -C /home/zhangll24/RCA_project/RCAEval-clean rev-parse HEAD)" = "5e96b700445bfb5c599e505ecf37d53bf847bbeb"
test -z "$(git -C /home/zhangll24/RCA_project/RCAEval-clean status --porcelain)"
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py protocol-preflight --method MicroCause --python "$RESCUE_PYTHON" > /tmp/ada-rca-rescue-v2-microcause-protocol.json
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py freeze-environment --method MicroCause --python "$RESCUE_PYTHON"
git add artifacts/baseline_eval/execution_v2/environments/microcause.json
git commit -m "env(MicroCause): freeze V2 rescue environment"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py determinism-preflight --method MicroCause --python "$RESCUE_PYTHON" --cases-per-dataset 5 --worker-counts 1,10,20 > /tmp/ada-rca-rescue-v2-microcause-determinism.json
```

### B. 10-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microcause
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method MicroCause --python "$RESCUE_PYTHON" --attempt-id microcause-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-microcause-heartbeat.jsonl --heartbeat-seconds 30
```

### C. 20-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microcause
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method MicroCause --python "$RESCUE_PYTHON" --attempt-id microcause-a3-rescue-v2 --workers 20 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-microcause-heartbeat.jsonl --heartbeat-seconds 30
```

### D. Interrupted-container resume

Use the command matching B or C; the worker count must not change.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microcause
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method MicroCause --python "$RESCUE_PYTHON" --attempt-id microcause-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume --resume-policy missing-only --log-file /tmp/ada-rca-rescue-v2-microcause-heartbeat.jsonl --heartbeat-seconds 30
```

For a 20-core initial run, replace only `--workers 10` with
`--workers 20`. No terminal record is overwritten or retried.

### E. Commit and verify method lock

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microcause
git add artifacts/baseline_eval/execution_v2/attempts/microcause/microcause-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/records/microcause/microcause-a3-rescue-v2 artifacts/baseline_eval/execution_v2/runtimes/microcause/microcause-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/locks/microcause_prediction_lock.json
git commit -m "eval(MicroCause): complete V2 rescue attempt"
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python scripts/run_baseline_rescue_v2.py verify-method-lock --method MicroCause --attempt-id microcause-a3-rescue-v2
```

The final verification must report `execution_validity=INTEGRITY_VALID`. A
blocking status produces an invalid method lock and stops global-lock creation.
## 3.3 MicroRank

Attempt: `microrank-a3-rescue-v2`
Task branch: `eval/rescue-v2-microrank`
Interpreter: `/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python`

### A. Environment / protocol / determinism preflight

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microrank
test "$(git branch --show-current)" = "eval/rescue-v2-microrank"
test -z "$(git status --porcelain)"
test "$(git -C /home/zhangll24/RCA_project/RCAEval-clean rev-parse HEAD)" = "5e96b700445bfb5c599e505ecf37d53bf847bbeb"
test -z "$(git -C /home/zhangll24/RCA_project/RCAEval-clean status --porcelain)"
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py protocol-preflight --method MicroRank --python "$RESCUE_PYTHON" > /tmp/ada-rca-rescue-v2-microrank-protocol.json
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py freeze-environment --method MicroRank --python "$RESCUE_PYTHON"
git add artifacts/baseline_eval/execution_v2/environments/microrank.json
git commit -m "env(MicroRank): freeze V2 rescue environment"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py determinism-preflight --method MicroRank --python "$RESCUE_PYTHON" --cases-per-dataset 5 --worker-counts 1,10,20 > /tmp/ada-rca-rescue-v2-microrank-determinism.json
```

### B. 10-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microrank
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method MicroRank --python "$RESCUE_PYTHON" --attempt-id microrank-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-microrank-heartbeat.jsonl --heartbeat-seconds 30
```

### C. 20-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microrank
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method MicroRank --python "$RESCUE_PYTHON" --attempt-id microrank-a3-rescue-v2 --workers 20 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-microrank-heartbeat.jsonl --heartbeat-seconds 30
```

### D. Interrupted-container resume

Use the command matching B or C; the worker count must not change.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microrank
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method MicroRank --python "$RESCUE_PYTHON" --attempt-id microrank-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume --resume-policy missing-only --log-file /tmp/ada-rca-rescue-v2-microrank-heartbeat.jsonl --heartbeat-seconds 30
```

For a 20-core initial run, replace only `--workers 10` with
`--workers 20`. No terminal record is overwritten or retried.

### E. Commit and verify method lock

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-microrank
git add artifacts/baseline_eval/execution_v2/attempts/microrank/microrank-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/records/microrank/microrank-a3-rescue-v2 artifacts/baseline_eval/execution_v2/runtimes/microrank/microrank-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/locks/microrank_prediction_lock.json
git commit -m "eval(MicroRank): complete V2 rescue attempt"
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python scripts/run_baseline_rescue_v2.py verify-method-lock --method MicroRank --attempt-id microrank-a3-rescue-v2
```

The final verification must report `execution_validity=INTEGRITY_VALID`. A
blocking status produces an invalid method lock and stops global-lock creation.
## 3.4 TraceRCA

Attempt: `tracerca-a3-rescue-v2`
Task branch: `eval/rescue-v2-tracerca`
Interpreter: `/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python`

### A. Environment / protocol / determinism preflight

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-tracerca
test "$(git branch --show-current)" = "eval/rescue-v2-tracerca"
test -z "$(git status --porcelain)"
test "$(git -C /home/zhangll24/RCA_project/RCAEval-clean rev-parse HEAD)" = "5e96b700445bfb5c599e505ecf37d53bf847bbeb"
test -z "$(git -C /home/zhangll24/RCA_project/RCAEval-clean status --porcelain)"
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py protocol-preflight --method TraceRCA --python "$RESCUE_PYTHON" > /tmp/ada-rca-rescue-v2-tracerca-protocol.json
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py freeze-environment --method TraceRCA --python "$RESCUE_PYTHON"
git add artifacts/baseline_eval/execution_v2/environments/tracerca.json
git commit -m "env(TraceRCA): freeze V2 rescue environment"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py determinism-preflight --method TraceRCA --python "$RESCUE_PYTHON" --cases-per-dataset 5 --worker-counts 1,10,20 > /tmp/ada-rca-rescue-v2-tracerca-determinism.json
```

### B. 10-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-tracerca
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method TraceRCA --python "$RESCUE_PYTHON" --attempt-id tracerca-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-tracerca-heartbeat.jsonl --heartbeat-seconds 30
```

### C. 20-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-tracerca
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method TraceRCA --python "$RESCUE_PYTHON" --attempt-id tracerca-a3-rescue-v2 --workers 20 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-tracerca-heartbeat.jsonl --heartbeat-seconds 30
```

### D. Interrupted-container resume

Use the command matching B or C; the worker count must not change.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-tracerca
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method TraceRCA --python "$RESCUE_PYTHON" --attempt-id tracerca-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume --resume-policy missing-only --log-file /tmp/ada-rca-rescue-v2-tracerca-heartbeat.jsonl --heartbeat-seconds 30
```

For a 20-core initial run, replace only `--workers 10` with
`--workers 20`. No terminal record is overwritten or retried.

### E. Commit and verify method lock

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-tracerca
git add artifacts/baseline_eval/execution_v2/attempts/tracerca/tracerca-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/records/tracerca/tracerca-a3-rescue-v2 artifacts/baseline_eval/execution_v2/runtimes/tracerca/tracerca-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/locks/tracerca_prediction_lock.json
git commit -m "eval(TraceRCA): complete V2 rescue attempt"
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python scripts/run_baseline_rescue_v2.py verify-method-lock --method TraceRCA --attempt-id tracerca-a3-rescue-v2
```

The final verification must report `execution_validity=INTEGRITY_VALID`. A
blocking status produces an invalid method lock and stops global-lock creation.
## 3.5 mmBARO

Attempt: `mmbaro-a3-rescue-v2`
Task branch: `eval/rescue-v2-mmbaro`
Interpreter: `/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python`

### A. Environment / protocol / determinism preflight

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-mmbaro
test "$(git branch --show-current)" = "eval/rescue-v2-mmbaro"
test -z "$(git status --porcelain)"
test "$(git -C /home/zhangll24/RCA_project/RCAEval-clean rev-parse HEAD)" = "5e96b700445bfb5c599e505ecf37d53bf847bbeb"
test -z "$(git -C /home/zhangll24/RCA_project/RCAEval-clean status --porcelain)"
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py protocol-preflight --method mmBARO --python "$RESCUE_PYTHON" > /tmp/ada-rca-rescue-v2-mmbaro-protocol.json
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py freeze-environment --method mmBARO --python "$RESCUE_PYTHON"
git add artifacts/baseline_eval/execution_v2/environments/mmbaro.json
git commit -m "env(mmBARO): freeze V2 rescue environment"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py determinism-preflight --method mmBARO --python "$RESCUE_PYTHON" --cases-per-dataset 5 --worker-counts 1,10,20 > /tmp/ada-rca-rescue-v2-mmbaro-determinism.json
```

### B. 10-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-mmbaro
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method mmBARO --python "$RESCUE_PYTHON" --attempt-id mmbaro-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-mmbaro-heartbeat.jsonl --heartbeat-seconds 30
```

### C. 20-core full run

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-mmbaro
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method mmBARO --python "$RESCUE_PYTHON" --attempt-id mmbaro-a3-rescue-v2 --workers 20 --datasets re2ob,re2tt --no-timeout --resume-policy fresh --log-file /tmp/ada-rca-rescue-v2-mmbaro-heartbeat.jsonl --heartbeat-seconds 30
```

### D. Interrupted-container resume

Use the command matching B or C; the worker count must not change.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-mmbaro
export RESCUE_PYTHON=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
export PYTHONHASHSEED=20260830
export PYTHONDONTWRITEBYTECODE=1
export CUDA_VISIBLE_DEVICES=""
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export PYTHONPATH="$PWD:/home/zhangll24/RCA_project/RCAEval-clean"
"$RESCUE_PYTHON" scripts/run_baseline_rescue_v2.py run --method mmBARO --python "$RESCUE_PYTHON" --attempt-id mmbaro-a3-rescue-v2 --workers 10 --datasets re2ob,re2tt --no-timeout --resume --resume-policy missing-only --log-file /tmp/ada-rca-rescue-v2-mmbaro-heartbeat.jsonl --heartbeat-seconds 30
```

For a 20-core initial run, replace only `--workers 10` with
`--workers 20`. No terminal record is overwritten or retried.

### E. Commit and verify method lock

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-v2-mmbaro
git add artifacts/baseline_eval/execution_v2/attempts/mmbaro/mmbaro-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/records/mmbaro/mmbaro-a3-rescue-v2 artifacts/baseline_eval/execution_v2/runtimes/mmbaro/mmbaro-a3-rescue-v2.json artifacts/baseline_eval/execution_v2/locks/mmbaro_prediction_lock.json
git commit -m "eval(mmBARO): complete V2 rescue attempt"
/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python scripts/run_baseline_rescue_v2.py verify-method-lock --method mmBARO --attempt-id mmbaro-a3-rescue-v2
```

The final verification must report `execution_validity=INTEGRITY_VALID`. A
blocking status produces an invalid method lock and stops global-lock creation.

## 4. Central integration and V2 global prediction lock

After each task container commits its environment and completed attempt, run this
from the central worktree. The `git log` expressions select method-scoped
commits from the task worktrees; no Git index is shared.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
test -z "$(git status --porcelain)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-circa log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/circa.json)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-circa log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/circa_prediction_lock.json)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-microcause log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/microcause.json)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-microcause log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/microcause_prediction_lock.json)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-microrank log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/microrank.json)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-microrank log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/microrank_prediction_lock.json)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-tracerca log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/tracerca.json)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-tracerca log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/tracerca_prediction_lock.json)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-mmbaro log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/mmbaro.json)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-mmbaro log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/mmbaro_prediction_lock.json)"
```

Verify every lock before creating the global lock:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
COMMON_PY=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method CIRCA --attempt-id circa-a3-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method MicroCause --attempt-id microcause-a3-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method MicroRank --attempt-id microrank-a3-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method TraceRCA --attempt-id tracerca-a3-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method mmBARO --attempt-id mmbaro-a3-rescue-v2
```

The active lock for MicroRank, TraceRCA, and mmBARO is currently the corrected
`*_prediction_lock_reissued_v2.json` sidecar. Their original
`*_prediction_lock.json` files and earlier reissue sidecars are retained as
immutable evidence and may continue to show the historical invalid attestation;
do not replace or delete them. `verify-method-lock` selects the corrected active
sidecar automatically.

For the remaining methods after their task commits arrive, use the following
current-state integration sequence. CIRCA's old task runner may create an
invalid original lock even when all terminal statuses are non-blocking; in that
case central re-attestation writes a distinct sidecar. MicroCause's corrected
task runner should produce a valid original lock.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
test -z "$(git status --porcelain)"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-circa log -1 --format=%H -- artifacts/baseline_eval/execution_v2/attempts/circa/circa-a3-rescue-v2.json)"
COMMON_PY=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
"$COMMON_PY" scripts/run_baseline_rescue_v2.py reissue-method-lock --method CIRCA --attempt-id circa-a3-rescue-v2
git add artifacts/baseline_eval/execution_v2/locks/circa_prediction_lock_reissued_v2.json
git commit -m "eval(CIRCA): re-attest V2 method lock"
git cherry-pick "$(git -C /home/zhangll24/RCA_project/Ada-RCA-v2-microcause log -1 --format=%H -- artifacts/baseline_eval/execution_v2/attempts/microcause/microcause-a3-rescue-v2.json)"
```

The CIRCA re-attestation command must run after the CIRCA attempt commit is
integrated and before the MicroCause attempt is cherry-picked, so the central
worktree is clean at the required transition. If the CIRCA task branch is
updated to the corrected V2 code after its resume, the central re-attestation
still remains the authoritative immutable sidecar step.

Create, commit, and verify the global lock:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
COMMON_PY=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
"$COMMON_PY" scripts/run_baseline_rescue_v2.py create-global-lock-v2
git add artifacts/baseline_eval/execution_v2/prediction_lock_v2.json
git commit -m "eval: create V2 global prediction lock"
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-global-lock-v2
```

### 4.1 Final six-method combined global lock

The five-method lock above remains an optional base-scope artifact. The final
unified table must use the explicit combined lock below, which verifies the
five base locks and the independent CausalRCA CPU lock together:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
COMMON_PY=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method CIRCA --attempt-id circa-a3-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method MicroCause --attempt-id microcause-a3-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method MicroRank --attempt-id microrank-a3-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method TraceRCA --attempt-id tracerca-a3-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method mmBARO --attempt-id mmbaro-a3-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-method-lock --method CausalRCA --attempt-id causalrca-cpu-a1-rescue-v2
"$COMMON_PY" scripts/run_baseline_rescue_v2.py create-global-lock-v2-causalrca
git add artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json
git commit -m "eval: create combined V2 global prediction lock"
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-global-lock-v2-causalrca
```

## 5. Metric-unlock commands

The following are **ONLY RUN AFTER GLOBAL PREDICTION LOCK IS COMMITTED**. They
join labels only after the gate, report OB and TT separately, use denominator
90, treat only legal `METHOD_FAILURE` as zero utility, and block on all
other invalid statuses.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
COMMON_PY=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-global-lock-v2
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 evaluate-v2
git add artifacts/baseline_eval/execution_v2/evaluation
git commit -m "eval: unlock V2 unified metrics after global prediction lock"
```

The evaluator writes the overall, fault-level, robustness, comparability, and
paired-bootstrap outputs. These commands verify each projection and publish the
final report:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
COMMON_PY=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 fault-level-v2
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 robustness-v2
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 comparability-v2
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 paired-bootstrap-v2
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 render-report-v2
git add docs/baseline_eval/RCA_BASELINE_CONFIRMATORY_RESULTS_V2.md
git commit -m "docs: publish V2 unified baseline evaluation report"
```

Paired bootstrap defaults are 10,000 fault-stratified resamples with seed
`20260827`, primary `Ada-RCA minus baseline Avg@5`, and secondary
`Ada-RCA minus baseline AC@1`. Baseline MRR remains
`NOT-IDENTIFIABLE`; no candidate completion is legal.

### 5.1 Final six-method metric-unlock commands

Run these only after the combined lock commit above. They generate the final
six-baseline tables, including CausalRCA, under the combined evaluation root:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
COMMON_PY=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-global-lock-v2-causalrca
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 evaluate-v2-causalrca
git add artifacts/baseline_eval/execution_v2/evaluation_causalrca
git commit -m "eval: compute combined six-method V2 metrics"
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 fault-level-v2-causalrca
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 robustness-v2-causalrca
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 comparability-v2-causalrca
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 paired-bootstrap-v2-causalrca
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 render-report-v2-causalrca
git add docs/baseline_eval/RCA_BASELINE_CONFIRMATORY_RESULTS_V2.md
git commit -m "docs: publish combined six-method V2 baseline table"
```
