# Supervised Baseline Evaluation Protocol V1

Status: `FROZEN BEFORE FORMAL SUPERVISED-BASELINE RESULTS`

Freeze date: 2026-09-11 (Asia/Shanghai)

Starting source: `main@a2c620922e7c0ab3615d34654d4a3690d1b22c8e`

Track: independent supervised-baseline evaluation. This protocol does not
authorize any change to Ada-RCA V1, its frozen Z2 representation, its candidate
registries, its OOF splits, its predictions, or its historical conclusions.

## 1. Question and scope

This track asks whether generic supervised comparators, trained with the same
root-service supervision as Ada-RCA, explain or dominate the frozen Ada-RCA V1
result. Exactly three generic comparators are authorized before the DejaVu gate:

1. frozen Z1 + row-wise logistic regression (`Z1-LR`);
2. frozen Z1 + event-grouped XGBoost pairwise ranker (`Z1-XGBRanker`);
3. frozen full temporal representation + event-level convolutional TCN
   (`Trajectory-TCN`).

No additional model, representation search, ensemble, topology module, Z2
change, or Ada-RCA rescue is authorized. DejaVu is a later, gated feasibility
track and is not authorized for implementation or execution until Section 10
passes.

## 2. Immutable input identities

The comparators consume the committed source, feature, split, and candidate
artifacts already used by the final method. They do not regenerate the dataset
or define a second preprocessing path.

| Item | RE2-OB | RE2-TT |
|---|---|---|
| Cases | 90 | 90 |
| Candidates per case | 11 | 68 |
| Feature manifest SHA-256 | `cc171f32c7642c6ddbe59b5b52bb6f8351dd8d8a35289144277900bbbb1da4ed` | `ac0424a4018624a61e993649e2b94c678838a2d02dfc4bf8f5c1b0694a145256` |
| Split-manifest SHA-256 | `a672d12be89e91efd7fe69cdf81713b3d18482bba6b46620b0bfd0b4ff7bfd62` | `3c3947d6377433507ca1ea6b69d88f6d8f359b42937bbcff1a7ac98422f05d7e` |
| Assignment SHA-256 | `ca576819554ebe3d1cddd8f261bb661e7111896ff7b7dd6258e9f5daafad5195` | `88b4615ed3c950569ed7e4c4e9c66a302e8f88adf1715a8457540e00390b68e7` |
| Candidate-registry SHA-256 | `9eae7e79662ade83e0f6034073ab5c424bbf93be5765bd4bc5ea51d90c0efd19` | `67ad834a58be40802d9a8071ae849b7812ee390b87b08b5d82567596a39d236a` |

The representation authority is `docs/REPRESENTATION_FREEZE.md`, SHA-256
`740fbf8a48c0753c19d8450e92ed2a1e80f81cfae9f34c354fd83ab1b12f4387`.
The fixed channel order is `metric`, `log`, `trace-error`, `trace-latency`.

## 3. Frozen OOF design

RE2-OB and RE2-TT are trained and evaluated independently. Each uses the
committed three-fold assignment:

- repetition 1 is fold 0;
- repetition 2 is fold 1;
- repetition 3 is fold 2.

For each outer fold, exactly 60 cases are training cases and exactly 30 cases
are test cases. No case or candidate row crosses the boundary. Candidate order
is the committed dataset registry order. Exact score ties are resolved by that
order, which is lexicographic in the frozen registries.

Global experiment seed: `20260826`, reused from the frozen P3 track. Dataset,
fold, and method runs do not select or change this seed based on results.

## 4. Label firewall

Prediction-visible data contain telemetry-derived arrays, opaque case IDs,
dataset, fold assignment, and the legal candidate registry only.

For an outer fold:

- the learner receives root labels only for the 60 outer-training cases;
- scaler fitting, model fitting, and any optimizer state use only those cases;
- the prediction method accepts the 30 test telemetry events without roots,
  fault types, or other label fields;
- test roots are joined only after all candidate scores and complete rankings
  for that fold have been produced;
- test roots are used only by the evaluator and final result serializer.

There is no outer-test normalization, early stopping, hyperparameter selection,
threshold selection, feature selection, architecture selection, or checkpoint
selection. The runner must persist a firewall audit showing the train/test case
sets and that no test label was supplied to model fit or predict.

## 5. Z1-LR freeze

Input is exactly `base.reshape(candidate_count, 32)` from each committed feature
archive. No Z2 field is loaded into this model.

Each event-candidate row has binary training target 1 if and only if the
candidate is the training event's root service. A `StandardScaler` is fit on
outer-training candidate rows only. The classifier is:

```text
sklearn.linear_model.LogisticRegression
penalty = l2
C = 1.0
solver = lbfgs
max_iter = 5000
class_weight = None
random_state = 20260826
```

Candidate score is `predict_proba(...)[positive_class]`. Candidates are ranked
by decreasing score with canonical-order tie-breaking. There is no search.

## 6. Z1-XGBRanker freeze

Input is the same exact 32-dimensional Z1. One outer-training event is one
ranking group: group size 11 on RE2-OB and 68 on RE2-TT. Each group contains one
relevance-1 root and all other candidates at relevance 0. Event rows are kept
contiguous in opaque-case-ID order.

```text
xgboost.XGBRanker
objective = rank:pairwise
n_estimators = 200
max_depth = 3
learning_rate = 0.05
subsample = 1.0
colsample_bytree = 1.0
reg_lambda = 1.0
random_state = 20260826
n_jobs = 1
tree_method = hist
```

