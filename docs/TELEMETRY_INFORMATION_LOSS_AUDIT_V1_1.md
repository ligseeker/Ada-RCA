# Telemetry Information-Loss Audit V1.1

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Verification Status: VERIFIED WITH RAW-LINEAGE LIMITATION
- Version Label: telemetry_information_loss_v1_1
- Primary statistical unit: candidate-case pair
- Machine-readable result:
  `artifacts/evidence_closure/telemetry_information_loss_v1_1.json`

## Gate result

`GATE_3_PASS — GATE_4_AUTHORIZED`

The candidate-case feature pathway is auditable from hash-bound canonical
derived telemetry inputs and committed frozen feature artifacts. The audit does
not fit a model, calculate a prediction metric, create a new feature, run sparse
optimization, or admit a previously rejected feature family.

## Candidate-case information funnel

Every number below counts candidate-case pairs. Raw metric rows, log records,
and trace spans are not mixed into this table.

| Dataset | Modality | Eligible | Mapped | Window observed | Pre observed | Post observed | Scale valid | Feature active |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RE2-OB | Metric | 990 | 990 | 990 | 990 | 990 | 990 | 990 |
| RE2-OB | Log | 990 | 812 | 812 | 812 | 812 | 807 | 807 |
| RE2-OB | Trace Error | 990 | 900 | 900 | 900 | 900 | 0 | 0 |
| RE2-OB | Trace Latency | 990 | 900 | 900 | 900 | 900 | 374 | 374 |
| RE2-TT | Metric | 6,120 | 6,120 | 6,120 | 6,120 | 6,120 | 6,120 | 6,120 |
| RE2-TT | Log | 6,120 | 1,787 | 1,787 | 1,767 | 1,767 | 1,707 | 1,707 |
| RE2-TT | Trace Error | 6,120 | 2,347 | 2,347 | 2,340 | 2,339 | 0 | 0 |
| RE2-TT | Trace Latency | 6,120 | 2,347 | 2,347 | 2,340 | 2,339 | 847 | 847 |

The funnel is monotonic for every dataset/modality. Every frozen active pair is
a subset of scale-valid pairs. Metric is fully active. Mapping is the dominant
loss for TT log/trace modalities; robust pre-event scaling is the terminal loss
for Trace Error and a material loss for Trace Latency.

## Trace Error zero-scale diagnostics

The definitions and counts remain at candidate-case level. `pre_all_zero` and
`pre_constant` require every pre-observed mapped indicator series in the pair to
meet the condition. `MAD_pre_zero` and `IQR_pre_zero` likewise require all
pre-observed mapped indicators to have a zero raw statistic.

| Diagnostic | RE2-OB count / 990 | RE2-TT count / 6,120 |
|---|---:|---:|
| pre_all_zero | 899 | 2,340 |
| pre_constant | 899 | 2,340 |
| post_positive | 31 | 0 |
| post_changed | 31 | 0 |
| MAD_pre_zero | 900 | 2,340 |
| IQR_pre_zero | 900 | 2,340 |
| rejected_by_scale | 900 | 2,340 |
| pre_all_zero AND post_positive | 30 | 0 |
| pre_all_zero AND post_positive AND rejected_by_scale | 30 | 0 |
| pre_constant AND post_changed | 30 | 0 |
| pre_constant AND post_changed AND rejected_by_scale | 30 | 0 |

For RE2-OB, 30 candidate-case pairs contain an observable post-event positive
Trace Error signal after an all-zero/constant pre-event baseline, but the
frozen robust-scale rule rejects every such pair because both pre MAD and pre
IQR are zero. This is a verified information-loss mechanism. It is not evidence
that a sparse feature would improve RCA, and this audit does not authorize one.

For RE2-TT, the pre-observed Trace Error pairs are all-zero/constant and no
post-positive or post-changed pair is present in the canonical derived input.

## Relationship to the legacy telemetry table

`docs/OPT_TELEMETRY_INFORMATION_LOSS_AUDIT.md` is retained unchanged as a
historical audit. Its service-row counts were taken from a different event
feature audit and are not a complete candidate-case funnel. In particular, its
Trace Error count of 630 for each dataset must not be interpreted as 630 frozen
Trace Error-active candidate-case pairs. The committed P3 feature artifacts
show zero Trace Error-active pairs in both datasets.

This correction does not change any frozen feature or prediction. It narrows
the active claim to what the actual feature artifacts support.

## Canonical artifact validation

For each dataset, all 360 consumed derived files (90 cases × four modalities)
match the size and SHA-256 recorded in the committed dataset manifest. Source
manifests and all frozen feature artifacts match the frozen optimization commit.
The audit consumes `simple_metrics.csv`, `logts.csv`, `tracets_err.csv`, and
`tracets_lat.csv`, exactly the four frozen representation inputs.

## Auditability boundary

Candidate-case funnel status:
`AUDITABLE_FROM_HASH_BOUND_CANONICAL_DERIVED_INPUTS_AND_FROZEN_FEATURE_ARTIFACTS`.

Raw-record lineage status:
`NOT_FULLY_AUDITABLE_FROM_AVAILABLE_CANONICAL_ARTIFACTS`.

Raw and derived files are hash-bound, but the repository does not commit a
per-record lineage mapping each raw log/span/metric row to a derived wide-series
cell and its rejection cause. Therefore raw-to-derived mapping failure, raw
record rejection, and raw aggregation loss are not guessed. This limitation is
separate from the fully audited derived-input-to-feature candidate-case funnel.
