# P3-A0.5 Event-Relative Telemetry Representation Freeze

Status: FROZEN before any P3-A1/P3-A2 morphology performance result.

This document fixes the complete numeric representation used by Z0, Z1, Z2, Z3, and Z3-SHUFFLE. Any factual infeasibility discovered later must be handled through the protocol-deviation procedure in `RESEARCH_STATUS.md`; unfavorable performance is not a reason to change this representation.

## 1. Event window and grid

- Window: half-open `[t0 - 600 s, t0 + 600 s)`.
- Common grid: 80 event-relative bins of width 15 seconds.
- Pre-event bins: indices `0..39`, relative starts `-600, -585, ..., -15` seconds.
- Post-event bins: indices `40..79`, relative starts `0, 15, ..., 585` seconds.
- A timestamp is assigned by `floor((timestamp - (t0 - 600)) / 15)` when it lies in the half-open window.
- Duplicate observations in one indicator/bin are averaged over finite values.
- No interpolation, forward fill, backward fill, or synthetic boundary value is introduced.
- An empty timestamp, non-finite timestamp/value, or absent cell is missing and contributes only through masks. A recorded numeric zero is an observed zero.

This matches RCAEval's official default `--length 20` context (10 minutes before and after t0) while using one common 15-second grid for all four channels.

## 2. Source channels and cadence

Fixed channel order:

1. `metric`: `simple_metrics.csv`, native cadence 1 second, averaged into the common 15-second bins.
2. `log`: `logts.csv`, native cadence 15 seconds.
3. `trace-error`: `tracets_err.csv`, native cadence 15 seconds.
4. `trace-latency`: `tracets_lat.csv`, native cadence 15 seconds.

The raw `metrics.csv`, `logs.csv`, and `traces.csv` files remain provenance evidence. The frozen numerical representation consumes the official derived files above so that all modalities have auditable scalar indicator time series. In `simple_metrics.csv`, the `time` column and columns ending in `_latency-50` are excluded; all other numeric indicator columns, including `_latency-90`, are eligible.

## 3. Indicator-to-service mapping

Mapping is label-free and uses only the frozen candidate registry and telemetry column schema.

- Metric columns map only when the column begins with the exact string `<candidate>_`; the longest matching candidate is selected.
- Log and trace columns use the same longest exact `<candidate>_` prefix rule.
- For RE2-OB trace columns only, raw prefix `frontendservice_` is normalized to `frontend_` before matching because the trace schema and deployment registry use these two official aliases.
- `frontend-external`, `traceservice`, `health`, auxiliary containers, and any unmatched entity remain unmapped.
- No root label, fault type, condition directory, or historically injected-service list is consulted.

## 4. Robust pre-event normalization

For each scalar indicator independently, use its observed pre-event bin values only:

`center = median(pre)`

`scale = 1.4826 * median(|pre - center|)`

If `scale < 1e-6`, use:

`scale = (Q75(pre) - Q25(pre)) / 1.349`

If the fallback is still `< 1e-6`, or no finite pre-event value exists, the indicator is degenerate and is excluded from deviation aggregation for all bins. It is not assigned a fake deviation.

For a valid observed value:

`d(t) = (x(t) - center) / (scale + 1e-6)`.

Center/scale are case-local, indicator-local, and pre-event-only. They do not use labels, other cases, post-event values, or test-fold statistics.

## 5. Service-channel aggregation

For service `i`, channel `m`, and bin `t`:

`q_i,m(t) = Q90` over finite `|d(t)|` values of valid indicators mapped to that service/channel.

- Quantiles use linear interpolation as implemented by NumPy's default continuous quantile.
- If no valid indicator is observed in a bin, `q` is missing and the observation mask is `0`.
- Missing `q` is never treated as a real zero. Numeric arrays use zero only as the storage fill value accompanied by mask `0`.

## 6. Base evidence B_i

For every service and each of the four channels, compute from observed `q` values:

