# Ada-RCA V1 Z2-XGB Scientific Closure Report

Status: `COMPLETE`

Scientific disposition:

```text
MORPHOLOGY_CONTRIBUTION_LIMITED
ADA_RCA_METHOD_RETAIN_WITH_REFRAMED_CLAIM
```

This report is the final attribution closure for Ada-RCA V1. It is bounded to
the frozen RE2-OB and RE2-TT protocol, the committed three-fold OOF splits,
and the four-cell representation/scorer matrix. It does not constitute an
Ada-RCA V2 design or a new benchmark sweep.

## Executive answer

With the XGBRanker held fixed, replacing Z1 by frozen Z2 produced only a small
RE2-OB point increase in Avg@5 (`+0.004444`) and a RE2-TT point decrease
(`-0.011111`). The corresponding 95% paired bootstrap intervals crossed zero
on both datasets. The primary contrast therefore does not support a robust
additional Z2 morphology contribution under this nonlinear scorer.

With Z2 held fixed, Z2-XGB was essentially tied with Ada-RCA V1 on RE2-OB,
while on RE2-TT it improved the point estimates for Avg@5, AC@1, and MRR.
The RE2-TT AC@1 and MRR intervals excluded zero; the Avg@5 interval narrowly
crossed zero. This is evidence that the frozen Conditional Logit scorer is a
real limitation on TT, especially for top-1 and reciprocal-rank behavior, but
it is not evidence that Ada-RCA is invalid or that XGB is universally better.

The scientific conclusion is consequently scorer-dependent attribution:
Z2 gives a sizeable descriptive gain over Z1 under the linear scorer, but that
gain attenuates to near zero on OB and reverses on TT under the stronger XGB
scorer. The defensible Ada-RCA claim is compact, interpretable,
lightweight, and linear-friendly—not universal morphology-driven performance
superiority.

## A. Research question

The preceding supervised-baseline track showed that Z1-XGB was approximately
competitive with Ada-RCA V1 on RE2-OB and higher on RE2-TT Avg@5. That result
could not distinguish three explanations:

1. Z2 compact morphology contains information unavailable to Z1;
2. Z1 already contains most of the RCA information and Ada-RCA's Conditional
   Logit is the limiting scorer; or
3. the result is an interaction between representation and scorer.

The frozen questions were:

- **RQ1:** Does Z2 provide incremental RCA information when the scorer is the
  same XGBRanker used for Z1-XGB?
- **RQ2:** With Z2 fixed, is the nonlinear XGBRanker stronger than the frozen
  Ada-RCA Conditional Logit scorer?
- **RQ3:** Is the observed difference primarily representation, scorer, or
  representation/scorer interaction?

## B. Protocol and provenance

### Repository state

| Item | Value |
|---|---|
| Starting source | `evaluation/supervised-baselines@c15e054ecbff9a7a54f26cb24c2e804c269da641` |
| Worktree | `/home/zhangll24/RCA_project/Ada-RCA-z2-xgb-closure` |
| Branch | `evaluation/z2-xgb-closure` |
| Closure protocol freeze | commit `8f0a507` |
| Frozen Z2 identity audit | commit `318128f` |
| Formal Z2-XGB OOF artifacts | commit `57b9443` |
| Diagnostics, replay, validation | commit `2b9d7cc` |
| Pinned environment | `/home/zhangll24/.venvs/ada-rca-supervised-baselines/bin/python` |
| Python / XGBoost | `3.8.20` / `2.1.4` |
| Hash seed | `PYTHONHASHSEED=20260826` |

The protocol was committed before any formal Z2-XGB result existed. The
source worktree `evaluation/supervised-baselines` was not modified by this
closure.

### Controlled-variable design

The only experimental change from Z1-XGB was:

```text
input representation: Z1 32D -> frozen Z2 68D
```

The scorer was semantically identical to Z1-XGB:

```text
xgboost.XGBRanker
objective       = rank:pairwise
n_estimators    = 200
max_depth       = 3
learning_rate   = 0.05
subsample       = 1.0
colsample_bytree= 1.0
reg_lambda      = 1.0
random_state    = 20260826
n_jobs          = 1
tree_method     = hist
```

There was no scaler, feature selection, class weighting, early stopping,
validation selection, tuning, alternate objective, ensemble, or TT/OB
override.

