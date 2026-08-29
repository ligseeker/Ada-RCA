# P6-E5 Baseline Failure Policy

Date: 2026-08-29  
Status: frozen pre-performance policy; this document does not authorize P6-E5

This policy governs any future formal external-baseline reproduction. It is
separate from the P6-E4R integration smoke and must be applied before any
performance result exists.

## F-A — Algorithmic Failure

The legal input reached the unchanged official baseline, but the method failed
or produced no legal ranking. Retain the case in the 90-case denominator,
record F-A explicitly, assign strict all-case robustness utility 0 for that
case, include that zero utility in future AC@1, AC@3, and Avg@5 all-case
computation, and report the F-A failure rate separately. Never fabricate a
ranking.

## F-B — Officially Unsupported Input

Use F-B only when upstream explicitly establishes unsupported input. For an
applicable baseline, retain the case in the strict robustness denominator,
assign utility 0, and report the unsupported rate separately. A crash alone is
not evidence of F-B.

## F-C — Environment or Dependency

F-C is not a localization error. First attempt a legitimate reproducible
environment reconstruction using repository requirements, original method
specification, or documented compatible versions. If reconstruction remains
impossible, mark the case `NR / NOT RUN`; do not assign RCA utility zero.

## F-D — Ada-RCA Adapter or Integration Failure

F-D means the adapter or integration is invalid. Repair the adapter and rerun;
never score the run as a baseline failure.

## F-E — Data Integrity

Stop the affected comparison and preserve the integrity failure explicitly.
Never convert it into a performance result.

## Reporting Views

The primary external-baseline result is the **STRICT ALL-CASE ROBUSTNESS VIEW**
using all 90 cases per dataset. The failure rate for each taxonomy is reported
beside performance. A **SUCCESSFUL-OUTPUT-SUBSET VIEW** may be shown only as a
clearly labeled secondary diagnostic and can never replace the all-case
headline.
