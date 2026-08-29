# Telemetry Information-Loss Audit

The audit is label-free. Root and fault labels are used only for optional
post-hoc stratification and never determine feature admission.

## Information funnel

Counts are service-row counts from the audited feature bundles; `N_raw` is the
raw-row count when the extractor recorded it. A missing raw count is reported as
`NR` rather than inferred from labels.

| Dataset | Channel | N_raw | N_mapped | N_in_window | N_with_pre_obs | N_with_post_obs | N_scale_valid | N_active |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RE2-OB | Metric | NR | 990 | 990 | 988 | 988 | 988 | 988 |
| RE2-OB | Log | 15,053,223 | 902 | 902 | 902 | 902 | 902 | 902 |
| RE2-OB | Trace Error | 34,461,235 | 630 | 630 | 630 | 630 | 630 | 630 |
| RE2-OB | Trace Latency | 34,461,235 | 630 | 630 | 630 | 630 | 630 | 630 |
| RE2-TT | Metric | NR | 990 | 990 | 988 | 988 | 988 | 988 |
| RE2-TT | Log | NR | 990 | 990 | 990 | 990 | 990 | 990 |
| RE2-TT | Trace Error | NR | 630 | 630 | 630 | 630 | 630 | 630 |
| RE2-TT | Trace Latency | NR | 630 | 630 | 630 | 630 | 630 | 630 |

The metric and event-bundle audit confirms finite values and zero-valued masks
for unavailable rows. Existing Z2 artifacts expose four channels (`metric`,
`log`, `trace-error`, `trace-latency`) and 90 cases per dataset.

## Rejection reasons

The dominant observed reasons are unavailable raw entities and incomplete
interval content. For RE2-OB log, 88/990 service rows have no observed entity;
the remaining 902 are mapped. Its minimum complete interval ratio is
`0.7949002217`, below the predeclared `0.80` staged-support threshold, while
relative-to-whole support is `1.0`. Thus `trace-error availability=0`-style rows
are caused by absent raw trace entities in the selected window, not by root or
fault labels. Zero pre MAD/IQR rows are represented by the current invalid-scale
path and are not silently converted into labels.

The available bundle does not preserve a per-row distinction for every raw
rejection reason (mapping failure vs no pre vs no post). Those cells remain
`NR` rather than being fabricated. A post-hoc sparse-event probe is therefore
descriptive only. No sparse family is admitted solely because discarded rows
are enriched at roots.

## Decision

Trace channels have root-independent usable whole-event support, but RE2-OB log
staged support fails the frozen absolute threshold. The optimization search may
use existing whole-event channels and the single predeclared sparse family;
staged log features are excluded.
