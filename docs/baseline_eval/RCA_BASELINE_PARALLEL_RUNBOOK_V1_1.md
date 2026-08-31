# RCAEval Parallel Baseline Runbook V1.1

This runbook contains the copy-and-run commands for separate task containers.
Use one task per method. Replace `<PARALLEL_BASE_COMMIT>` with the committed
revision that contains the V1.1 parallel amendment and harness.

## Common task rules

Run every task from its own Ada-RCA working copy. Do not point two tasks at the
same worktree. Store console logs outside the repository so the clean-worktree
preflight is not tripped.

Before starting a task:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines
git switch --detach <PARALLEL_BASE_COMMIT>
git switch -c execution/<METHOD-SLUG>-a1-20260831
git status --short --branch
```

The four currently runnable methods are independent. Their task branches may
run at the same time. BARO is complete, CIRCA retains its separate legacy
recovery workflow, and CausalRCA must not be run.

## MicroCause task

```bash
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
  > /tmp/ada-rca-microcause-a1-20260831.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/microcause/microcause-a1-20260831 \
  artifacts/baseline_eval/execution_v1/locks/microcause_prediction_lock.json
git commit -m "eval: freeze label-free MicroCause predictions"
git status --short --branch
```

## MicroRank task

```bash
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
  > /tmp/ada-rca-microrank-a1-20260831.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/microrank/microrank-a1-20260831 \
  artifacts/baseline_eval/execution_v1/locks/microrank_prediction_lock.json
git commit -m "eval: freeze label-free MicroRank predictions"
git status --short --branch
```

## TraceRCA task

```bash
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
  > /tmp/ada-rca-tracerca-a1-20260831.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/tracerca/tracerca-a1-20260831 \
  artifacts/baseline_eval/execution_v1/locks/tracerca_prediction_lock.json
git commit -m "eval: freeze label-free TraceRCA predictions"
git status --short --branch
```

## mmBARO task

```bash
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
  > /tmp/ada-rca-mmbaro-a1-20260831.log 2>&1

git add \
  artifacts/baseline_eval/execution_v1/records/mmbaro/mmbaro-a1-20260831 \
  artifacts/baseline_eval/execution_v1/locks/mmbaro_prediction_lock.json
git commit -m "eval: freeze label-free mmBARO predictions"
git status --short --branch
```

## Resume after a task interruption

Resume only from the same task working copy and exact execution commit. Do not
commit partial records before resuming.

```bash
source <THE-SAME-ENVIRONMENT>/bin/activate
git status --short --branch
python scripts/run_baseline_confirmatory.py run-method \
  --method <METHOD> \
  --attempt-id <THE-SAME-ATTEMPT-ID> \
  --resume \
  >> /tmp/<THE-SAME-LOG>.log 2>&1
```

## Central integration after tasks finish

Cherry-pick each task's environment commit followed by its prediction commit.
The exact commit IDs come from the task branches.

```bash
git switch evaluation/rcaeval-baselines
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
