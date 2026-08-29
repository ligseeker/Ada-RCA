# Ada-RCA V2 Protocol Deviations

## V2-F0 fresh-fit score identity guard

Status: CORRECTED BEFORE F0 INTERPRETATION OR COMMIT  
Date: 2026-08-29

The first V2-F0 runner execution completed all 30 fixed dataset/variant fits,
then stopped at an extra implementation guard that required a newly fitted
`FULL-Z2` score vector to differ from the historical V1 persisted-state replay
by at most `1e-12`.

This score threshold was not a preregistered F0 gate. V2-G0 had already passed
the required persisted-state replay with zero score error, exact ranking
identity, exact metric recomputation, complete candidate/root coverage, exact
folds, valid checksums, and the full V1 test suite. F0 preregistered reuse of the
same scorer, scaling policy, folds, and complete ranking, but did not require a
new optimization run to reproduce historical serialized scores within the G0
persisted-state threshold.

The completed F0 `FULL-Z2` fits had identical scaler means and scales. Maximum
absolute weight differences from the historical V1 states were
`5.662137425588298e-15` on RE2-OB and `1.2212453270876722e-14` on RE2-TT.
All 180 rankings and all frozen metrics were identical. Maximum absolute score
differences were `1.2079226507921703e-13` on RE2-OB and
`1.2008172234345693e-12` on RE2-TT. The latter exceeded the extra guard by
`2.008172234345693e-13` despite no ranking or metric change.

The correction is limited to audit logic:

- F0 `FULL-Z2` now requires exact ranking identity and exact overall metric
  identity with V1;
- the maximum fresh-fit score difference remains recorded descriptively;
- no feature, variant, threshold, fold, scaler, optimizer, convergence rule,
  model, metric, bootstrap, or scientific gate changed;
- none of the 30 completed fits is rerun;
- the retained partial artifacts are checksum-verified, their complete
  rankings/root ranks/folds are revalidated, and only the missing descriptive
  summaries are resumed.

This correction cannot improve or change any F0 performance value and does not
authorize model selection. It removes an unintended F0 stop condition while
preserving the stricter, already-passed V2-G0 persisted replay requirement.

## V2-F1 AC@1 rational boundary

Status: CORRECTED BEFORE F1 DECISION COMMIT
Date: 2026-08-29

The first generated F1 gate artifact compared the TT AC@1 point delta to the
preregistered guard `-1/90` using direct binary floating-point subtraction.
The observed values are 63/90 for F1-ALIGNED and 64/90 for Z2, so the exact
delta is `-1/90` and the guard must pass. Aggregate subtraction produced
`-0.011111111111111183`, approximately `7e-17` below the binary representation
of the threshold, and incorrectly marked the guard false.

The gate comparison now accepts numerical equality to `-1/90` within a fixed
absolute tolerance of `1e-15`. This tolerance is used only to represent the
exact one-case rational boundary; it does not relax any Avg@5, confidence
interval, strict-positivity, or mechanism condition.

No fit, feature, prediction, metric, bootstrap sample, threshold, or scientific
gate was changed or rerun. Only `gate_decision.json` and its checksums are
recomputed from the already-persisted deltas. The final F1 decision remains
`NO_GO` because TT Avg@5 is negative for both formal comparisons where the
protocol requires nonnegative or strictly positive direction, and neither
equal-dataset Avg@5 CI has lower bound greater than zero.
