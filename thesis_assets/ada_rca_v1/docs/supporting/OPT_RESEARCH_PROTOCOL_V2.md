# Ada-RCA Performance Optimization Protocol V2

Status: `PRE-OPTIMIZATION PROTOCOL`
Branch: `research/performance-optimization`
Starting scientific reference: V1 frozen base commit `bed295326e567395e725caa82840a534dcc0b1de`

## Positioning

This branch is an independent performance-optimization study. The frozen V1
method remains `V1-SCIENTIFIC`: 68D Z2 event-relative multimodal features with
event-level conditional-logit ranking. Historical high scores are descriptive
`HISTORICAL-REFERENCE` evidence only. The final optimization result is
`OPT-DEVELOPMENT-NESTED-OOF`; RE2-OB and RE2-TT have been reused during prior
development and therefore are not untouched external tests.

## Data and evaluation

Only RE2-OB and RE2-TT are used, each with 90 failure events, the canonical
legal candidate universe, root mapping, case registry, and frozen three-fold
outer assignments. Ranking is complete, duplicate-free, deterministic, and
event-grouped. Predictive inputs exclude root labels, fault type, and explicit
service/root identity. All preprocessing and selection are train-only.

Metrics are AC@1, AC@3, AC@5, Avg@5, and MRR, with fault and root macro
diagnostics. Avg@5 is primary; AC@1 and MRR are secondary. Configurations within
`1/90` Avg@5 are practically equivalent and are ordered by AC@1, then MRR,
then lower complexity. Candidate rows are not independent observations; the
effective sample size for model selection is approximately 90 events per
dataset.

## Historical and telemetry gates

Historical candidates are inspected and replayed without changing V1. They are
classified as canonically replayable, concept-reusable but protocol-incompatible,
or incomparable/leakage-risk. The telemetry audit reports the raw-to-active
information funnel separately for Metric, Log, Trace Error, and Trace Latency,
without labels in the inclusion decision. If sparse-event semantics are
confirmed, one predeclared sparse family is eligible; otherwise no sparse
features are added.

## Frozen optimization search

Before the first optimization outer OOF, `OPT_SEARCH_SPACE_FREEZE_V1.md` is
committed. At most eight representation candidates, three ranker families, and
the exact small grids in that document are allowed. Inner deterministic 3-fold
CV is used, with a predeclared 2-fold fallback when stratification is
impossible. Representations are reduced to `TOP_K_REPRESENTATIONS <= 3` before
ranker/grid comparison. Only the predeclared conditional-logit plus tree-family
score fusion with fixed alpha candidates may be selected in inner CV.

After freeze, no new feature family, modality subset, model family,
hyperparameter, ensemble, topology, hard-negative scheme, objective, tie-break,
or rescue is permitted. An implementation defect requires a documented invalid
run and complete rerun; a scientific expansion is `STOPPED FOR HUMAN REVIEW`.

## One-shot nested OOF

Each dataset is trained independently under the frozen outer folds. All
representation, ranker, hyperparameter, and ensemble decisions are made only
inside each outer-train split. Both `PER-DATASET-OPT` and a shared-family
`GLOBAL-OPT` are reported. Outer-test events are used only once for final OOF
metrics and diagnostics. Selection and outer-test event IDs must be disjoint.

## Uncertainty and interpretation

Final V1-versus-optimization contrasts use paired fault-stratified bootstrap,
10,000 iterations, seed `20260829`. Intervals describe case-sampling
uncertainty conditional on fixed predictions; they exclude search-space,
historical-reuse, researcher-degree-of-freedom, and benchmark meta-overfitting
uncertainty. Conclusions are separated into FACT, INFERENCE, and NOT SUPPORTED.
The run stops after final diagnostics with `OPTIMIZED_MODEL_FOUND`,
`NO_CLEAR_OPTIMIZATION_GAIN`, or `OPTIMIZATION_INVALID`.
