# P6-E4 Tier-A Integration Qualification Protocol

Status: **FROZEN BEFORE ANY TIER-A RCA METHOD INVOCATION**  
Date: 2026-08-29  
Branch: `exp/p6-baselines`  
Base SHA: `bed295326e567395e725caa82840a534dcc0b1de`

## 1. Objective and Scope

P6-E4 is a **NON-PERFORMANCE INTEGRATION QUALIFICATION**. It asks:

> Can the frozen Tier-A RCAEval baselines be executed with semantically valid
> inputs and auditable outputs before formal performance reproduction?

It does not ask which method performs better. This round authorizes P6-E4 and
P6-G1 only. It does not authorize P6-E5 formal baseline performance
reproduction, runtime comparison, Tier-B execution, Ada-RCA modification, or
method development.

The frozen Tier-A methods are, without substitution:

1. A1 BARO;
2. A2 TraceRCA; and
3. A3 multi-source BARO (`mmbaro`).

The only datasets are RE2-OB and RE2-TT.

## 2. Scientific Boundary

`main` remains the frozen scientific baseline. P3-G1, P4-G0, the Final Method,
P6 Final Evaluation Protocol V1.0, P6-G0, and
`BASELINE_SELECTION_NON_INTERFERENCE_PASS` remain unchanged.

This work must not modify Z2, the event-level conditional-logit scorer, lambda,
splits, candidate registries, frozen Tier A/B/C membership, or historical
scientific conclusions. It must not introduce a new RCA method, dataset,
topology model, GNN, Transformer, attention mechanism, P5 stage, or result-based
rescue.

## 3. Performance Firewall

Qualification code and decisions must not access root labels or import/call a
performance evaluator. This round must not produce or calculate:

- AC@1, AC@3, or AC@5;
- Avg@5;
- MRR;
- root rank, hit, correctness, or accuracy;
- Ada-RCA versus baseline deltas;
- bootstrap comparisons;
- runtime comparisons; or
- leaderboards.

Published performance values must not influence adapter behavior, timestamp
conversion, event-window semantics, service mapping, dataset aliases, modality
activation, completion rules, Tier membership, execution priority, or whether
a method is worth running. All integration decisions use only source semantics,
dataset schema, provenance, implementation behavior, compatibility, and
deterministic engineering facts.

## 4. Upstream Provenance and Isolation

The only authorized RCAEval source is a clean detached checkout of:

- remote: `https://github.com/phamquiluan/RCAEval.git`;
- commit: `5e96b700445bfb5c599e505ecf37d53bf847bbeb`.

Before qualification, `git rev-parse HEAD` must equal the pinned commit and
`git status --porcelain` must be empty. The clean checkout is read-only for this
round. All adapters, compatibility handling, instrumentation, and artifacts
belong to Ada-RCA on `exp/p6-baselines`.

Upstream provenance must record the clean path, remote, HEAD, clean status,
Python and package versions, and SHA-256 checksums for:

- `RCAEval/e2e/baro.py`;
- `RCAEval/e2e/tracerca.py`;
- `RCAEval/e2e/__init__.py`;
- `RCAEval/io/time_series.py`; and
- `main.py`.

An isolated environment may be created when required by documented Python or
dependency compatibility. Environment choice must follow repository
requirements, original method specifications, or official compatibility
documentation, never RCA performance. Environment records must include the
environment name, Python/package versions, dependency source, installation
commands, freeze/export, and pinned RCAEval commit.

## 5. Dataset and Static Audit

All 180 legal RE2 cases may be inspected for schema, source presence,
timestamp magnitude, row counts, and static support. The all-case audit may
record only:

- dataset and normalized case path;
- available source files and missing-source flags;
- `inject_time`;
- file row counts and malformed-row counts;
- timestamp column names and min/max values;
- trace `startTime`, `duration`, and derived end-time min/max;
- `logts`, `tracets_err`, and `tracets_lat` support.

It must not record root labels, root correctness, root rank, baseline hits, or
evaluation metrics.

## 6. Deterministic Smoke Manifest

Before the first Tier-A method invocation, enumerate legal case directories in
each dataset, normalize each path relative to its dataset root using POSIX path
separators, compute SHA-256 of that relative path, sort by ascending hash with
the normalized path as a deterministic tie-breaker, and select the first three.

The six selected cases and hashes must be stored in
`artifacts/p6_e4/smoke_case_manifest.json` and committed before method
execution. Selection must not use root, fault performance, method output, or
published performance.

Each Tier-A method must execute the same frozen six cases twice per case.

## 7. Native Output and Service Projection

The frozen output policy is:

> native ranking -> deterministic service projection -> preserve first
> occurrence -> deduplicate service.

Unranked legal services must not be appended. A partial native ranking remains
a partial projected ranking. Qualification must not manufacture a complete
ranking for MRR, AC@5, or any other performance purpose.

Every mapping rule must be label-free, deterministic, audited against the
legal service registry, and report collisions, conflicts, unknown names,
duplicates, NaN values, and empty output. Special mappings such as `-db` must
be source/schema justified and dataset-independent unless an explicit dataset
governance rule is documented.

## 8. Failure Instrumentation