### Frozen input and OOF protocol

The Z2 input was read directly from the committed Ada-RCA feature archives:

```text
Z1 block: base candidate x 4 x 8 = 32D
Z2 block: z2   candidate x 4 x 9 = 36D
Z2: concatenate((base, z2), axis=2).reshape(candidate_count, 68)
```

The feature-order digest was
`0acf244e629a5e62e3cca82f33f01cd25157ffaf2843f985b46755b615637dfa`.
The archive identity audit passed all 180 archives, with 90 cases per
dataset, 11 candidates per RE2-OB case, and 68 candidates per RE2-TT case.
The representation checksums were:

| Dataset | Representation checksum |
|---|---:|
| RE2-OB | `d4bce7fcec056519bea8525595d3cc09ca8d4e3872e3d905f0fbf65a99b2b364` |
| RE2-TT | `270fd8acb1059f66e8d8a1f5b6881e9822f0a3e8f37951466eb42dddbe251de9` |

Both datasets used the same frozen three-fold OOF assignment as Ada-RCA,
Z1-XGB, and Trajectory-CNN: 60 training cases and 30 test cases per fold.
Training used Z2 and one root label per training event. Test prediction was
label-free; test roots and fault types were joined only after the complete
candidate score vector and permutation had been emitted.

The primary contrast was `Z2-XGB - Z1-XGB`, with Avg@5 primary and AC@1/MRR
secondary. The scorer contrast was `Z2-XGB - Ada-RCA V1`. Both used 10,000
fault-stratified paired bootstrap resamples with seed `20260826`, pairing by
case ID.

The Z1-CL cell was not refit. It was read from the historical authoritative
artifact at:

```text
d36ad67:artifacts/p4_g0/predictions/a0/re2ob/
d36ad67:artifacts/p4_g0/predictions/a0/re2tt/
```

The Z2-CL cell is the unchanged Ada-RCA V1 final-method artifact.

## C. 2x2 results

### RE2-OB

| Method | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| Z1 + Conditional Logit | 0.855556 | 0.988889 | 1.000000 | 0.951111 | 0.913333 |
| Z2 + Conditional Logit (Ada-RCA V1) | 0.877778 | 0.988889 | 0.988889 | 0.962222 | 0.931481 |
| Z1 + XGBRanker | 0.888889 | 0.977778 | 0.988889 | 0.957778 | 0.933439 |
| Z2 + XGBRanker | 0.888889 | 0.988889 | 0.988889 | 0.962222 | 0.935185 |

Trajectory-CNN, retained only as a requested diagnostic comparator, was
`AC@1=0.822222`, `AC@3=0.977778`, `AC@5=0.988889`, `Avg@5=0.942222`, and
`MRR=0.897222`.

### RE2-TT

| Method | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| Z1 + Conditional Logit | 0.577778 | 0.800000 | 0.866667 | 0.764444 | 0.708019 |
| Z2 + Conditional Logit (Ada-RCA V1) | 0.711111 | 0.866667 | 0.933333 | 0.851111 | 0.803472 |
| Z1 + XGBRanker | 0.811111 | 0.922222 | 0.933333 | 0.900000 | 0.871645 |
| Z2 + XGBRanker | 0.822222 | 0.911111 | 0.922222 | 0.888889 | 0.868969 |

Trajectory-CNN was `AC@1=0.766667`, `AC@3=0.900000`, `AC@5=0.966667`,
`Avg@5=0.886667`, and `MRR=0.846402`.

### Z2-XGB fault-level metrics

These are descriptive strata of the new formal Z2-XGB artifact; no stratum was
used for selection or rescue.

| Dataset | Fault | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---|---:|---:|---:|---:|---:|
| OB | CPU | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| OB | MEM | 0.866667 | 1.000000 | 1.000000 | 0.973333 | 0.933333 |
| OB | DISK | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| OB | SOCKET | 0.866667 | 1.000000 | 1.000000 | 0.973333 | 0.933333 |
| OB | DELAY | 0.800000 | 1.000000 | 1.000000 | 0.933333 | 0.877778 |
| OB | LOSS | 0.800000 | 0.933333 | 0.933333 | 0.893333 | 0.866667 |
| TT | CPU | 0.866667 | 1.000000 | 1.000000 | 0.960000 | 0.922222 |
| TT | MEM | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| TT | DISK | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 1.000000 |
| TT | SOCKET | 0.866667 | 1.000000 | 1.000000 | 0.960000 | 0.922222 |
| TT | DELAY | 0.666667 | 0.733333 | 0.800000 | 0.746667 | 0.727255 |
| TT | LOSS | 0.533333 | 0.733333 | 0.733333 | 0.666667 | 0.642116 |

