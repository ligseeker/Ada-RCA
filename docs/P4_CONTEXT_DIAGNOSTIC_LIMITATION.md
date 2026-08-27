# P4 Foreign-Context Diagnostic Limitation

Status: GOVERNANCE QUALIFICATION  
Date: 2026-08-27

The P4-G0 primary gate and its `NO-GO / CLOSED` decision are unchanged. This
document qualifies only the non-gating foreign-context diagnostic.

## Observed implementation

For normal within-event candidate-relative percentiles, the implementation uses
the preregistered mapping

`(rank - 1) / (N - 1)`

with feature-wise ascending average ranks.

For a foreign event context, the implementation uses the mid-distribution
mapping

`(# less + 0.5 * # equal) / N`.

The two mappings are therefore not the same percentile coordinate system. The
foreign intervention also changes the candidate-context distribution itself.

## Limitation and consequence

Normal-versus-foreign scores consequently conflate at least two changes:

1. the candidate context distribution used to compute relative values; and
2. the percentile denominator/mapping (`N-1` normal versus `N` foreign).

Therefore the foreign-context comparison cannot be interpreted as candidate-
context causal evidence or as clean mechanism evidence isolating context
dependence. It remains a descriptive, non-gating diagnostic only.

P4-G0 primary A0/A1/A2/A3 rankings, metrics, bootstrap, integrity tests, and
the `P4-G0 = NO-GO / CLOSED` decision do not depend on this diagnostic and are
not modified. The limitation must be carried into the final evidence summary
and any scientific claim boundary.

