# RCAEval Confirmatory Baseline Protocol Freeze V1

Status: **PERFORMANCE-BLIND PROTOCOL FREEZE**  
Phase: **B0/B1 — protocol and adapter audit only**  
Date: 2026-08-30  
Ada-RCA evidence start: `9342e06db91945be2e44703437229ba45b18bda8`  
Ada-RCA scientific V1 reference: `bed295326e567395e725caa82840a534dcc0b1de`  
Optimization record: `53c9face2c96761c9114edb558eb6d8666a38dc6`  
RCAEval source: `5e96b700445bfb5c599e505ecf37d53bf847bbeb`

This document preregisters the confirmatory baseline protocol. It does not
contain, authorize, compute, or summarize baseline performance. The protocol
becomes effective only when the execution matrix and machine-readable freeze
are committed. Full confirmatory execution additionally requires user review.

## 1. Scientific boundary

Ada-RCA V1 is immutable. This work must not modify Z2, feature extraction,
Conditional Logit, lambda, folds, candidate registries, root mappings,
predictions, or metrics. Baseline outcomes cannot reopen V1 and cannot be used
to tune Ada-RCA, select an adapter, select a seed, or redesign this protocol.

The future comparison asks how fixed methods behave on one fixed benchmark
task. It does not establish causal identification, untouched external
confirmation, cross-system generalization, or superiority of Ada-RCA's
representation mechanism.

## 2. Performance-blind selection

Eligibility is decided only from task relevance, scientific-family diversity,
source provenance, executable path, dependency availability, adapter
feasibility, output semantics, and deterministic control. Remembered,
published, reproduced, or accidentally observed scores are prohibited inputs.

The audit classification is one of:

- `EXECUTABLE-CANDIDATE`: a legal callable path and semantics-preserving
  adapter exist;
- `EXECUTION-AUDIT-REQUIRED`: code exists but a semantic, dependency, or
  determinism question is unresolved; or
- `CONTEXT-ONLY`: a defensible run would require algorithm invention or a
  substantial semantic modification.

The execution gate is separately one of:

- `AUTHORIZED_FOR_CONFIRMATORY_EXECUTION`;
- `BLOCKED_PENDING_SEMANTIC_AUDIT`;
- `BLOCKED_INCOMPATIBLE`; or
- `CONTEXT_ONLY`.

No full baseline run is legal until its gate value is frozen in Git and the
user has reviewed the freeze.

## 3. Canonical evaluation unit

The only datasets are `RE2-OB` and `RE2-TT`. Each dataset has exactly 90
canonical events. Event identity and order are the committed `case_id` values
in:

- `artifacts/source/re2ob/inputs.jsonl`; and
- `artifacts/source/re2tt/inputs.jsonl`.

The event anchor is the committed integer `anchor_time`, equal to the
corresponding `inject_time.txt`, in Unix seconds. Labels are joined only after
a valid case result is persisted. Predictive adapters must not receive root
service, fault type, relative source directory, injection target, or a label-
derived alias.

The legal candidate universes are exactly the label-free registries in:

- `artifacts/source/re2ob/service_registry.json` — 11 services; and
- `artifacts/source/re2tt/service_registry.json` — 68 services.

Root labels are exactly the sidecars in `artifacts/source/<dataset>/labels.jsonl`.
There is no case-specific hand correction.

## 4. Window and anchor policy

The canonical source window is the half-open interval
`[t0 - 600 seconds, t0 + 600 seconds)`. The adapter supplies that source window
when doing so does not replace native internal processing.

Window classifications mean:

- `WINDOW-ALIGNED`: the method consumes the supplied interval and does not
  select a materially different internal interval;
- `WINDOW-COMPATIBLE-WITH-NATIVE-INTERNAL-PROCESSING`: the exact source window
  is supplied, but the native method resamples, splits, truncates, or selects an
  internal subwindow that is part of the audited algorithm; and
- `WINDOW-NOT-COMPARABLE`: no defensible common-window invocation exists.

For metric and derived 15-second series, `time` and `t0` are seconds. Raw trace
`startTime` and `duration` are microseconds. Trace adapters filter by native
span-end time `startTime + duration` in the half-open microsecond source window
and pass `t0 * 1_000_000` to MicroRank and TraceRCA. They do not convert
duration, bin raw spans, or replace the methods' end-time split.

Native internal processing is retained and disclosed. In particular, CIRCA's
RHT path loads `t0-120` through `t0+300` at one-second resolution from the
supplied source window; mmBARO strides metric rows by 15, splits each derived
series at `t0`, and removes two normal trace-error values; MicroCause uses the
supplied full series without an explicit pre/post split.

## 5. Frozen service adapter

The adapter is label-independent and uses only the ordered native output and
the frozen legal registry.

1. Normalize the single frozen raw-trace alias `frontendservice` to `frontend`.
2. Match a native item to the longest legal candidate that is either the exact
   item or is followed by the native underscore separator.
3. Retain the first occurrence of each mapped service. This is the best/earliest
   native-rank rule and is used for every method because the audited callable
   outputs return ordered names, not scores.
4. Record later mappings to the same service as duplicates; do not let them
   consume adapted service positions.
5. Record unmapped or non-registry items and omit them. Do not create candidate
   evidence, guess aliases, or map using the root label.