1. `magnitude`: maximum post-event `q`.
2. `mean_impact`: mean post-event `q`.
3. `pre_post_shift`: mean post-event `q` minus mean pre-event `q`.
4. `onset_seconds`: first post-event bin start in `0, 15, ..., 585` where `q >= 3.0` and the immediately following observed bin also has `q >= 3.0`.
5. `onset_missing`: `0` when onset exists, otherwise `1`.
6. `persistence`: fraction of observed post-event bins with `q >= 3.0`.
7. `coverage`: observed `q` bins divided by 80.
8. `channel_available`: `1` only when at least one observed pre-event and one observed post-event `q` value exist; otherwise `0`.

When `channel_available = 0`, all numeric base values except `onset_missing=1` and `coverage` are stored as zero. Missing onset uses the end-window sentinel `600` seconds before the availability rule is applied. `B_i` concatenates these eight fields in the fixed channel order, producing 32 features.

## 7. Frozen anomaly magnitude A_i and Z0

For each available channel, compute `min(20, magnitude)`. The service anomaly magnitude is:

`A_i = mean over available channels of min(20, magnitude_i,m)`.

If no channel is available, `A_i = 0`. This rule is label-free. Z0 contains only the single scalar `A_i`.

Magnitude ranking sorts decreasing `A_i`; exact ties use canonical service-registry order. This same ranking defines MI-1 and MI-3.

## 8. Amplitude-normalized morphology z_i,m(t)

For each service-channel:

`z(t) = q(t) / (max_observed q + 1e-6)`.

If no `q` is observed or `max_observed q < 1e-6`, morphology is inactive:

- `morphology_active = 0`;
- stored `z` values are zero;
- the original q-observation mask is retained.

Otherwise `morphology_active = 1`. Missing bins store `z=0` with observation mask `0`.

## 9. Frozen variant feature definitions

- Z0: `[A_i]`.
- Z1: the 32-dimensional `B_i` vector.
- Z2: Z1 plus, per channel, the following eight summaries of observed normalized morphology: pre mean, post mean, post-minus-pre mean, post peak-time fraction (`post_bin / 39`, sentinel `1` if absent), post amplitude-weighted temporal centroid fraction, post ordinary-least-squares slope against post-bin fraction, mean absolute difference over adjacent observed post bins, fraction of observed post bins with `z >= 0.5`, followed by `morphology_active`. Z2 therefore adds 36 fields (9 per channel).
- Z3: Z1 plus, per channel, 80 stored `z` values, 80 q-observation-mask values, and one `morphology_active` value. Z3 adds 644 fields (676 total including the 32 Z1 fields).
- Z3-SHUFFLE: identical to Z3 except that, independently for each case, the 80 temporal positions are permuted using a deterministic permutation seeded by SHA-256 of `"Ada-RCA|P3-G1|20260826|<opaque_case_id>"`. The same case permutation is applied to z and its mask for all candidates and channels. Case ID, seed, or permutation is never exposed as a model feature. This preserves the per-channel multiset, amplitude normalization, masks, and dimensionality while destroying cross-case temporal alignment.

The shuffle rule is frozen now. It must not be changed after performance inspection.

## 10. Missingness, numerical storage, and feature order

- Fixed channel order is `metric`, `log`, `trace-error`, `trace-latency`.
- Within a channel, feature order is exactly the order listed above.
- Missing numeric values are stored as zero only when accompanied by the corresponding availability/observation mask.
- No service-name embedding, one-hot service identity, fault-type feature, path token, topology, graph feature, raw log text, or raw trace graph is included.
- Candidate registry order is fixed by the committed service registry and is used only for output coverage and deterministic tie-breaking.

## 11. Learning boundary

OB and TT are learned independently. For every OOF fold:

- `StandardScaler` is fit on training-fold candidate rows only.
- Logistic regression is L2, `C=1.0`, `max_iter=5000`, with no hyperparameter search.
- Test-fold cases contribute neither scaler statistics nor training labels.
- Candidate scores are sorted decreasing; exact score ties use canonical registry order.

## 12. Scientific interpretation

The tested hypothesis is strictly incremental: after Z1 already supplies magnitude, onset, pre/post shift, persistence, and coverage, does the full normalized trajectory in Z3 improve ranking? Z3-SHUFFLE tests whether any improvement depends on aligned temporal order rather than the same unordered values.
