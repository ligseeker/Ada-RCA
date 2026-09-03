# Frozen Trace Error Representation Invariant

Status: **READ-ONLY FROZEN FEATURE AUDIT**

Machine-readable artifact:
`artifacts/evidence_closure/trace_error_representation_invariant.json`

## Audit boundary

This audit reads all 180 committed files under
`artifacts/features/{re2ob,re2tt}/*.npz`. It performs no model fit, score
calculation, prediction regeneration, feature regeneration, or representation
search. Every inspected feature file is byte-identical to its blob at the
frozen optimization commit `53c9face2c96761c9114edb558eb6d8666a38dc6`.

The primary proof is the frozen feature matrix itself. Optimization traces are
not used to infer the representation invariant.

## Frozen Trace Error block

Z2 contains four channels in this exact order: Metric, Log, Trace Error, and
Trace Latency. Each channel contains eight base fields followed by nine
morphology fields. Trace Error therefore occupies frozen Z2 indices 34 through
50, inclusive, and has exactly 17 dimensions.

## Dataset-level invariants

| Dataset | Cases | Candidate-case rows | All-zero 17D rows | Nonzero 17D rows | Unique TE vectors | Nonzero-variance dimensions | Cases with within-case candidate variation |
|---|---:|---:|---:|---:|---:|---:|---:|
| RE2-OB | 90 | 990 | 0 | 990 | 1 | 0 | 0 / 90 (0.0%) |
| RE2-TT | 90 | 6,120 | 0 | 6,120 | 1 | 0 | 0 / 90 (0.0%) |

The block is not all zero. In both datasets every candidate-case row is exactly:

```text
[0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

The single nonzero element is `base.onset_missing = 1`. Thus globally nonzero
does not mean candidate-discriminative.

## Per-dimension statistics

The following table applies identically to RE2-OB and RE2-TT.

| Frozen Z2 index | Trace Error field | Min | Max | Variance | Unique count | Varies within any case |
|---:|---|---:|---:|---:|---:|---|
| 34 | `base.magnitude` | 0 | 0 | 0 | 1 | No |
| 35 | `base.mean_impact` | 0 | 0 | 0 | 1 | No |
| 36 | `base.pre_post_shift` | 0 | 0 | 0 | 1 | No |
| 37 | `base.onset_seconds` | 0 | 0 | 0 | 1 | No |
| 38 | `base.onset_missing` | 1 | 1 | 0 | 1 | No |
| 39 | `base.persistence` | 0 | 0 | 0 | 1 | No |
| 40 | `base.coverage` | 0 | 0 | 0 | 1 | No |
| 41 | `base.channel_available` | 0 | 0 | 0 | 1 | No |
| 42 | `morphology.normalized_pre_mean` | 0 | 0 | 0 | 1 | No |
| 43 | `morphology.normalized_post_mean` | 0 | 0 | 0 | 1 | No |
| 44 | `morphology.normalized_post_minus_pre_mean` | 0 | 0 | 0 | 1 | No |
| 45 | `morphology.post_peak_time_fraction` | 0 | 0 | 0 | 1 | No |
| 46 | `morphology.post_amplitude_weighted_centroid_fraction` | 0 | 0 | 0 | 1 | No |
| 47 | `morphology.post_ols_slope` | 0 | 0 | 0 | 1 | No |
| 48 | `morphology.post_mean_absolute_adjacent_difference` | 0 | 0 | 0 | 1 | No |
| 49 | `morphology.post_fraction_z_ge_0_5` | 0 | 0 | 0 | 1 | No |
| 50 | `morphology.morphology_active` | 0 | 0 | 0 | 1 | No |

## Global, across-case, and within-case distinctions

- Globally nonzero: **yes**, solely because `base.onset_missing = 1`.
- Across-case variation: **none**. There is one case-mean TE vector in each
  dataset, identical to the vector above.
- Within-case candidate-discriminative variation: **none**. Every candidate in
  every case receives the same TE block.

These are separate properties. The first does not imply either of the latter
two.

## Removal invariant

Removing Trace Error changes every raw 68D candidate vector because it removes
the constant `onset_missing = 1` coordinate. However, it removes exactly the
same 17D block from every candidate in every case. Consequently, for any fixed
linear coefficient vector, the TE contribution to every pairwise candidate
utility difference is exactly zero. The frozen block cannot change a
within-event Conditional Logit ranking.

This is a representation statement, not a newly scored ablation. No model was
run to reach it.

## Exact field relationship

For all 990 RE2-OB rows and all 6,120 RE2-TT rows:

- `base.coverage = 0`;
- `base.channel_available = 0`;
- `morphology_active = 0`;
- the other eight morphology fields are all zero;
- `base.onset_missing = 1`; and
- the other seven base fields are all zero.

This follows the frozen implementation path. When no Trace Error indicator
survives robust pre-event scaling, `q` remains unobserved and `q_mask` is false.
The base calculation therefore records zero coverage and takes the unavailable-
channel branch, which emits `onset_missing = 1` and returns before any active
morphology can be constructed.

The Gate 3 mapping counts are not contradicted: raw/derived Trace Error can map
to a service, while failure of every indicator's pre-event robust scale still
leaves no observed normalized `q` value in the frozen feature representation.

## Frozen optimization-trace cross-check

Only after establishing the matrix invariant, the frozen inner-selection
traces were inspected as secondary evidence. All available exact comparisons
agree with the feature-matrix result:

| Representation pair | Exact representation-screen comparisons | Exact shared ranker/lambda comparisons | Interpretation |
|---|---:|---:|---|
| M+TE vs Z1-M | 6 / 6 | 6 / 6 | `CONSISTENT_WITH_TE_NONDISCRIMINATIVE` |
| FULL-Z2 vs M+L+TL | 6 / 6 | 12 / 12 | `CONSISTENT_WITH_TE_NONDISCRIMINATIVE` |

The six screen comparisons cover three outer folds in each dataset. Ranker-grid
counts include only configurations for which both representations are present
at the same ranker and lambda. Every compared `fold_scores`, `mean_Avg@5`, and,
where recorded, `AC@1_mean` value is exactly identical. The final copied
selection traces are also byte-identical to their corresponding O4 traces.

These trace equivalences are consistent with the TE block being
non-discriminative, but they are not the primary proof and are not a new
ablation run.

## Scientific classification

For both datasets and overall:

`TRACE_ERROR_EFFECTIVELY_NONDISCRIMINATIVE_IN_FROZEN_Z2`

Ada-RCA accepts Trace Error telemetry as an input modality, but the frozen
robust-scale representation suppresses its candidate-discriminative
contribution on RE2-OB and RE2-TT. This does not show that a sparse-aware
replacement would improve RCA and does not authorize a new representation.