6. If no legal service remains, emit `ADAPTER_FAILURE`.

This adapter creates an adapted partial service ranking. It does not claim that
indicator or operation ranking was natively a service-ranking task.

## 6. Native and partial-ranking policy

Native output granularity must be preserved in each result record:

- indicator ranking;
- operation ranking;
- service ranking;
- graph nodes plus a ranking;
- native top-k; or
- complete native list over the method's retained nodes.

AC@1, AC@3, AC@5, and Avg@5 are identifiable for the first five items of an
ordered native list after the frozen service projection. MicroRank is not
described as native top-5: although its call passes `top_max=5`, the pinned
implementation retains indices `< top_max + 6` and therefore returns up to 11
operations. Only its identifiable first-five prefix is used for top-5 metrics.
Absence from the exhausted native first-five prefix is a negative top-5
retrieval result. Avg@5 is computed
only from the five identifiable nested top-k relationships. It must never use a
fabricated rank below the known list.

MRR requires a legitimate complete ranking of every frozen legal service. None
of the audited RCAEval methods naturally guarantees that property. Therefore
baseline MRR is `NOT-IDENTIFIABLE` in V1.

## 7. Candidate completion

Candidate completion is frozen to `NONE` for every RCAEval baseline. Missing
legal services are not alphabetically appended, randomly appended, ordered by
registry position, or assigned tied scores. Consequently there is no adapted
complete-ranking metric in this protocol.

Each case records missing-service reasons without conflation:

- `NO_OBSERVED_TELEMETRY`;
- `ALGORITHM_FILTERED_INDICATOR`;
- `NATIVE_TOP_K_TRUNCATION`;
- `ADAPTER_MISMATCH`; or
- `EXECUTION_FAILURE`.

## 8. Failure and denominator policy

Every canonical case emits exactly one terminal status:

- `SUCCESS`;
- `METHOD_FAILURE`;
- `ADAPTER_FAILURE`;
- `DATA_FAILURE`; or
- `TIMEOUT`.

All selected methods use a hard per-case timeout of 3,600 seconds. The timeout
is an execution-safety limit and is not selected from observed performance.

The denominator remains 90 cases per dataset. Failures are persisted before
any label join. A failure is never replaced by input-column order, a random or
dummy ranking, an alphabetical ranking, or omission. RCAEval's exception
decorator signature (`adj == []` with ranks equal to preprocessed column order)
and CausalRCA's empty-graph column-order return are classified as
`METHOD_FAILURE`, not predictions. Successful-subset metrics are prohibited.

## 9. Randomness

One canonical run is frozen for each method. There is no seed search.

- BARO, TraceRCA, and mmBARO have no explicit RNG call in the audited path.
- CIRCA and MicroCause use NumPy RNG.
- MicroRank uses unordered Python sets and therefore requires a fixed process
  hash seed even though it has no explicit RNG call in its RCA entry point.
- CausalRCA uses Torch parameter initialization and may use NumPy/Python state.
- RCD uses NumPy permutation when and if its environment is authorized.

The canonical seed is `20260830` for Python, NumPy, and Torch. Confirmatory
workers must start with `PYTHONHASHSEED=20260830`. Torch methods run on CPU with
deterministic algorithms enabled. A worker that cannot establish these controls
must emit `ADAPTER_FAILURE`; it must not proceed nondeterministically.

## 10. Metric legality states

Metric cells use only:

- `NATIVE`;
- `ADAPTED-BUT-VALID`; or
- `NOT-IDENTIFIABLE`.

Ada-RCA's complete service ranking is `NATIVE` for all five metrics. A baseline
indicator/operation-to-service top-k is `ADAPTED-BUT-VALID` for AC@1, AC@3,
AC@5, and Avg@5. MRR is `NOT-IDENTIFIABLE` for every audited RCAEval baseline.
Metric values are outside this phase and outside this document.

## 11. Compatibility tiers

- `P1_SAME_TASK_HIGH_COMPATIBILITY`: native service ranking with compatible
  cases and candidates;
- `P2_BENCHMARK_COMPARABLE_WITH_MATERIAL_DIFFERENCES`: root-ranking utility is
  comparable but supervision, native granularity, candidate universe,
  preprocessing, telemetry, or output completeness differs; and
- `P3_CONTEXT_ONLY`: unbiased quantitative comparison is not supported.

Executable RCAEval methods remain P2. Ada-RCA is root-label supervised and
cross-case trained; the audited RCAEval paths are case-wise and label-free.
That difference must appear beside future results and is neither hidden nor
used as a post-hoc penalty.

## 12. Execution record contract

Each future case record must include protocol version, Git commits, method,
dataset, case ID, source identity, candidate-registry digest, start/end time,
timeout, seed controls, window classification, native output kind, native output
length, mapped services, duplicates, unmapped entries, missing-candidate reasons,
terminal status, and a sanitized error when applicable.

No aggregate evaluator is part of B0/B1. Label joins and metric aggregation are
disabled until the user reviews this committed freeze and starts a separate
confirmatory-execution phase.

## 13. Stop rule

This phase stops after protocol, adapter, provenance, timestamp, failure, and
firewall tests pass. It must end before any real baseline performance is
inspected. Any accidental exposure is logged as `PERFORMANCE_FIREWALL_BREACH`
and cannot silently influence this freeze.
