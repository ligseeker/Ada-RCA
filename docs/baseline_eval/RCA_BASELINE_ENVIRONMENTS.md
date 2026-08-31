# RCAEval Baseline Virtual Environments

This document is the activation and environment-routing reference for the
confirmatory RCAEval baselines. Virtual environments are stored outside every
Ada-RCA and RCAEval worktree under `/home/zhangll24/.venvs/`.

## Environment inventory

| Environment | Absolute path | Purpose |
|---|---|---|
| Common RCAEval | `/home/zhangll24/.venvs/ada-rca-baselines-common` | BARO, CIRCA, MicroRank, TraceRCA, mmBARO, and CausalRCA if CausalRCA is re-authorized |
| MicroCause | `/home/zhangll24/.venvs/ada-rca-baselines-microcause` | MicroCause only; pins the legacy Tigramite API required by the pinned RCAEval source |

Both environments use Python 3.10.20 and inherit the audited package stack from
`/home/zhangll24/miniconda3/envs/rcaeval`. The environment directories contain
their own activation scripts and method-specific overrides. Changing or
removing the underlying `rcaeval` Conda environment invalidates both virtual
environments and requires a new preflight and environment freeze.

## Method-to-environment routing

| Method | Activate | Special requirement | Current execution note |
|---|---|---|---|
| BARO | Common RCAEval | None beyond the frozen worker controls | The completed confirmatory attempt remains bound to its historical project-local `.venv` manifest; do not regenerate it |
| CIRCA | Common RCAEval for a future attempt | None beyond the frozen worker controls | Attempt `circa-a1-20260830` is paused after 100/180 terminal records without a prediction lock; it remains bound to the frozen project-local `.venv` and must not be restarted automatically |
| MicroCause | MicroCause | `tigramite==4.2.2.1` | Authorized for an isolated parallel task |
| MicroRank | Common RCAEval | Fixed `PYTHONHASHSEED=20260830` through the runner | Authorized for an isolated parallel task |
| TraceRCA | Common RCAEval | None beyond the frozen worker controls | Authorized for an isolated parallel task |
| mmBARO | Common RCAEval | Official `mm-ob` / `mm-tt` dataset keys are enforced by the adapter | Authorized for an isolated parallel task |
| CausalRCA | Common RCAEval if re-authorized | CUDA availability plus the saved GPU amendment | Deferred; do not freeze or run unless the method is explicitly restored |

RCD and the context-only methods are not part of this environment map because
they are not authorized for the current confirmatory execution.

## Activation commands

Activate the common environment:

```bash
source ~/.venvs/ada-rca-baselines-common/bin/activate
```

Activate the MicroCause environment:

```bash
source ~/.venvs/ada-rca-baselines-microcause/bin/activate
```

Set the clean RCAEval checkout and Ada-RCA harness on `PYTHONPATH` for manual
import or synthetic checks:

```bash
export PYTHONPATH=/home/zhangll24/RCA_project/RCAEval-clean:/home/zhangll24/RCA_project/Ada-RCA-baselines
```

Confirm the active interpreter:

```bash
command -v python
python --version
```

Leave the environment before activating another one:

```bash
deactivate
```

## Formal runner usage

Activation is convenient for interactive work, but formal freezes should pass
the absolute interpreter path so that the environment identity is unambiguous.

An environment may be checked with the read-only command below. It runs two
synthetic predictions and both dataset schema checks, but writes no artifact
and does not authorize real execution:

```bash
python scripts/run_baseline_confirmatory.py preflight-environment \
  --method MicroRank \
  --python /home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
```

Common environment example:

```bash
source ~/.venvs/ada-rca-baselines-common/bin/activate
python scripts/run_baseline_confirmatory.py freeze-environment \
  --method MicroRank \
  --python /home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
```

MicroCause example:

```bash
source ~/.venvs/ada-rca-baselines-microcause/bin/activate
python scripts/run_baseline_confirmatory.py freeze-environment \
  --method MicroCause \
  --python /home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python
```

Under the V1.1 parallel amendment, different methods may freeze and execute in
separate task containers without waiting for preceding registry entries. Each
task must use its own Git working copy and method-scoped artifacts. See
`RCA_BASELINE_PARALLEL_RUNBOOK_V1_1.md` for the full commands.

## Recreation commands

The environments were created outside the project from the audited Python
3.10 base:

```bash
mkdir -p /home/zhangll24/.venvs

/home/zhangll24/miniconda3/envs/rcaeval/bin/python3.10 -m venv \
  --system-site-packages \
  /home/zhangll24/.venvs/ada-rca-baselines-common

/home/zhangll24/miniconda3/envs/rcaeval/bin/python3.10 -m venv \
  --system-site-packages \
  /home/zhangll24/.venvs/ada-rca-baselines-microcause

/home/zhangll24/.venvs/ada-rca-baselines-microcause/bin/python -m pip install \
  --no-deps 'tigramite==4.2.2.1'
```

Do not recreate or mutate an environment after a method's first real case has
started. A changed environment requires a new attempt and a new frozen
environment manifest.

## Verification record

Environment identity observed on 2026-08-31:

- both environments: Python 3.10.20;
- common: Torch 2.8.0, CUDA build 12.8, Tigramite 5.2.10.1, NetworkX 2.5;
- MicroCause: Tigramite 4.2.2.1.

Synthetic checks completed from the external environments:

| Method | Status | Fingerprint |
|---|---|---|
| BARO | `PASS` | `5baa59716de4674de9983767c195e5de64c7408461b8c8fae2b47322a500b8f6` |
| MicroCause | `PASS` | `594e370ebd9cbc7da54d97e8cd3d6fc0084961fd08bdb8ca3ef31b6e1df5a0ea` |
| MicroRank | `PASS` | `8495edcc420230bc760d43bba175cec747bf2c0edda21ef5b5a80c4450e2a491` |
| TraceRCA | `PASS` | `b56fedf7a64308ce1ba3f915712b3672ae029c060e319ff1d942628751dfb125` |
| mmBARO | `PASS` | `233b5ca861daaaab6f39198b5244a1f858b6a753a74a1bed1812527029eaec49` |

Every synthetic result reported that its native module path was inside the
clean pinned RCAEval checkout. CIRCA was not re-run during this check because
its formal attempt was already running. CausalRCA imported from the clean
checkout and the common environment contains the CUDA-enabled Torch build, but
no CUDA device was available at verification time. CUDA availability must be
checked again before any future CausalRCA environment freeze.
