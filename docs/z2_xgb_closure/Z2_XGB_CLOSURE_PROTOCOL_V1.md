# Ada-RCA V1 Z2-XGB Scientific Attribution Closure Protocol V1

Status: `FROZEN BEFORE FORMAL Z2-XGB RESULTS`

Freeze date: 2026-09-12 (Asia/Shanghai)

Starting source: `evaluation/supervised-baselines@c15e054ecbff9a7a54f26cb24c2e804c269da641`

Worktree: `/home/zhangll24/RCA_project/Ada-RCA-z2-xgb-closure`

Branch: `evaluation/z2-xgb-closure`

This protocol is the final scientific-attribution closure for Ada-RCA V1. It
does not authorize Ada-RCA V2 development, a new representation, a new
baseline family, parameter search, topology changes, or any modification of
the frozen Ada-RCA method or historical supervised-baseline artifacts.

## 1. Scientific question

The preceding supervised-baseline track showed that Z1-XGB is approximately
competitive with Ada-RCA V1 on RE2-OB and is higher on RE2-TT Avg@5. That
observation cannot distinguish whether Ada-RCA's behavior is attributable to
the compact Z2 morphology representation, to its frozen Conditional Logit
scorer, or to their interaction.

This closure asks:

- **Q1:** With the scorer held fixed at the XGBoost pairwise ranker, does Z2
  provide information beyond Z1?
- **Q2:** With the representation held fixed at Z2, is the nonlinear XGBoost
  scorer stronger than the frozen Ada-RCA Conditional Logit scorer?
- **Q3:** Across both axes, is the observed contribution primarily
  representation, scorer, or representation-scorer interaction?

The primary controlled contrast is `Z2-XGB - Z1-XGB`, with `Avg@5` as the
primary metric. Secondary controlled contrasts are `AC@1` and `MRR`. The
scorer contrast is `Z2-XGB - Ada-RCA V1` (where Ada-RCA V1 is Z2-Conditional
Logit).

## 2. Fixed 2x2 attribution matrix

| Representation | Linear / Conditional Logit | Nonlinear / XGBRanker |
|---|---|---|
| Z1 | authoritative historical Z1-CL (`P4-G0` variant `a0`) | authoritative completed Z1-XGB |
| Z2 | authoritative Ada-RCA V1 (`Z2-CL`) | **new formal Z2-XGB** |

The Z1-CL row is not redefined or refit in this closure. Its authoritative
source is the immutable Git object:

```text
d36ad67:artifacts/p4_g0/predictions/a0/re2ob/
d36ad67:artifacts/p4_g0/predictions/a0/re2tt/
```

Those artifacts declare `variant: a0`, `representation: z1`, feature
dimension 32, lambda 1.0, train-fold-only StandardScaler, seed 20260826, and
frozen three-fold OOF. Their overall metrics are read from the committed
historical artifacts and are not recomputed as a new model.

The Z2-CL row is the current frozen Ada-RCA V1 artifact:

```text
artifacts/final_method/re2ob/
artifacts/final_method/re2tt/
```

The completed Z1-XGB row is read from the already-authoritative supervised
baseline artifact:

```text
artifacts/supervised_baselines/xgb_ranker/re2ob/
artifacts/supervised_baselines/xgb_ranker/re2tt/
```

The completed Trajectory-TCN artifacts are used only for the requested
case-level diagnostic comparison and are not part of the 2x2 attribution
matrix.

## 3. Frozen representation and input identity

Z2-XGB must load the same committed feature archives used by Ada-RCA V1. No
feature extraction, approximation, reimplementation, scaling, imputation, or
archive regeneration is allowed.

For each `artifacts/features/<dataset>/<case_id>.npz`, the prediction-visible
arrays are:

```text
base: candidate x 4 x 8       -> Z1: candidate x 32
z2:   candidate x 4 x 9       -> morphology block: candidate x 36
Z2 = concatenate((base, z2), axis=2).reshape(candidate_count, 68)
```

This is the committed frozen operation in `src/rca/features.py` and the
representation consumed by `src/rca/final_method.py`. The authoritative
feature order is `FINAL_Z2_FEATURE_NAMES` in that module and in each frozen
Ada-RCA `config.json`. The feature-order SHA-256 is:

```text
0acf244e629a5e62e3cca82f33f01cd25157ffaf2843f985b46755b615637dfa
```

The representation authority is:

```text
docs/REPRESENTATION_FREEZE.md
SHA-256 740fbf8a48c0753c19d8450e92ed2a1e80f81cfae9f34c354fd83ab1b12f4387
```

The committed input identities are:

| Item | RE2-OB | RE2-TT |
|---|---|---|
| feature archive count | 90 | 90 |
| candidate count | 11 | 68 |
| feature manifest SHA-256 | `cc171f32c7642c6ddbe59b5b52bb6f8351dd8d8a35289144277900bbbb1da4ed` | `ac0424a4018624a61e993649e2b94c678838a2d02dfc4bf8f5c1b0694a145256` |
| candidate registry SHA-256 | `9eae7e79662ade83e0f6034073ab5c424bbf93be5765bd4bc5ea51d90c0efd19` | `67ad834a58be40802d9a8071ae849b7812ee390b87b08b5d82567596a39d236a` |
| assignment SHA-256 | `ca576819554ebe3d1cddd8f261bb661e7111896ff7b7dd6258e9f5daafad5195` | `88b4615ed3c950569e9f4e4c9e66a302e8f88adf1715a8457540e00390b68e7` |

Before formal execution, a read-only identity audit must verify for all 180
archives: filename equals embedded case ID; case IDs equal the committed
assignment universe; candidate order equals the committed registry; `base`
has shape `candidate x 4 x 8`; `z2` has shape `candidate x 4 x 9`; the
concatenated result has shape `candidate x 68`; and every value is finite.
The audit must persist the per-archive SHA-256 values and a representation
identity summary. A failed identity check is a hard stop; no alternative Z2
pipeline is authorized.

## 4. Frozen XGB scorer and controlled-variable rule

The only experimental change from Z1-XGB is the input representation:

```text
Z1 32D -> Z2 68D
```

The scorer must remain semantically identical to the completed Z1-XGB scorer:

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

There is no scaler, class weighting, feature selection, early stopping,
validation, checkpoint selection, tuning, search, alternate objective, or
parameter override. The new runner must preserve the existing Z1-XGB module
and artifacts unchanged. Its configuration audit must compare every scorer
parameter against `src/rca/supervised_baselines/xgb_ranker.py`; only the
representation/method identity fields may differ.

## 5. Frozen OOF design and label firewall

RE2-OB and RE2-TT are run independently. Each has 90 cases and the exact
committed repetition 3-fold split:

- fold 0: 60 train, 30 test;
- fold 1: 60 train, 30 test;
- fold 2: 60 train, 30 test.

The candidate registries and case IDs must be identical to Ada-RCA V1, Z1-XGB,
and Trajectory-TCN. Event rows remain contiguous and use canonical candidate
order. Each training group has exactly one positive root and group size 11
for RE2-OB or 68 for RE2-TT.

Training receives Z2 arrays and `root_service` only for the 60 outer-training
cases. Test prediction receives Z2 arrays, opaque case IDs, fold metadata, and
the legal candidate registry only. Test roots and fault types are absent from
fit and predict calls and are joined only after every complete test candidate
score vector and ranking has been persisted. They are used only by the
evaluator, case metrics, fault stratification, and final serializer.

## 6. Required formal artifacts

Formal output is create-once and isolated under:

```text
artifacts/z2_xgb_closure/z2_xgb/
  re2ob/{fold_0,fold_1,fold_2,aggregate}/
  re2tt/{fold_0,fold_1,fold_2,aggregate}/
```

Each fold must contain at least:

```text
config.json
environment.json
firewall.json or label_firewall.json
integrity.json
model_state.ubj
predictions.jsonl
metrics.json
provenance.json
checksums.json
```

Each case in `predictions.jsonl` must contain the full candidate permutation,
finite scores, contiguous ranks, fold, dataset, and post-evaluation root
fields. No ranking completion, candidate deduplication, root substitution, or
failure repair is allowed. Aggregate artifacts must retain 90 cases per
dataset, raw candidate rows, case metrics, overall metrics, fault/root/fold
strata, provenance, integrity, and checksums.

## 7. Metrics and primary contrasts

The retained evaluator arithmetic is authoritative. Report separately for
RE2-OB and RE2-TT:

```text
AC@1, AC@3, AC@5, Avg@5, MRR
```

Also report fault strata:

```text
CPU, MEM, DISK, SOCKET, DELAY, LOSS
```

The primary contrast is:

```text
Z2-XGB - Z1-XGB
```

with `Avg@5` primary and `AC@1`/`MRR` secondary. The scorer contrast is:

```text
Z2-XGB - Ada-RCA V1 (Z2-CL)
```

For both contrasts and both datasets, use the existing fault-stratified paired
bootstrap implementation, exactly 10,000 resamples, seed `20260826`, pairing
by case ID only. Report point delta and 95% percentile interval for `Avg@5`,
`AC@1`, and `MRR`. Add the required `AC@1` paired diagnostics even if an
earlier artifact reports only `Avg@5`.

## 8. Case-level root-rank diagnostics

All comparison inputs must be aligned by exact case ID and verified to contain
the same 90 cases within each dataset. For a comparison `new` versus `old`:

```text
improved  = new root rank < old root rank
unchanged = new root rank = old root rank
degraded  = new root rank > old root rank
```

Required comparisons are:

