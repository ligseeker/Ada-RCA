# RCAEval V2 Combined Six-Method Lock Amendment V1

Status: **USER-AUTHORIZED ADDITIVE COMBINED-LOCK AMENDMENT**<br>
Date: 2026-09-07<br>
Base protocol: `RCA_BASELINE_RESCUE_PROTOCOL_V2`<br>
Base protocol digest:
`dbba81fae2b879bc77084bd6cc07c207c4a9f30dc5a286eb6b1533b0144429de`<br>
CausalRCA CPU extension digest:
`fe46fc498507370563452aa3b31fa65938f5a23c6850586a22afcafa0787551b`<br>
Combined protocol digest:
`24419f179d44ee09f082a23173a0d35c5ec2d3d5592cd93ff9a2afe1d0591e54`

## Purpose and scope

This amendment records the user's instruction to produce one final V2 table for
the five completed V2 baselines plus the authorized CausalRCA CPU extension:

`CIRCA -> MicroCause -> MicroRank -> TraceRCA -> mmBARO -> CausalRCA`

It is additive. The frozen five-method protocol, its method locks, and its
optional five-method global lock are not rewritten. The combined lock binds the
active lock for each of the six methods, the frozen input manifest, the pinned
RCAEval checkout, and the frozen Ada-RCA reference before any labels are joined
or metrics are computed.

The machine-readable binding is
`artifacts/baseline_eval/rescue_protocol_v2_causalrca_combined.json`.
The six-method global lock is
`artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json`.
The combined evaluation artifacts are written under
`artifacts/baseline_eval/execution_v2/evaluation_causalrca/`.

## Frozen evaluation rules

- Use the already committed method records and locks; do not rerun a method.
- Keep RE2-OB and RE2-TT separate with 90 cases per dataset.
- Treat only legal `METHOD_FAILURE` as zero utility; all other blocking statuses
  prevent lock creation and evaluation.
- Compute AC@1, AC@3, AC@5, Avg@5, fault-level rows, robustness rows, and the
  10,000-resample fault-stratified paired bootstrap specified by V2.
- Keep baseline MRR `NOT-IDENTIFIABLE`; no candidate completion is allowed.
- Read labels and prediction contents only after the committed combined lock.

## Authorized transition

The central coordinator may run:

```bash
cd /home/zhangll24/RCA_project/Ada-RCA-baselines-eval-admin
COMMON_PY=/home/zhangll24/.venvs/ada-rca-baselines-common/bin/python
"$COMMON_PY" scripts/run_baseline_rescue_v2.py create-global-lock-v2-causalrca
git add artifacts/baseline_eval/execution_v2/prediction_lock_v2_causalrca.json
git commit -m "eval: create combined V2 global prediction lock"
"$COMMON_PY" scripts/run_baseline_rescue_v2.py verify-global-lock-v2-causalrca
```

Only after that lock commit:

```bash
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 evaluate-v2-causalrca
git add artifacts/baseline_eval/execution_v2/evaluation_causalrca
git commit -m "eval: compute combined six-method V2 metrics"
"$COMMON_PY" -m src.baseline_eval.evaluation_v2 render-report-v2-causalrca
git add docs/baseline_eval/RCA_BASELINE_CONFIRMATORY_RESULTS_V2.md
git commit -m "docs: publish combined six-method V2 baseline table"
```

The resulting report includes the six requested baselines and the frozen
Ada-RCA reference row; it does not pool the two datasets.
