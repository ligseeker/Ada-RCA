# RCAEval Five-Baseline Rescue V2 Runbook

Status: `V2_RESCUE_CODE_READY — FIVE TASK-CONTAINER EXECUTIONS PENDING`

This runbook is the operational companion to
`RCA_BASELINE_RESCUE_PROTOCOL_V2.md`. It is performance-blind. Do not
join labels, inspect native/adapted ranking contents, or run `evaluate-v2`
before a committed V2 global prediction lock exists.

Pinned RCAEval: `/home/zhangll24/RCA_project/RCAEval-clean`,
commit `5e96b700445bfb5c599e505ecf37d53bf847bbeb`. Frozen input-manifest
digest: `b8280866432cdd494825cf831d2a73d2fe157de0ecd8801347953172e1ab43ec`.
V2.1 protocol digest:
`dbba81fae2b879bc77084bd6cc07c207c4a9f30dc5a286eb6b1533b0144429de`.

## 1. Coordinator creates isolated task worktrees

Run once from the clean central worktree after the final V2 code commit. Worker
containers must not create worktrees or switch branches.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
git worktree add <CIRCA_TASK_WORKTREE> -b eval/rescue-v2-circa evaluation/rcaeval-baselines
git worktree add <MICROCAUSE_TASK_WORKTREE> -b eval/rescue-v2-microcause evaluation/rcaeval-baselines
git worktree add <MICRORANK_TASK_WORKTREE> -b eval/rescue-v2-microrank evaluation/rcaeval-baselines
git worktree add <TRACERCA_TASK_WORKTREE> -b eval/rescue-v2-tracerca evaluation/rcaeval-baselines
git worktree add <MMBARO_TASK_WORKTREE> -b eval/rescue-v2-mmbaro evaluation/rcaeval-baselines
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

## 3.1 CIRCA

Attempt: `circa-a3-rescue-v2`
Task branch: `eval/rescue-v2-circa`
Interpreter: `/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python`

### A. Environment / protocol / determinism preflight

```bash
cd <CIRCA_TASK_WORKTREE>
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
cd <CIRCA_TASK_WORKTREE>
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
cd <CIRCA_TASK_WORKTREE>
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
cd <CIRCA_TASK_WORKTREE>
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
cd <CIRCA_TASK_WORKTREE>
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
cd <MICROCAUSE_TASK_WORKTREE>
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
cd <MICROCAUSE_TASK_WORKTREE>
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
cd <MICROCAUSE_TASK_WORKTREE>
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
cd <MICROCAUSE_TASK_WORKTREE>
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
cd <MICROCAUSE_TASK_WORKTREE>
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
cd <MICRORANK_TASK_WORKTREE>
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
cd <MICRORANK_TASK_WORKTREE>
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
cd <MICRORANK_TASK_WORKTREE>
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
cd <MICRORANK_TASK_WORKTREE>
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
cd <MICRORANK_TASK_WORKTREE>
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
cd <TRACERCA_TASK_WORKTREE>
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
cd <TRACERCA_TASK_WORKTREE>
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
cd <TRACERCA_TASK_WORKTREE>
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
cd <TRACERCA_TASK_WORKTREE>
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
cd <TRACERCA_TASK_WORKTREE>
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
cd <MMBARO_TASK_WORKTREE>
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
cd <MMBARO_TASK_WORKTREE>
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
cd <MMBARO_TASK_WORKTREE>
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
cd <MMBARO_TASK_WORKTREE>
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
cd <MMBARO_TASK_WORKTREE>
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
git cherry-pick "$(git -C <CIRCA_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/circa.json)"
git cherry-pick "$(git -C <CIRCA_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/circa_prediction_lock.json)"
git cherry-pick "$(git -C <MICROCAUSE_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/microcause.json)"
git cherry-pick "$(git -C <MICROCAUSE_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/microcause_prediction_lock.json)"
git cherry-pick "$(git -C <MICRORANK_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/microrank.json)"
git cherry-pick "$(git -C <MICRORANK_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/microrank_prediction_lock.json)"
git cherry-pick "$(git -C <TRACERCA_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/tracerca.json)"
git cherry-pick "$(git -C <TRACERCA_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/tracerca_prediction_lock.json)"
git cherry-pick "$(git -C <MMBARO_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/environments/mmbaro.json)"
git cherry-pick "$(git -C <MMBARO_TASK_WORKTREE> log -1 --format=%H -- artifacts/baseline_eval/execution_v2/locks/mmbaro_prediction_lock.json)"
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

Create, commit, and verify the global lock:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
COMMON_PY=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
"$COMMON_PY" scripts/run_baseline_rescue_v2.py create-global-lock-v2
git add artifacts/baseline_eval/execution_v2/prediction_lock_v2.json
git commit -m "eval: create V2 global prediction lock"
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-global-lock-v2
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
