# Final Ada-RCA Structural and Shortcut Control Audit

Status: COMPLETE; all control comparisons are `CONTROL_SEPARATED`  
Generating source commit: `dcd1f14ebaa5b34281a04222e20ebec2e85c2a7a`  
Bootstrap: 10,000 paired fault-stratified resamples, seed `20260827`.

All deltas below are `FINAL_Z2 - CONTROL`. Positive values favor the frozen
final method. RE2-OB and RE2-TT are resampled separately; the mean is the
equal-dataset arithmetic mean.

## S0: train-seen-root-set structural baseline

Every fold contains five distinct training-seen roots on both datasets. This
is a benchmark/root-universe structural baseline, not a root-frequency prior or
feature-leakage baseline.

### S0-A deterministic registry order

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.200000 | 0.600000 | 1.000000 | 0.600000 | 0.456667 |
| RE2-TT | 0.200000 | 0.600000 | 1.000000 | 0.600000 | 0.456667 |

| Delta | RE2-OB point [95% CI] | RE2-TT point [95% CI] | Equal-dataset mean [95% CI] |
|---|---:|---:|---:|
| Avg@5 | +0.362222 [+0.293333, +0.431111] | +0.251111 [+0.171111, +0.328889] | +0.306667 [+0.254444, +0.358889] |
| AC@1 | +0.677778 [+0.566667, +0.788889] | +0.511111 [+0.400000, +0.622222] | +0.594444 [+0.511111, +0.672222] |

State: `CONTROL_SEPARATED`.

### S0-B analytical tie-neutral expectation

The event-level expected metrics use the actual highest-score tie group in
each fold/event. No Monte Carlo permutation and no hard-coded group size were
used. The observed group size is five for every event under the current
balanced design.

| Dataset | Expected AC@1 | Expected AC@3 | Expected AC@5 | Expected Avg@5 | Expected MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.200000 | 0.600000 | 1.000000 | 0.600000 | 0.456667 |
| RE2-TT | 0.200000 | 0.600000 | 1.000000 | 0.600000 | 0.456667 |

| Delta | RE2-OB point [95% CI] | RE2-TT point [95% CI] | Equal-dataset mean [95% CI] |
|---|---:|---:|---:|
| Avg@5 | +0.362222 [+0.333333, +0.384444] | +0.251111 [+0.202222, +0.300000] | +0.306667 [+0.278889, +0.334444] |
| AC@1 | +0.677778 [+0.611111, +0.744444] | +0.511111 [+0.433333, +0.588889] | +0.594444 [+0.544444, +0.644444] |

State: `CONTROL_SEPARATED`. The benchmark root universe provides substantial
performance by itself, especially AC@5 = 1.0, but it does not match the final
method on Avg@5 or AC@1. `BENCHMARK_ROOT_UNIVERSE_DOMINANT` is not triggered.

## S1: observability-only RCA

S1 uses only Z1 `coverage` and `channel_available` for four channels (8D).

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.211111 | 0.444444 | 0.788889 | 0.491111 | 0.411737 |
| RE2-TT | 0.000000 | 0.000000 | 0.122222 | 0.048889 | 0.092427 |

| Delta | RE2-OB point [95% CI] | RE2-TT point [95% CI] | Equal-dataset mean [95% CI] |
|---|---:|---:|---:|
| Avg@5 | +0.471111 [+0.397778, +0.546667] | +0.802222 [+0.740000, +0.862222] | +0.636667 [+0.588889, +0.684444] |
| AC@1 | +0.666667 [+0.566667, +0.766667] | +0.711111 [+0.633333, +0.788889] | +0.688889 [+0.627778, +0.750000] |

State: `CONTROL_SEPARATED`. Observability carries some RCA information on OB,
but it is far below the final method and is nearly uninformative on TT.
`OBSERVABILITY_SIGNAL_DOMINANT` is not triggered. This result does not prove
absence of instrumentation effects; S2 and S3 address stable pre-event
fingerprints more directly.

## S2: pre-event-only RCA

S2 was extracted anew from only `[t0-600,t0)` in the official derived telemetry
files. It uses exactly pre mean q, pre max q, pre coverage, and pre available
per channel (16D). It does not reuse full-event Z2/Z3 normalization or active
state.

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.322222 | 0.644444 | 0.922222 | 0.642222 | 0.536402 |
| RE2-TT | 0.022222 | 0.222222 | 0.344444 | 0.211111 | 0.194791 |

| Delta | RE2-OB point [95% CI] | RE2-TT point [95% CI] | Equal-dataset mean [95% CI] |
|---|---:|---:|---:|
| Avg@5 | +0.320000 [+0.253333, +0.388889] | +0.640000 [+0.551111, +0.726667] | +0.480000 [+0.425556, +0.536667] |
| AC@1 | +0.555556 [+0.444444, +0.666667] | +0.688889 [+0.611111, +0.766667] | +0.622222 [+0.555556, +0.688889] |

State: `CONTROL_SEPARATED`. Pre-event service/telemetry structure contains
meaningful RCA information on OB and weaker information on TT, but it does not
reproduce final performance. `CORE_INTERPRETATION_NOT_SUPPORTED` is not
triggered by the frozen S2 rule.

## Numerical integrity and deviation

All S1/S2 folds now converge with gradient infinity norm `<= 1e-8`. Maximum
norms are:

| Control | RE2-OB | RE2-TT |
|---|---:|---:|
| S1 | 7.4311499176e-09 | 6.3117133742e-10 |
| S2 | 6.8223204863e-14 | 1.2095879853e-13 |

The first uncommitted run exposed a float64 strict-loss-comparison issue in
Newton polishing. The ULP-aware numerical deviation is fully disclosed in
`docs/FINAL_AUDIT_PROTOCOL_DEVIATIONS.md`. The valid rerun produced identical
root ranks, metrics, point deltas, confidence intervals, and control states.
Candidate scores changed by at most `1.2121e-6`. One RE2-OB S1 case changed
only the ordering of non-root candidates at ranks 7-10; its root remained rank
4. The convergence residual/state was corrected without changing any RCA
metric or scientific state.

## Current scientific consequence

S0, S1, and S2 are all separated from the final method under the pre-frozen
rule. This retains, with limitations, the possibility that post-event
event-relative evidence contributes information beyond the benchmark root
universe, observability alone, and the exact pre-event representation tested.
It does not isolate which individual Z2 components cause the gain, does not
erase post-selection, and does not establish a universal morphology mechanism.
S3 and the anchor feasibility audit remain authorized.
