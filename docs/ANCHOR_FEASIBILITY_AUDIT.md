# Anchor Robustness Feasibility Audit

Status: `ANCHOR_AUDIT_NOT_FEASIBLE_UNDER_FROZEN_PIPELINE`  
Generating audit commit: `9ececc0a9d974841243ddc8a09d5980fceb8d94e`  
Performance computed: **no**.

The audit checked all 180 cases, all four official derived sources
(`simple_metrics.csv`, `logts.csv`, `tracets_err.csv`, `tracets_lat.csv`), and
all offsets `-30, -15, 0, +15, +30` seconds. The retained full window requires
support over `[t0-630, t0+630)`.

Support uses the half-open derived-series interval
`[first_timestamp, last_timestamp + cadence)`, preserving the frozen 1-second
metric and 15-second log/trace cadence semantics. No padding, interpolation,
truncation, source switch, shorter window, case dropping, or feasible-subset
analysis is used.

## Result

There are 77 unsupported case-source-offset combinations, affecting five cases:

| Dataset | Unsupported combinations | Affected cases |
|---|---:|---:|
| RE2-OB | 49 | 3 |
| RE2-TT | 28 | 2 |
| Total | 77 | 5 |

All failures are timestamp-boundary support failures. No unexpected data source
was detected. RE2-OB's 514 malformed/blank timestamp rows remain explicit
missingness evidence and were not silently repaired.

Because at least one required offset is unsupported for at least one frozen
case/source, the protocol forbids shifted performance. The anchor performance
audit is skipped. Robustness evidence is therefore unavailable under the
current frozen data pipeline; this is not a method failure and does not
authorize any representation, preprocessing, event-window, source, or anchor
change.

The complete per-case/per-source/per-offset report is
`artifacts/final_audit/anchor_feasibility.json`.