## D. Paired statistics

All intervals below are percentile 95% intervals from the prespecified
10,000-resample fault-stratified paired bootstrap. Positive values favor the
left-hand method.

| Dataset | Contrast | Delta Avg@5 [95% CI] | Delta AC@1 [95% CI] | Delta MRR [95% CI] |
|---|---|---:|---:|---:|
| OB | Z2-XGB - Z1-XGB | +0.004444 [-0.013333, +0.026667] | 0.000000 [-0.055556, +0.055556] | +0.001746 [-0.027884, +0.032593] |
| TT | Z2-XGB - Z1-XGB | -0.011111 [-0.046667, +0.020000] | +0.011111 [-0.055556, +0.077778] | -0.002676 [-0.040605, +0.034524] |
| OB | Z2-XGB - Ada-RCA | 0.000000 [-0.024444, +0.026667] | +0.011111 [-0.022222, +0.044444] | +0.003704 [-0.018519, +0.025926] |
| TT | Z2-XGB - Ada-RCA | +0.037778 [-0.002222, +0.077778] | +0.111111 [+0.033333, +0.188889] | +0.065497 [+0.014317, +0.118245] |
| OB | Z1-XGB - Ada-RCA | -0.004444 [-0.033333, +0.022222] | +0.011111 [-0.044444, +0.066667] | +0.001958 [-0.031534, +0.035185] |
| TT | Z1-XGB - Ada-RCA | +0.048889 [+0.008889, +0.091111] | +0.100000 [+0.011111, +0.188889] | +0.068173 [+0.013729, +0.122977] |

The earlier Z1-XGB versus Ada-RCA paired contrast remains useful context: its
TT point deltas were Avg@5 `+0.048889`, AC@1 `+0.100000`, and MRR `+0.068173`,
with intervals `[+0.008889,+0.091111]`, `[+0.011111,+0.188889]`, and
`[+0.013729,+0.122977]`, respectively. The new Z2-XGB comparison shows that
the TT advantage over Ada-RCA is not explained by a large additional Z2
increment under XGB; it is primarily a scorer contrast at fixed Z2.

## E. Case-level root-rank transitions

For every comparison, `improved` means the new method placed the root at a
smaller rank, `unchanged` means equal rank, and `degraded` means a larger
rank. Pairing was by exact case ID.

### Overall transitions

| Dataset | Comparison | Improved | Unchanged | Degraded |
|---|---|---:|---:|---:|
| OB | Z1-XGB vs Ada-RCA | 5 | 80 | 5 |
| OB | Z2-XGB vs Z1-XGB | 5 | 81 | 4 |
| OB | Z2-XGB vs Ada-RCA | 3 | 84 | 3 |
| OB | Trajectory-CNN vs Ada-RCA | 5 | 75 | 10 |
| TT | Z1-XGB vs Ada-RCA | 20 | 59 | 11 |
| TT | Z2-XGB vs Z1-XGB | 9 | 71 | 10 |
| TT | Z2-XGB vs Ada-RCA | 16 | 65 | 9 |
| TT | Trajectory-CNN vs Ada-RCA | 19 | 60 | 11 |

### Primary morphology transition by all fault types

The following table is the full fault-type summary for `Z2-XGB vs Z1-XGB`.
Entries are `improved / unchanged / degraded`.

| Dataset | CPU | MEM | DISK | SOCKET | DELAY | LOSS |
|---|---:|---:|---:|---:|---:|---:|
| OB | 1/14/0 | 0/15/0 | 0/15/0 | 2/12/1 | 0/13/2 | 2/12/1 |
| TT | 1/12/2 | 0/15/0 | 0/15/0 | 0/13/2 | 2/10/3 | 6/6/3 |

### RE2-TT focus: MEM, DELAY, LOSS