RCAEval's generic exception-to-dummy-ranking fallback is not a valid result.
The adapter must capture raw exceptions and distinguish:

- F-A: algorithmic no-output or method failure;
- F-B: officially unsupported input;
- F-C: environment or dependency failure;
- F-D: Ada-RCA adapter or integration failure; and
- F-E: data-integrity failure.

P6-E4 records status only. No failure is converted to performance zero. A
dummy fallback, successful-subset suppression, or fabricated ranking is not
accepted.

## 9. BARO Qualification

The official callable is `RCAEval/e2e/baro.py::baro`. Input is
`simple_metrics.csv` plus `inject_time.txt`. The adapter freezes the half-open
window `[t0 - 600, t0 + 600)` and records loader preprocessing, forward/zero
fill behavior, RCAEval preprocessing, BARO's pre-event `RobustScaler`, and
indicator-ranking semantics. Ada-RCA Z2 preprocessing must not enter this path.

Indicator-to-service mapping must be derived by auditing all observed indicator
names against the label-free legal service registry. `split("_")[0]` is not an
accepted universal assumption without evidence. Collisions, unknowns, and any
special mappings must be explicit.

For every repeat, record input rows, pre/post rows, native/projected rank
lengths, duplicate count, unknown count, execution status, and ranking
checksum. BARO is READY only when upstream provenance is clean, the frozen
window and input are valid, all smoke executions succeed, repeat outputs are
deterministic, mapping is valid, and the performance firewall passes.

## 10. TraceRCA Qualification

The official callable is `RCAEval/e2e/tracerca.py::tracerca`. Before any call,
the timestamp-unit audit must determine the units of `inject_time`,
`startTime`, `duration`, and `startTime + duration` from pinned source/history,
official documentation/demos, original implementation where available, raw
numeric magnitude, and data-generation semantics. Conversion factors must not
be tried and selected by localization performance.

The timestamp audit must record numerical evidence, source evidence, the
chosen conversion factor, justification, OB/TT consistency, and remaining
ambiguity. If the units cannot be uniquely justified, TraceRCA is
`BLOCKED / SEMANTIC_AMBIGUITY` and must not be invoked.

The adapter freezes raw-span selection to `[t0 - 600, t0 + 600)`. The inclusion
timestamp follows official RCAEval/original TraceRCA semantics where defined;
otherwise the quantity most consistent with TraceRCA's internal pre/post split
is frozen and labeled `ADAPTER ASSUMPTION`. Boundary semantics are half-open.
Every smoke input must contain selected, pre-event, and post-event spans.

Native operation names must be mapped through the explicit raw-span
`operation <-> serviceName` relationship, not string splitting alone. Conflicts,
unknown services, NaN, empty output, duplicates, rank lengths, and checksums are
recorded. TraceRCA is READY only when timestamp semantics are uniquely
justified, the event window is frozen, pre/post inputs are nonempty, mapping is
valid, upstream code is unchanged, repeats are deterministic, and the
performance firewall passes.

## 11. mmBARO Qualification

The official callable is `RCAEval/e2e/baro.py::mmbaro`. Before any call, static
analysis must classify each data-dictionary key (`metric`, `logs`, `logts`,
`traces`, `tracets_err`, `tracets_lat`, `cluster_info`) as required by access,
used by score computation, or loaded but unused. Key presence alone does not
establish modality use.

The dataset alias audit must determine from clean RCAEval source/history,
documentation, notebooks, official scripts, and data-path semantics whether
`re2-ob -> mm-ob` and `re2-tt -> mm-tt` are intended aliases. Performance may
not be used. Insufficient evidence sets
`mmBARO = BLOCKED / SEMANTIC_AMBIGUITY`; the trace branch must not be forced
open.

The modality activation audit must classify metric, log time series, trace
error time series, trace latency time series, raw logs, raw spans, and
`cluster_info` as `USED`, `LOADED_NOT_USED`, `NOT_LOADED`, or `UNAVAILABLE`.
Only actually consumed inputs may be described as modalities.

Smoke execution is authorized only after the input dictionary, alias, and
modality activation rules are frozen. Each repeat records active-source row
counts and pre/post counts, native/projected rank lengths, duplicates, unknowns,
active modality set, raw exception, status, and checksum.

## 12. Qualification States

Each method receives exactly one top-level state:

- `READY`;
- `BLOCKED / SEMANTIC_AMBIGUITY`;
- `BLOCKED / UNSUPPORTED_INPUT`;
- `BLOCKED / ENVIRONMENT`;
- `BLOCKED / OUTPUT_MAPPING`; or
- `INVALID`.

`INVALID` is reserved for adapter contamination, protocol violation,
data-integrity failure, or root/performance leakage into an integration
decision. A method requiring an algorithm-semantic patch is blocked rather
than rescued.

## 13. P6-G1 Rule

Only:

`BARO == READY AND TraceRCA == READY AND mmBARO == READY`

permits:

**P6-G1 = GO — TIER-A INTEGRATION QUALIFIED**

Otherwise:

**P6-G1 = PARTIAL — AWAITING HUMAN REVIEW**

Tier-B substitution and formal baseline reproduction are not automatic under
either state. This round must stop after the P6-G1 decision.
