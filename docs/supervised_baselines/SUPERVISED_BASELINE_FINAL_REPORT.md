# Supervised Baseline Evaluation Final Report

Status: `PARTIAL — DEJAVU_GATE_PENDING`

Date: 2026-09-11

## Material Passport

- Artifact type: controlled experiment result and reproducibility handoff
- Starting source: `main@a2c620922e7c0ab3615d34654d4a3690d1b22c8e`
- Worktree: `/home/zhangll24/RCA_project/Ada-RCA-supervised-baselines`
- Branch: `evaluation/supervised-baselines`
- Formal A2 execution source: `1bdcaa996e0c9499e5623354ac76e6a92723f7ff`
- Evidence status: LR and XGB complete; TCN partial; DejaVu not started
- Verification status: all completed A2 fold checksums, label firewalls,
  candidate permutations, and available 90-case aggregates verified

## A. Protocol

This track adds supervised comparators because the earlier external baselines
were predominantly case-wise unsupervised and therefore did not match Ada-RCA's
root-label supervision. The frozen protocol is
`docs/supervised_baselines/SUPERVISED_BASELINE_PROTOCOL_V1.md`.

All methods reuse the committed RE2-OB and RE2-TT candidate registries, the
repetition-based 3-fold split, frozen telemetry-derived feature archives, and
the retained evaluator. Each dataset has 90 cases; each fold has 60 outer-train
and 30 outer-test cases. Datasets are never pooled for training or headline
evaluation.

Training roots are loaded only for the 60 outer-training events. Prediction
events contain no root or fault field. Test roots are joined only after all
scores and complete rankings for the fold exist. There is no outer-test scaler
fit, early stopping, checkpoint selection, threshold selection, feature
selection, or hyperparameter search.

An initial delegated execution used the wrong process `PYTHONHASHSEED`. It was
detected before aggregation, retained as `INVALID_PROTOCOL_ENV`, and excluded.
The deviation and corrective A2 rule are recorded in
`SUPERVISED_BASELINE_PROTOCOL_DEVIATIONS.md`. No model setting changed after
the invalid attempt.

## B. Methods

- **Z1-LR:** committed Z1 32D, training-candidate-only `StandardScaler`, fixed
  L2 logistic regression, candidate probability ranking.
- **Z1-XGBRanker:** committed Z1 32D, one complete failure event per ranking
  group, fixed `rank:pairwise` XGBoost configuration.
- **Trajectory-TCN:** committed `z` and `q_mask` arrays as 8 x 80 candidate
  sequences, two fixed Conv1D blocks, event-level candidate cross entropy,
  fixed 100 epochs, no validation or early stopping.
- **DejaVu:** `NOT RUN`; its gate cannot be evaluated until TCN TT is complete.

These are comparators, not new Ada-RCA components or method contributions.

## C. Main results

Only complete 90-case OOF aggregates appear as results. `PARTIAL` cells are not
point estimates for the dataset.

| Method | Input | Supervision | OB AC@1 | OB AC@3 | OB AC@5 | OB Avg@5 | OB MRR | TT AC@1 | TT AC@3 | TT AC@5 | TT Avg@5 | TT MRR |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Z1-LR | Z1 32D | supervised | 0.8444 | 0.9556 | 0.9778 | 0.9267 | 0.8957 | 0.5778 | 0.7889 | 0.8667 | 0.7600 | 0.7066 |
| Z1-XGB | Z1 32D | supervised ranker | 0.8889 | 0.9778 | 0.9889 | 0.9578 | 0.9334 | 0.8111 | 0.9222 | 0.9333 | 0.9000 | 0.8716 |
| Trajectory-TCN | z + mask, 8 x 80 | supervised ranker | 0.8222 | 0.9778 | 0.9889 | 0.9422 | 0.8972 | PARTIAL | PARTIAL | PARTIAL | PARTIAL | PARTIAL |
| DejaVu | Metric + FDG | supervised | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN |
| Ada-RCA V1 | Z2 68D | supervised ranker | 0.8778 | 0.9889 | 0.9889 | 0.9622 | 0.9315 | 0.7111 | 0.8667 | 0.9333 | 0.8511 | 0.8035 |

