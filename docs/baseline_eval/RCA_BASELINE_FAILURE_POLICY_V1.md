# RCA Baseline Failure Policy V1

Status: **FROZEN BEFORE PERFORMANCE EXECUTION**  
Date: 2026-08-30

## 1. Scope

This policy applies to every selected method, dataset, and one of the 90 frozen
case IDs. It replaces RCAEval's exception-to-column-order behavior and
successful-subset evaluator for confirmatory execution.

## 2. Preflight gate

Before cases are scheduled, the runner must verify the exact RCAEval commit,
clean source state, Python/dependency manifest, candidate/input digests,
protocol digest, canonical seed controls, writable output directory, and method
authorization. A preflight failure invalidates the run before case inference;
it is not converted to 90 localization errors and no metric is legal.

RCD has no authorized environment in V1 and must not be scheduled. Context-only
methods must not be scheduled.

## 3. Terminal case states

Every scheduled case ends in exactly one state.

### `SUCCESS`

The method returned a valid native ranking, no audited fallback signature was
detected, at least one native item mapped to the frozen registry, and the
label-free case record was persisted.

### `METHOD_FAILURE`

The legal input reached the method, but the method raised, returned no/invalid
native ranking, produced a numerical failure, used a method-defined invalid
fallback, or violated its frozen native-output contract. Specific detections
include:

- RCAEval decorator output `adj=[]` plus preprocessed input-column order;
- CausalRCA empty adjacency plus input-node order;
- MicroRank output longer than its pinned cap of 11;
- empty or non-string native ranks; and
- a method exception after valid input delivery.

### `ADAPTER_FAILURE`

The method returned structurally valid native output, but the frozen projection
could not legally produce a service prediction. Examples are zero legal mapped
services, an ambiguous/non-frozen alias, invalid serialization, or unavailable
deterministic controls. Adapter failures are not method predictions.

### `DATA_FAILURE`

The required case input is missing, unreadable, digest-invalid, schema-invalid,
outside the frozen case set, has inconsistent timestamp units, or does not
match the frozen candidate/event metadata. The method is not invoked.

### `TIMEOUT`

The per-case worker exceeds 3,600 wall-clock seconds. The worker is terminated,
partial output is discarded, and the timeout record is persisted.

## 4. Classification precedence

Use the first applicable state:

1. pre-invocation source/schema/digest defect -> `DATA_FAILURE`;
2. hard deadline exceeded -> `TIMEOUT`;
3. native call exception/invalid output/fallback -> `METHOD_FAILURE`;
4. legal native output cannot be projected/persisted -> `ADAPTER_FAILURE`;
5. otherwise -> `SUCCESS`.

No exception is caught and replaced by a ranking.

## 5. Persistence contract

Persist one atomic JSON record per method/dataset/case. Every record contains
protocol and source provenance, case ID, method, dataset, timing, seed controls,
window/output semantics, native/adapted lengths, duplicate/unmapped audit, and
terminal state. A failure record contains no native or adapted ranking. Errors
are sanitized to exclude file contents and labels.

Labels and performance fields are rejected from case records. Root labels are
joined only in a later, separately authorized evaluation phase after all 90
terminal records exist.

## 6. Denominator and subset rule

The required record identity is the exact frozen set of 90 case IDs per
dataset. Duplicate, missing, or foreign IDs invalidate the method/dataset run.
Failures remain in the denominator. A successful-subset table may not replace
the 90-case confirmatory result and is not authorized by this freeze.

## 7. No fallback or completion

Forbidden replacements include input column order, registry order,
alphabetical order, random/dummy ranking, previous-case output, cached output
from another commit, and appended unobserved services. Candidate completion is
`NONE`.

## 8. Retry policy

There is no automatic retry. A method failure or timeout remains terminal for
the frozen attempt. A systematic data/adapter defect invalidates the run and
requires a documented protocol-preserving repair, new attempt identifier, and
user review before any rerun. The original attempt record is retained. Reruns
cannot be selected by outcome.

## 9. Crash recovery

Atomic case files are the recovery boundary. On restart, already valid records
are verified by digest; missing cases are not silently interpreted as failures
or omitted. Resumption is permitted only before labels are joined and only with
the same commits, environment, protocol, seed, and timeout.

## 10. Firewall interaction

Status counts may be audited during execution because they are operational,
not localization performance. Root-conditioned failure analysis, root ranks,
AC@k, Avg@5, MRR, winners, and deltas remain forbidden until the separate
performance phase is authorized.
