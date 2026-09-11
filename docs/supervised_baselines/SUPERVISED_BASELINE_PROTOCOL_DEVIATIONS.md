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