The only completed TCN TT fold is fold 0: 30 cases, AC@1 0.7667, AC@3
0.8667, AC@5 0.9667, Avg@5 0.8733, MRR 0.8372. This is a partial fold result
and is not used as a TT estimate or scientific conclusion.

Optional paired fault-stratified bootstrap diagnostics use
`baseline - Ada-RCA`, 10,000 resamples, seed 20260826. They do not alter the
point-estimate gate:

| Comparator | Dataset | Avg@5 delta | 95% bootstrap interval |
|---|---|---:|---:|
| Z1-LR | RE2-OB | -0.0356 | [-0.0644, -0.0111] |
| Z1-LR | RE2-TT | -0.0911 | [-0.1644, -0.0222] |
| Z1-XGB | RE2-OB | -0.0044 | [-0.0333, 0.0222] |
| Z1-XGB | RE2-TT | +0.0489 | [0.0089, 0.0911] |
| Trajectory-TCN | RE2-OB | -0.0200 | [-0.0533, 0.0133] |

## D. DejaVu gate

`DEJAVU_GATE = PENDING` because `tcn/re2tt` lacks a complete 3-fold aggregate.
Consequently no DejaVu repository audit, adapter, dependency environment, or
experiment was started. The current results cannot be promoted to PASS even
though neither complete comparator strictly exceeds Ada-RCA Avg@5 on both
datasets: the preregistered gate explicitly requires all three comparators.

## E. Scientific questions

### Q1. Does ordinary supervised LR explain Ada-RCA performance?

No on the completed point estimates. Z1-LR is lower than Ada-RCA on both
datasets, including Avg@5 by 0.0356 on OB and 0.0911 on TT. A simple row-wise
classifier using only Z1 therefore does not explain the frozen result.

### Q2. Can nonlinear Z1-XGB replace Z2 morphology?

Not uniformly across datasets. XGB is 0.0044 lower in OB Avg@5 but 0.0489
higher in TT Avg@5. It does not cross-dataset dominate Ada-RCA under the frozen
gate, but it materially challenges any claim that Ada-RCA is uniformly better
than a stronger Z1-only supervised ranker. In particular, TT evidence favors
XGB on the point estimate.

### Q3. Can a full-trajectory TCN replace compact morphology?

Not yet answerable. TCN is lower than Ada-RCA on the complete OB aggregate,
but TT has only one completed fold. The TT fold must not be extrapolated to a
90-case result.

### Q4. Is Ada-RCA competitive with published supervised DejaVu?

Not answerable. DejaVu was correctly not started because its development gate
is pending. Even after a future gate PASS, legal FDG provenance and task mapping
must pass a separate feasibility audit before execution.

## F. Current interpretation

The completed evidence supports Ada-RCA against simple Z1-LR and does not show
cross-dataset domination by Z1-XGB. It does **not** yet establish the overall
claim under all requested same-supervision comparators because TCN TT and
DejaVu are unresolved. The strongest completed counter-evidence is XGB on TT;
therefore the current support for Ada-RCA is qualified, heterogeneous, and not
a general superiority claim.

## G. Completion and blockers

- Z1-LR: `COMPLETE`, 6/6 folds, OB/TT aggregates complete.
- Z1-XGBRanker: `COMPLETE`, 6/6 folds, OB/TT aggregates complete.
- Trajectory-TCN: `PARTIAL`, 4/6 folds; OB complete and TT fold 0 complete.
- DejaVu: `NOT STARTED`, blocked by the pending development gate.

TCN TT fold 0 required 279.2 seconds, compared with 32.7–56.2 seconds per OB
fold. The run stopped after the current fold naturally completed to avoid
unbounded session wait. This is a runtime/session-risk stop, not an
implementation, dependency, numerical, data, or integrity failure.

## H. Commands