| Comparison | MEM | DELAY | LOSS |
|---|---:|---:|---:|
| Z1-XGB vs Ada-RCA | 2/13/0 | 6/5/4 | 7/3/5 |
| Z2-XGB vs Z1-XGB | 0/15/0 | 2/10/3 | 6/6/3 |
| Z2-XGB vs Ada-RCA | 2/13/0 | 4/9/2 | 6/5/4 |

The TT result is not a uniform morphology shift. MEM is unchanged for all 15
cases under Z2-XGB versus Z1-XGB. LOSS has a modest net improvement (6 versus
3), while DELAY has more degradations than improvements (3 versus 2). The
larger Z2-XGB versus Ada-RCA transition advantage on TT therefore mainly
reflects scorer changes at fixed Z2, not a broad rank improvement caused by
adding morphology to XGB.

### Fold and root-service breakdown for the primary contrast

Entries are again `improved / unchanged / degraded` for `Z2-XGB vs Z1-XGB`.

| Dataset | Fold 0 | Fold 1 | Fold 2 |
|---|---:|---:|---:|
| OB | 3/25/2 | 1/28/1 | 1/28/1 |
| TT | 1/26/3 | 4/21/5 | 4/24/2 |

| Dataset | Root service | Transition count |
|---|---|---:|
| OB | checkoutservice | 1/14/3 |
| OB | currencyservice | 3/15/0 |
| OB | emailservice | 0/18/0 |
| OB | productcatalogservice | 0/18/0 |
| OB | recommendationservice | 1/16/1 |
| TT | ts-auth-service | 2/12/4 |
| TT | ts-order-service | 0/16/2 |
| TT | ts-route-service | 3/15/0 |
| TT | ts-train-service | 1/17/0 |
| TT | ts-travel-service | 3/11/4 |

The complete `fault_type` × `root_service` × `fold` tables for all three
required comparisons, including Trajectory-CNN, are retained in
`artifacts/z2_xgb_closure/diagnostics/rank_transitions.json`; the individual
case rows are in `rank_transition_cases.jsonl`.

## F. Scientific attribution

The descriptive representation gains were calculated as:

```text
Delta_morph_linear = Z2-CL  - Z1-CL
Delta_morph_xgb    = Z2-XGB - Z1-XGB
interaction        = Delta_morph_xgb - Delta_morph_linear
```

| Dataset | Metric | Morphology gain under CL | Morphology gain under XGB | Interaction |
|---|---|---:|---:|---:|
| OB | Avg@5 | +0.011111 | +0.004444 | -0.006667 |
| OB | AC@1 | +0.022222 | 0.000000 | -0.022222 |
| OB | MRR | +0.018148 | +0.001746 | -0.016402 |
| TT | Avg@5 | +0.086667 | -0.011111 | -0.097778 |
| TT | AC@1 | +0.133333 | +0.011111 | -0.122222 |
| TT | MRR | +0.095452 | -0.002676 | -0.098128 |

These are controlled descriptive decompositions, not a causal estimate of an
isolated latent morphology mechanism.

### Answer to RQ1

**Z2 morphology does not show a robust nonlinear-scorer increment in this
closure.** The point estimate is slightly positive on OB and negative on TT
for Avg@5; AC@1 is zero on OB and only +0.011111 on TT; all primary Z2-XGB
versus Z1-XGB intervals cross zero. The result is therefore not Case A from
the frozen interpretation matrix. It is closest to Case B, with a dataset
dependent trade-off consistent with a limited morphology-performance claim.

### Answer to RQ2

**The frozen Conditional Logit appears to be a limiting scorer on TT.** At the
same Z2 representation, XGB improves TT AC@1 and MRR with paired intervals
above zero and improves TT Avg@5 pointwise, although the Avg@5 interval
narrowly crosses zero. On OB the two Z2 scorers are effectively tied. This
supports a bounded scorer-limitation interpretation, not a universal XGB
superiority claim.

### Answer to RQ3

**The evidence favors scorer contribution and a negative representation/scorer
interaction over a standalone morphology contribution.** The linear-scoring
morphology gains are positive on TT, but the corresponding XGB gains are near
zero or negative. The negative interaction is largest on TT (`-0.097778` for
Avg@5, `-0.122222` for AC@1, and `-0.098128` for MRR). Thus Ada-RCA's Z2 is
useful in the specific sense that it makes the frozen linear scorer effective;
this closure does not establish that Z2 is intrinsically superior when a
stronger scorer can learn interactions directly from Z1.