1. Z1-XGB versus Ada-RCA V1, with special attention to RE2-TT;
2. Z2-XGB versus Z1-XGB, isolating the representation change under XGB;
3. Z2-XGB versus Ada-RCA V1, isolating the scorer change at Z2.

For each comparison report overall OB/TT transition counts and transition
counts by `fault_type`, `root_service`, and `fold`. The TT discussion must
explicitly include MEM, DELAY, and LOSS. No subgroup is used for model
selection, tuning, rescue, or post-hoc output repair.

Trajectory-TCN is included only as an additional case-level diagnostic source;
it does not create another matrix cell or authorize a new experiment.

## 9. Attribution calculations

Use the four matrix cells to report:

```text
Delta_morph_linear = Z2-CL - Z1-CL
Delta_morph_xgb    = Z2-XGB - Z1-XGB
```

If their signs or magnitudes differ, report the representation-by-scorer
interaction explicitly rather than attributing the difference to morphology
alone. The report must distinguish point estimates, paired uncertainty, and
scientific inference. It must not interpret a higher score in one dataset as
universal superiority.

## 10. Pre-frozen scientific interpretation matrix

The disposition is determined after integrity checks and the prespecified
statistics; it is not chosen to favor Ada-RCA.

### Case A: nonlinear morphology contribution supported

If `Z2-XGB > Z1-XGB` in both OB and TT point estimates, with a materially
positive and preferably bootstrap-supported effect, conclude that compact Z2
morphology retains incremental information under a stronger nonlinear scorer.
The representation contribution may remain a substantive claim, bounded by the
two datasets and the observed uncertainty.

### Case B: Z1 contains most information

If `Z2-XGB` is approximately `Z1-XGB`, the gain is small, or intervals broadly
cross zero, conclude that Z1 likely contains most RCA information and Z2's main
value may be to make complex temporal relations explicit and usable by a
simple linear scorer. Position Ada-RCA as compact, interpretable,
lightweight, and linear-friendly rather than uniformly performance-superior.

### Case C: morphology trade-off under nonlinear scoring

If `Z2-XGB < Z1-XGB`, especially consistently across both datasets, conclude
that compact Z2 may compress information useful to the nonlinear scorer.
Shrink the morphology-performance claim and preserve the unfavorable result;
do not alter Z2 or the XGB configuration.

In every case, independently decide whether the method is retained:

```text
ADA_RCA_METHOD_RETAIN
or
ADA_RCA_METHOD_RETAIN_WITH_REFRAMED_CLAIM
```

No result in this closure alone licenses `ADA_RCA_METHOD_INVALID`.

## 11. Service-fingerprint evidence synthesis

Do not add a leave-one-root experiment. The report must synthesize the already
available S2 pre-event-only and S3 service-identity-probe evidence, keeping
their evidence class and protocol identity explicit. Discuss whether strong
XGB performance could partly exploit stable service fingerprints through
feature interactions. This is interpretation only and cannot trigger a new
experiment in this closure.

## 12. Prohibited actions and stop rules

The following are out of scope and prohibited:

- new representations, features, topology, data, or baselines;
- LightGBM, MLP, Transformer, GNN, ensemble, or alternate XGB objective;
- changing Ada-RCA, Z2 definitions, candidate registries, labels, splits, or
  XGB parameters;
- feature selection, scaler insertion, class weighting, early stopping,
  tuning, search, or TT/OB-specific changes;
- merging events, changing root labels, completing partial rankings, or using
  test labels before complete prediction output;
- re-running Z1-CL under a newly defined implementation;
- changing the interpretation after seeing subgroup results.

If the committed Z2 archive identity, feature order, candidate order, case
universe, or provenance cannot be verified, stop formal Z2-XGB execution and
report `BLOCKED`. If a fold crashes, preserve the failed artifact, do not
auto-retry it, and report the remaining commands. A partial result is not a
complete attribution closure.

## 13. Validation requirements

Before accepting formal results, tests and validators must establish:

- Z2 dimension 68, feature-order digest, archive checksums, case IDs, and
  candidate order match the frozen Ada-RCA representation;
- XGB scorer parameters equal the completed Z1-XGB parameters;
- every training group has size 11/68 and one positive root;
- test labels are absent from fit/predict paths and joined only post-ranking;
- each dataset has 90 cases, each fold has 60/30 cases, and each prediction
  is a complete finite permutation;
- rerunning the same fold is deterministic without replacing the formal
  create-once artifact;
- all diagnostic case IDs align exactly and every paired bootstrap pair uses
  the same case ID.

## Material Passport

- Origin Skill: `academic-research-suite / experiment-agent`
- Origin Mode: `run + validate`
- Artifact type: preregistered scientific-attribution closure protocol
- Verification status: `FROZEN BEFORE FORMAL Z2-XGB RESULTS`
- Evidence boundary: inherited Z1-CL, Z1-XGB, Z2-CL, and TCN artifacts remain
  immutable; only the new Z2-XGB closure namespace may be created.
