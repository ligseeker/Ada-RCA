# RCAEval Parallel Baseline Runbook V1.1

This runbook contains the copy-and-run commands for task containers that share
one filesystem. Use one task per method. Replace `<SHARED_FS_BASE_COMMIT>` with
the committed revision that contains the shared-filesystem V1.1 amendment and
harness.

## Common task rules

Container isolation does not isolate files. Run every task from the dedicated
linked worktree assigned below. Do not point two containers at the same path.
Store console logs outside every Git worktree so the clean-worktree preflight
is not tripped.

Before starting any containers, run the following once from the central
coordinator. Do not run these commands concurrently:

```bash
TASK_ROOT=/home/zhangll24/RCA_project/Ada-RCA-baseline-tasks
LOG_ROOT=/home/zhangll24/RCA_project/Ada-RCA-baseline-task-logs
ADMIN_ROOT=/home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
BASE_COMMIT=<SHARED_FS_BASE_COMMIT>

mkdir -p "${TASK_ROOT}" "${LOG_ROOT}"

git -C "${ADMIN_ROOT}" worktree add \
  -b execution/microcause-a1-20260831 \
  "${TASK_ROOT}/microcause" "${BASE_COMMIT}"

git -C "${ADMIN_ROOT}" worktree add \
  -b execution/microrank-a1-20260831 \
  "${TASK_ROOT}/microrank" "${BASE_COMMIT}"

git -C "${ADMIN_ROOT}" worktree add \
  -b execution/tracerca-a1-20260831 \
  "${TASK_ROOT}/tracerca" "${BASE_COMMIT}"

git -C "${ADMIN_ROOT}" worktree add \
  -b execution/mmbaro-a1-20260831 \
  "${TASK_ROOT}/mmbaro" "${BASE_COMMIT}"

git -C "${ADMIN_ROOT}" worktree list
```

The four currently runnable methods are independent. Their task branches may
run at the same time. BARO is complete, CIRCA retains its separate legacy
recovery workflow, and CausalRCA must not be run.

## MicroCause task

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baseline-tasks/microcause
source ~/.venvs/ada-rca-baselines-microcause/bin/activate
set -euo pipefail
command -v python
python --version

python scripts/run_baseline_confirmatory.py global-preflight
python scripts/run_baseline_confirmatory.py preflight-environment \
  --method MicroCause \
  --python /home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python

python scripts/run_baseline_confirmatory.py freeze-environment \
  --method MicroCause \
  --python /home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python

git add artifacts/baseline_eval/execution_v1/environments/microcause.json
git commit -m "eval: freeze MicroCause execution environment"

python scripts/run_baseline_confirmatory.py run-method \
  --method MicroCause \
  --attempt-id microcause-a1-20260831 \
  > /home/zhangll24/RCA_project/Ada-RCA-baseline-task-logs/microcause-a1-20260831.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/microcause/microcause-a1-20260831 \
  artifacts/baseline_eval/execution_v1/locks/microcause_prediction_lock.json
git commit -m "eval: freeze label-free MicroCause predictions"
git status --short --branch
```

## MicroRank task

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baseline-tasks/microrank
source ~/.venvs/ada-rca-baselines-common/bin/activate
set -euo pipefail
command -v python
python --version

python scripts/run_baseline_confirmatory.py global-preflight
python scripts/run_baseline_confirmatory.py preflight-environment \
  --method MicroRank \
  --python /home/zhangll24/.venvs/ada-rca-baselines-common/bin/python

python scripts/run_baseline_confirmatory.py freeze-environment \
  --method MicroRank \
  --python /home/zhangll24/.venvs/ada-rca-baselines-common/bin/python

git add artifacts/baseline_eval/execution_v1/environments/microrank.json
git commit -m "eval: freeze MicroRank execution environment"

python scripts/run_baseline_confirmatory.py run-method \
  --method MicroRank \
  --attempt-id microrank-a1-20260831 \
  > /home/zhangll24/RCA_project/Ada-RCA-baseline-task-logs/microrank-a1-20260831.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/microrank/microrank-a1-20260831 \
  artifacts/baseline_eval/execution_v1/locks/microrank_prediction_lock.json
git commit -m "eval: freeze label-free MicroRank predictions"
git status --short --branch
```

## TraceRCA task

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baseline-tasks/tracerca
source ~/.venvs/ada-rca-baselines-common/bin/activate
set -euo pipefail
command -v python
python --version

python scripts/run_baseline_confirmatory.py global-preflight
python scripts/run_baseline_confirmatory.py preflight-environment \
  --method TraceRCA \
  --python /home/zhangll24/.venvs/ada-rca-baselines-common/bin/python

python scripts/run_baseline_confirmatory.py freeze-environment \
  --method TraceRCA \
  --python /home/zhangll24/.venvs/ada-rca-baselines-common/bin/python

git add artifacts/baseline_eval/execution_v1/environments/tracerca.json
git commit -m "eval: freeze TraceRCA execution environment"

python scripts/run_baseline_confirmatory.py run-method \
  --method TraceRCA \
  --attempt-id tracerca-a1-20260831 \
  > /home/zhangll24/RCA_project/Ada-RCA-baseline-task-logs/tracerca-a1-20260831.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/tracerca/tracerca-a1-20260831 \
  artifacts/baseline_eval/execution_v1/locks/tracerca_prediction_lock.json