## G. Service-fingerprint risk synthesis

No new leave-one-root experiment was added, as required by the frozen
protocol. The existing control/audit evidence was consulted as a limitation:

- The committed S2 audit is an exact pre-event-only 16D representation. It
  remains below the final method under its own frozen control rule, but it
  carries meaningful RCA information, especially on RE2-OB.
- The committed S3 service-identity probe reports stable service fingerprints:
  OB top-1 `0.598990` and macro-F1 `0.583065`; TT top-1 `0.132190` and
  macro-F1 `0.113494`.
- The S3 result is diagnostic evidence of stable service identity signal, not
  evidence of root-label leakage. It nevertheless limits a morphology-only
  attribution because an XGB scorer can exploit stable service-related feature
  interactions.

The S2/S3 evidence source was read-only Ada-RCA evidence at commit
`6c3abaaf34391db8a6e78743a3a3580440fe956d`, principally
`docs/FINAL_EVIDENCE_SUMMARY.md`, `docs/FINAL_METHOD_DECISION.md`,
`docs/FINAL_RCA_CONTROL_AUDIT.md`, and
`artifacts/final_audit/s3_service_identity/`. This closure does not merge the
historical S2 protocol or its separately documented bootstrap seed into the
current Z2-XGB statistics.

## H. Scientific disposition

### `MORPHOLOGY_CONTRIBUTION_LIMITED`

The nonlinear controlled contrast does not support a reliable Z2 increment:
OB is small and uncertain, while TT is negative for Avg@5 and MRR at the point
estimate. The positive Z2-over-Z1 linear contrast is real as an observed
descriptive difference in this matrix, but it is scorer-dependent and cannot
be promoted to a general morphology-performance claim.

### `ADA_RCA_METHOD_RETAIN_WITH_REFRAMED_CLAIM`

Ada-RCA V1 remains a complete, reproducible, compact, interpretable,
lightweight method. Its Z2 + Conditional Logit cell is competitive on OB and
has a meaningful TT gain over Z1 + Conditional Logit, while the closure
identifies the scorer as a likely TT bottleneck. Nothing in this closure
supports `ADA_RCA_METHOD_INVALID`.

## I. Thesis claim recommendation

### Allowed claim

> Ada-RCA V1 introduces a frozen 68-dimensional compact event-relative
> representation that packages service-level morphology for an interpretable
> Conditional Logit root scorer. Under the specified three-fold known-root,
> new-repetition RE2-OB/RE2-TT protocol, the method is complete and
> benchmark-competitive. A controlled scorer comparison shows that its
> observed advantage over the Z1 baseline is substantially scorer-dependent:
> the Z2 gain is visible with the lightweight linear scorer but is not a
> robust additional gain when the same input is scored by the fixed XGBRanker.

This wording preserves the actual innovation: compact representation design,
interpretability, low scorer complexity, and a complete auditable pipeline.
It explicitly limits performance attribution to this corpus and protocol and
acknowledges service-fingerprint and robustness limitations.

### Forbidden or too strong

The following claims are not supported by this closure:

- “Z2 morphology is universally superior to Z1.”
- “Z2 independently causes the RCA improvement under any scorer.”
- “Ada-RCA is SOTA” or “Ada-RCA is the best method.”
- “Ada-RCA's Conditional Logit is optimal.”
- “XGB proves nonlinear learning is unnecessary.”
- “The service-fingerprint risk is absent.”
- “The S2/S3 controls prove leakage,” or, conversely, “the controls prove
  morphology is the sole mechanism.”
- “Ada-RCA is invalid” solely because Z1-XGB or Z2-XGB has a higher TT point
  estimate.

## J. Artifacts and validation

Formal artifacts are under:

```text
artifacts/z2_xgb_closure/
  representation_identity.json
  validation.json
  z2_xgb/re2ob/{fold_0,fold_1,fold_2,aggregate}/
  z2_xgb/re2tt/{fold_0,fold_1,fold_2,aggregate}/
  replay_check/z2_xgb/re2ob/fold_0/
  diagnostics/{closure_summary.json,paired_statistics.json,
               rank_transitions.json,rank_transition_cases.jsonl,
               attribution.json,checksums.json}
```

