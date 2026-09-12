# Supervised Baseline Protocol Deviation Ledger

## A1: wrong process hash seed

- Detected: 2026-09-11 during live execution, before aggregation or gate use.
- Required: `PYTHONHASHSEED=20260826`.
- Observed: delegated runners used `PYTHONHASHSEED=20260830`, inherited from
  the separate RCAEval external-baseline runbook.
- Affected outputs: six Z1-LR folds, six Z1-XGBRanker folds, completed
  Trajectory-TCN RE2-OB fold 0, and interrupted Trajectory-TCN RE2-OB fold 1.
- Disposition: `INVALID_PROTOCOL_ENV`; none of these outputs may be aggregated,
  reported as the supervised-baseline result, or used by the DejaVu gate.
- Preservation: original bytes are retained below
  `artifacts/supervised_baselines/invalid_attempts/pythonhashseed_20260830/`.
- Corrective action: the runner now fails before artifact creation unless the
  process environment exactly contains `PYTHONHASHSEED=20260826`. Correct A2
  runs use the original frozen model configurations, seeds, features, splits,
  and output schemas. No configuration was changed after viewing A1 results.

This is an execution-environment correction, not a performance-driven rerun.

## A2: custom replay output rejected by the worktree firewall

- Detected: 2026-09-12 from `/home/zhangll24/RCA_project/logs/run.log`.
- Observed: the first fresh-replay LR fold completed, after which 17 remaining
  fold commands failed with `formal run rejects non-artifact worktree changes`.
- Root cause: the runner allowed only the hard-coded
  `artifacts/supervised_baselines/` prefix instead of also recognizing the
  explicit `--output-root artifacts/supervised_baselines_replay` namespace.
- Downstream effect: six aggregation commands raised `FileNotFoundError`
  because the rejected runs had produced no fold status files. The replay gate
  was therefore correctly `PENDING` but is not a valid final replay gate.
- Disposition: the incomplete replay is preserved under
  `artifacts/supervised_baselines_replay/`, marked
  `INVALID_EXECUTION_ORCHESTRATION`, and excluded from formal results.
- Corrective action: commit `f4977e9` permits untracked output only under the
  canonical namespace or the explicit `artifacts/supervised_baselines[_*]`
  output root. Source changes, tracked artifact modifications, and unrelated
  in-worktree output roots remain rejected.
- Verification: the exact regression test failed before the patch and passed
  after it; two sequential LR folds then completed under a new custom output
  root. No feature, model, loss, seed, split, or evaluator changed.

This is an execution-harness repair, not a performance-driven model change.

## A3: recorded package-version difference during TCN completion

- Observed: the retained earlier folds record NumPy/Pandas/scikit-learn
  `1.24.1/1.5.3/1.2.1`; the later TCN TT folds record
  `1.24.4/2.0.3/1.3.2`. Python 3.8.20, SciPy 1.10.1, Torch 1.12.0, CPU device,
  model configuration, and seed are unchanged.
- Audit: TCN TT fold 0 was replayed once in the later environment. All 2,040
  candidate rows, complete ranks, root ranks, metrics, and candidate scores
  match the retained formal fold exactly; maximum absolute score delta is 0.0.
- Disposition: `EXACT_REPLAY_PASS`; the audit is retained under
  `artifacts/supervised_baselines_env_drift_audit/` and is excluded from formal
  aggregation. The completed TCN TT aggregate and DejaVu gate remain valid.

This is a disclosed environment difference with exact non-impact evidence.

## A4: DejaVu raw-data preflight correction before training

- Detected: 2026-09-12 during the first label-blind RE2-OB source audit, before
  DejaVu dataset preparation, dependency installation, training, prediction,
  or result inspection.
- Initial rule: every one of the 20 exact CPU/MEM samples had to be finite and
  every repeated `(traceID, spanID)` key was blocking.
- Observed source facts: two truncated metric files lack only late post-event
  rows; five other files contain sparse blank CPU cells. Every such gap has a
  preceding finite value in the same event series. Two trace files repeat 48
  and 99 span keys respectively, but every repeated key resolves to the same
  service; there is no conflicting parent-service mapping.
- Correction: reproduce DejaVu's official forward-fill behavior within each
  event and metric series, resetting state at event boundaries. Leading gaps
  remain blocking. Record all duplicate span keys, but block only keys whose
  duplicates map the same `(traceID, spanID)` to conflicting candidate
  services.
- Scientific impact: this is a pre-training data-compatibility correction to
  match documented upstream missing-value semantics. It does not use labels,
  scores, rankings, test metrics, or performance feedback and does not change
  metric channels, graph edges, model architecture, loss, or hyperparameters.

The first `FAIL` audit artifact is retained as chronological diagnostic
evidence until superseded by a new create-once attempt; it is not an input or
result artifact.

## A5: DejaVu minimal environment closure preflight

- Detected: 2026-09-12 after isolated-environment installation and before
  DejaVu dataset preparation, training, prediction, or result inspection.
- Observed: `pip check` passed, but importing the pinned official GAT path
  failed because `utils/load_model.py` imports the official requirement
  `regex`, which the initial minimal runtime closure omitted.
- Correction: add the upstream-pinned `regex==2021.11.10` requirement and
  rerun the import/graph smoke test. The environment remains isolated at
  `~/.venvs/ada-rca-dejavu`; no existing baseline environment is modified.
- Scientific impact: none. This restores an official runtime dependency and
  changes no data, topology, model, loss, split, seed, or hyperparameter.

## A6: DejaVu official scientific-stack closure preflight

- Detected: 2026-09-12 during the second pinned-source import smoke and before
  dataset preparation, training, prediction, or result inspection.
- Observed: after restoring `regex`, official `utils/__init__.py` imported
  `SoftDTW`, which unconditionally imports Numba. Numba was not present in the
  inherited base environment even though it is declared by upstream.
- Correction: install the mutually compatible upstream-era stack only in the
  isolated DejaVu environment: NumPy 1.21.6, SciPy 1.6.3, Pandas 1.4.4,
  scikit-learn 1.0.2, Numba 0.55.2, and llvmlite 0.38.1. Rerun `pip check` and
  the pinned official GAT import/explicit-node-count DGL smoke.
- Scientific impact: none. This restores official runtime dependencies and
  prevents accidental use of the generic baseline environment's newer
  numerical stack. No experiment result exists at this point.