No scaler and no search are used. The exact installed XGBoost version and its
legal group argument are recorded before formal execution. If XGBoost cannot be
installed in the external project environment, the method is `BLOCKED`; no
substitute learner is authorized.

## 7. Trajectory-TCN freeze

The temporal source is the committed P3/Z3 component arrays, not raw telemetry
and not a new sequence generator:

- `z`: amplitude-normalized trajectory, shape `candidate x 4 x 80`;
- `q_mask`: observation mask, shape `candidate x 4 x 80`.

The model input concatenates these along the channel axis in the fixed order
`z(metric, log, trace-error, trace-latency), mask(metric, log, trace-error,
trace-latency)`, giving `candidate x 8 x 80`. Numeric missing trajectory values
remain zero only with mask zero. The frozen per-channel
`morphology_active` scalar and the 32-dimensional Z1 summaries are audited but
are not model inputs; they are not broadcast or concatenated. Thus this baseline
tests direct learning from the aligned temporal values and their required
missingness semantics without compact morphology summaries.

Shared candidate encoder:

```text
Conv1d(8, 32, kernel_size=3, padding=1)
ReLU
Dropout(0.2)
Conv1d(32, 64, kernel_size=3, padding=1)
ReLU
Dropout(0.2)
AdaptiveAvgPool1d(1)
Linear(64, 1)
```

Training is event-level. For each event the encoder returns one score per
candidate; cross entropy applies over the complete candidate axis against the
training root index. Fixed training configuration:

```text
PyTorch CPU
Adam
learning_rate = 1e-3
weight_decay = 1e-4
epochs = 100
event_batch_size = 1
seed = 20260826
deterministic algorithms = enabled
validation = none
early stopping = none
checkpoint selection = final epoch only
```

Training-event order is deterministically shuffled from the fixed seed once per
epoch. Training loss may be inspected only for numerical failure (`NaN`,
infinity, or execution failure), never for configuration changes. The required
smoke test is RE2-OB fold 0 using the same configuration; a smoke artifact is
not a formal OOF result. Only code/shape/numerical bug fixes are permitted after
smoke. Any feature, architecture, loss, optimizer, learning-rate, epoch, or seed
change requires a visible protocol deviation before further formal execution.

## 8. Prediction and result schema

Every evaluated candidate row contains:

```text
case_id, candidate, score, rank, root_service, root_rank, fold, dataset
```

`fault_type` may be included for stratification. Each case must contain exactly
the frozen candidate count, each candidate exactly once, ranks 1 through N
exactly once, and the root exactly once. The evaluator never completes or
repairs a ranking.

Each method/dataset artifact includes configuration, environment, provenance,
runtime, raw complete candidate rows, case metrics, aggregate metrics, firewall
audit, integrity audit, and checksums.

## 9. Evaluation

The retained `src/rca/evaluator.py` and its exact arithmetic are authoritative:
`AC@1`, `AC@3`, `AC@5`, `Avg@5`, and `MRR`. Results are reported separately for
RE2-OB and RE2-TT, with optional CPU/MEM/DISK/SOCKET/DELAY/LOSS strata. No pooled
180-case score replaces dataset-specific results.

The immutable Ada-RCA reference is reconstructed from committed
`artifacts/final_method/<dataset>/metrics.json`, whose prediction SHA-256 values
are:

- RE2-OB: `1d3bbc30869062c30569bd7b752cc2520d8e1337b8861bf11e55bbd69eaf5ff5`;
- RE2-TT: `e937897d182735651959ad9449a7d6837ac71b029bec0fe90e143395009dd57d`.

Reference point estimates are not consulted for model development.

## 10. DejaVu development gate

Primary gate metric is dataset-specific `Avg@5`. The gate is evaluated only
after all 18 generic fold-runs (three methods x two datasets x three folds) have
valid, complete OOF artifacts.

`DEJAVU_GATE_FAIL` if at least one of Z1-LR, Z1-XGBRanker, or Trajectory-TCN has
both:

```text
RE2-OB Avg@5 > Ada-RCA V1 RE2-OB Avg@5
AND
RE2-TT Avg@5 > Ada-RCA V1 RE2-TT Avg@5
```

Otherwise the decision is `DEJAVU_GATE_PASS`. Missing or partial generic
results imply `DEJAVU_GATE_PENDING`. This is a development gate based on point
estimates, not a significance claim. Optional fault-stratified paired bootstrap
does not alter the gate.

Only `PASS` authorizes a DejaVu feasibility audit. It does not authorize a
scientifically invalid FDG substitute. If no provenance-bound RE2 dependency
graph can be mapped to DejaVu failure instances, the required outcome is
`DEJAVU_NOT_RUN_FEASIBILITY_BLOCKED`.

## 11. Stop and deviation rules

- Formal output directories are create-once and never silently overwritten.
- A crashed formal run is preserved and is not automatically retried.
- Runtime/session risk may stop after the TCN smoke or any completed folds; the
  remaining commands must be reported and the DejaVu gate stays pending.
- Observed metrics cannot authorize tuning, retries, feature changes, or a new
  comparator.
- All deviations are appended to a separate deviation ledger with time,
  rationale, affected runs, and whether prior artifacts remain valid.

## Material Passport

- Artifact type: preregistered code-experiment protocol
- Evidence status: protocol frozen before new formal comparator results
- Inputs: committed Ada-RCA V1 source/features/splits/reference artifacts
- Output namespace: `artifacts/supervised_baselines/`
- Integrity boundary: no modification of `artifacts/final_method/` or frozen
  Ada-RCA implementation paths