The artifact validator reports `PASS` for all six folds, both aggregates,
all fold checksums, dimensions, candidate permutations, root uniqueness,
label-firewall conditions, and the independent deterministic replay. The
replay matched the formal fold exactly for configuration, environment,
integrity, metrics, model bytes, and predictions; only timestamps/runtime and
source provenance are expected to differ.

The relevant test command passed `24/24` tests:

```text
tests.test_z2_xgb_closure
tests.test_supervised_xgb
tests.test_supervised_protocol
tests.test_supervised_firewall
tests.test_supervised_evaluator
tests.test_features
```

## K. Full reproduction commands

The following commands assume a fresh worktree with the create-once closure
output paths empty. They use the pinned environment and preserve the formal
namespace guard.

```bash
cd /home/zhangll24/RCA_project
git worktree add ../Ada-RCA-z2-xgb-closure \
  -b evaluation/z2-xgb-closure \
  evaluation/supervised-baselines
cd /home/zhangll24/RCA_project/Ada-RCA-z2-xgb-closure

PY=/home/zhangll24/.venvs/ada-rca-supervised-baselines/bin/python
export PYTHONHASHSEED=20260826
export PYTHONDONTWRITEBYTECODE=1

git status --short --branch
git diff --check

$PY scripts/z2_xgb_closure/audit_frozen_z2.py \
  --output artifacts/z2_xgb_closure/representation_identity.json

$PY scripts/supervised_baselines/run_z2_xgb_ranker.py \
  --dataset re2ob --fold 0 --output-root artifacts/z2_xgb_closure
$PY scripts/supervised_baselines/run_z2_xgb_ranker.py \
  --dataset re2ob --fold 1 --output-root artifacts/z2_xgb_closure
$PY scripts/supervised_baselines/run_z2_xgb_ranker.py \
  --dataset re2ob --fold 2 --output-root artifacts/z2_xgb_closure
$PY scripts/supervised_baselines/run_z2_xgb_ranker.py \
  --dataset re2tt --fold 0 --output-root artifacts/z2_xgb_closure
$PY scripts/supervised_baselines/run_z2_xgb_ranker.py \
  --dataset re2tt --fold 1 --output-root artifacts/z2_xgb_closure
$PY scripts/supervised_baselines/run_z2_xgb_ranker.py \
  --dataset re2tt --fold 2 --output-root artifacts/z2_xgb_closure

$PY scripts/supervised_baselines/aggregate_results.py \
  --method z2_xgb --dataset re2ob \
  --output-root artifacts/z2_xgb_closure
$PY scripts/supervised_baselines/aggregate_results.py \
  --method z2_xgb --dataset re2tt \
  --output-root artifacts/z2_xgb_closure

$PY scripts/z2_xgb_closure/analyze_closure.py
$PY scripts/z2_xgb_closure/validate_closure.py

$PY -m unittest \
  tests.test_z2_xgb_closure \
  tests.test_supervised_xgb \
  tests.test_supervised_protocol \
  tests.test_supervised_firewall \
  tests.test_supervised_evaluator \
  tests.test_features

git diff --check
git status --short --branch
```

The formal Z2-XGB fold runner, aggregate runner, and diagnostic scripts are
create-once. A rerun must use a freshly audited worktree/output namespace; it
must not overwrite the committed formal artifacts.

## L. Closure commits

The closure history is intentionally incremental:

```text
8f0a507  docs: freeze z2 xgb closure protocol
6f2d503  feat: add frozen z2 xgb comparator
29b9165  test: add z2 xgb protocol checks
318128f  exp: record frozen z2 identity audit
9c60e04  feat: add z2 xgb closure aggregation
a660321  feat: add paired rank transition diagnostics
1fe44b1  fix: allow isolated z2 closure replay outputs
57b9443  exp: add z2 xgb oof artifacts
2b9d7cc  exp: add z2 xgb closure diagnostics
```

The commit containing this report is the final documentation commit for the
closure. No Ada-RCA V1 source, Z1-XGB artifact, Z1-CL artifact, or inherited
TCN artifact was modified.