Run from the supervised-baseline worktree:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-supervised-baselines
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=20260826
PY=/home/zhangll24/.venvs/ada-rca-supervised-baselines/bin/python
```

Resume only the missing formal TCN work and produce a final gate artifact while
preserving the existing pending gate:

```bash
$PY scripts/supervised_baselines/run_tcn.py --dataset re2tt --fold 1
$PY scripts/supervised_baselines/run_tcn.py --dataset re2tt --fold 2
$PY scripts/supervised_baselines/aggregate_results.py --method tcn --dataset re2tt
$PY scripts/supervised_baselines/aggregate_results.py --gate --gate-output dejavu_gate_final.json
```

Fresh create-once replay of all 18 folds into a separate namespace:

```bash
OUT=artifacts/supervised_baselines_replay

$PY scripts/supervised_baselines/run_logistic.py --dataset re2ob --fold 0 --output-root $OUT
$PY scripts/supervised_baselines/run_logistic.py --dataset re2ob --fold 1 --output-root $OUT
$PY scripts/supervised_baselines/run_logistic.py --dataset re2ob --fold 2 --output-root $OUT
$PY scripts/supervised_baselines/run_logistic.py --dataset re2tt --fold 0 --output-root $OUT
$PY scripts/supervised_baselines/run_logistic.py --dataset re2tt --fold 1 --output-root $OUT
$PY scripts/supervised_baselines/run_logistic.py --dataset re2tt --fold 2 --output-root $OUT

$PY scripts/supervised_baselines/run_xgb_ranker.py --dataset re2ob --fold 0 --output-root $OUT
$PY scripts/supervised_baselines/run_xgb_ranker.py --dataset re2ob --fold 1 --output-root $OUT
$PY scripts/supervised_baselines/run_xgb_ranker.py --dataset re2ob --fold 2 --output-root $OUT
$PY scripts/supervised_baselines/run_xgb_ranker.py --dataset re2tt --fold 0 --output-root $OUT
$PY scripts/supervised_baselines/run_xgb_ranker.py --dataset re2tt --fold 1 --output-root $OUT
$PY scripts/supervised_baselines/run_xgb_ranker.py --dataset re2tt --fold 2 --output-root $OUT

$PY scripts/supervised_baselines/run_tcn.py --dataset re2ob --fold 0 --output-root $OUT
$PY scripts/supervised_baselines/run_tcn.py --dataset re2ob --fold 1 --output-root $OUT
$PY scripts/supervised_baselines/run_tcn.py --dataset re2ob --fold 2 --output-root $OUT
$PY scripts/supervised_baselines/run_tcn.py --dataset re2tt --fold 0 --output-root $OUT
$PY scripts/supervised_baselines/run_tcn.py --dataset re2tt --fold 1 --output-root $OUT
$PY scripts/supervised_baselines/run_tcn.py --dataset re2tt --fold 2 --output-root $OUT

$PY scripts/supervised_baselines/aggregate_results.py --method logistic --dataset re2ob --output-root $OUT
$PY scripts/supervised_baselines/aggregate_results.py --method logistic --dataset re2tt --output-root $OUT
$PY scripts/supervised_baselines/aggregate_results.py --method xgb_ranker --dataset re2ob --output-root $OUT
$PY scripts/supervised_baselines/aggregate_results.py --method xgb_ranker --dataset re2tt --output-root $OUT
$PY scripts/supervised_baselines/aggregate_results.py --method tcn --dataset re2ob --output-root $OUT
$PY scripts/supervised_baselines/aggregate_results.py --method tcn --dataset re2tt --output-root $OUT
$PY scripts/supervised_baselines/aggregate_results.py --gate --output-root $OUT
```

Tests:

```bash
$PY -m unittest discover -s tests -p 'test_*.py' -v
```

There is no DejaVu command in this report because the gate is pending and no
adapter was authorized or implemented.

## I. Agent/runtime disclosure

The execution subtasks were explicitly dispatched with the available
`gpt-5.6-luna` model override. The primary runtime did not expose a
machine-readable self-attestation of its backend model ID, so strict proof that
the main seat was exactly `gpt-5.6-sol` is unavailable. Planning, protocol,
scientific decisions, code review, deviation disposition, aggregation review,
gate handling, and interpretation remained with the primary agent.