git commit -m "eval: freeze label-free TraceRCA predictions"
git status --short --branch
```

## mmBARO task

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baseline-tasks/mmbaro
source ~/.venvs/ada-rca-baselines-common/bin/activate
set -euo pipefail
command -v python
python --version

python scripts/run_baseline_confirmatory.py global-preflight
python scripts/run_baseline_confirmatory.py preflight-environment \
  --method mmBARO \
  --python /home/zhangll24/.venvs/ada-rca-baselines-common/bin/python

python scripts/run_baseline_confirmatory.py freeze-environment \
  --method mmBARO \
  --python /home/zhangll24/.venvs/ada-rca-baselines-common/bin/python

git add artifacts/baseline_eval/execution_v1/environments/mmbaro.json
git commit -m "eval: freeze mmBARO execution environment"

python scripts/run_baseline_confirmatory.py run-method \
  --method mmBARO \
  --attempt-id mmbaro-a1-20260831 \
  > /home/zhangll24/RCA_project/Ada-RCA-baseline-task-logs/mmbaro-a1-20260831.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/mmbaro/mmbaro-a1-20260831 \
  artifacts/baseline_eval/execution_v1/locks/mmbaro_prediction_lock.json
git commit -m "eval: freeze label-free mmBARO predictions"
git status --short --branch
```

## Resume after a task interruption

Resume only from the same assigned task worktree and exact execution commit.
Do not commit partial records before resuming.

```bash
source <THE-SAME-ENVIRONMENT>/bin/activate
cd <THE-SAME-ASSIGNED-WORKTREE>
git status --short --branch
python scripts/run_baseline_confirmatory.py run-method \
  --method <METHOD> \
  --attempt-id <THE-SAME-ATTEMPT-ID> \
  --resume \
  >> /home/zhangll24/RCA_project/Ada-RCA-baseline-task-logs/<THE-SAME-LOG>.log 2>&1
```

This generic resume procedure does not apply to the MicroRank, TraceRCA, or
mmBARO A1 attempts affected by the V1.2 raw-trace parser amendment. Retain
those A1 attempts and use the recovery procedure below.

## V1.2 raw-trace parser recovery

Run these blocks only after the V1.2 repair has been committed. Before each
block, verify that no process for that method is active. Replace
`<TRACE_CSV_REPAIR_COMMIT>` with the coordinator-provided repair commit. The
already committed environment manifests are reused unchanged.

### MicroRank A1 archive and A2 restart

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baseline-tasks/microrank
source ~/.venvs/ada-rca-baselines-common/bin/activate
set -euo pipefail

git add artifacts/baseline_eval/execution_v1/records/microrank/microrank-a1-20260831
git commit -m "eval: preserve interrupted MicroRank attempt a1"
git cherry-pick <TRACE_CSV_REPAIR_COMMIT>

python scripts/run_baseline_confirmatory.py global-preflight
python scripts/run_baseline_confirmatory.py run-method \
  --method MicroRank \
  --attempt-id microrank-a2-20260901 \
  > /home/zhangll24/RCA_project/Ada-RCA-baseline-task-logs/microrank-a2-20260901.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/microrank/microrank-a2-20260901 \
  artifacts/baseline_eval/execution_v1/locks/microrank_prediction_lock.json
git commit -m "eval: freeze repaired label-free MicroRank predictions"
```

### TraceRCA A1 archive and A2 restart

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baseline-tasks/tracerca
source ~/.venvs/ada-rca-baselines-common/bin/activate
set -euo pipefail

git add artifacts/baseline_eval/execution_v1/records/tracerca/tracerca-a1-20260831
git commit -m "eval: preserve interrupted TraceRCA attempt a1"
git cherry-pick <TRACE_CSV_REPAIR_COMMIT>

python scripts/run_baseline_confirmatory.py global-preflight
python scripts/run_baseline_confirmatory.py run-method \
  --method TraceRCA \
  --attempt-id tracerca-a2-20260901 \
  > /home/zhangll24/RCA_project/Ada-RCA-baseline-task-logs/tracerca-a2-20260901.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/tracerca/tracerca-a2-20260901 \
  artifacts/baseline_eval/execution_v1/locks/tracerca_prediction_lock.json
git commit -m "eval: freeze repaired label-free TraceRCA predictions"
```

### mmBARO A1 archive and A2 restart

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baseline-tasks/mmbaro
source ~/.venvs/ada-rca-baselines-common/bin/activate
set -euo pipefail

git add artifacts/baseline_eval/execution_v1/records/mmbaro/mmbaro-a1-20260831
git commit -m "eval: preserve interrupted mmBARO attempt a1"
git cherry-pick <TRACE_CSV_REPAIR_COMMIT>

python scripts/run_baseline_confirmatory.py global-preflight
python scripts/run_baseline_confirmatory.py run-method \
  --method mmBARO \
  --attempt-id mmbaro-a2-20260901 \
  > /home/zhangll24/RCA_project/Ada-RCA-baseline-task-logs/mmbaro-a2-20260901.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/mmbaro/mmbaro-a2-20260901 \
  artifacts/baseline_eval/execution_v1/locks/mmbaro_prediction_lock.json
git commit -m "eval: freeze repaired label-free mmBARO predictions"
```

## Central integration after tasks finish

Cherry-pick each task's environment commit followed by its prediction commit.
The exact commit IDs come from the task branches.

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
git cherry-pick <MICROCAUSE_ENV_COMMIT> <MICROCAUSE_PREDICTION_COMMIT>
git cherry-pick <MICRORANK_ENV_COMMIT> <MICRORANK_PREDICTION_COMMIT>
git cherry-pick <TRACERCA_ENV_COMMIT> <TRACERCA_PREDICTION_COMMIT>
git cherry-pick <MMBARO_ENV_COMMIT> <MMBARO_PREDICTION_COMMIT>

python -m unittest discover -s tests -p 'test_*.py'
python scripts/run_baseline_confirmatory.py global-preflight
```

Do not run `create-global-lock`, `evaluate`, or `report` until CIRCA has a
committed valid lock, every parallel task commit is integrated, and CausalRCA's
non-executed disposition has been committed.
