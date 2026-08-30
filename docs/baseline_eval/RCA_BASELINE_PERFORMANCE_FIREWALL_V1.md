# RCA Baseline Performance Firewall V1

Status: **ACTIVE — B0/B1**  
Date: 2026-08-30

## Purpose

This firewall separates protocol and adapter decisions from baseline outcomes.
It applies to BARO, CIRCA, MicroCause, MicroRank, TraceRCA, mmBARO, CausalRCA,
RCD, and every context-only method considered by the audit.

## Forbidden during B0/B1

- Running a real RE2 case through a baseline method.
- Joining a native/adapted baseline output to `root_service` or `fault_type`.
- Calculating, loading, transcribing, displaying, or comparing baseline AC@k,
  Avg@5, MRR, root ranks, win/loss counts, or deltas to Ada-RCA.
- Reading published baseline score tables for method selection.
- Selecting methods, adapters, completion rules, timeouts, or seeds using an
  outcome.
- Evaluating only successful cases.
- Treating a fallback column order, dummy ranking, or random ranking as output.

## Allowed during B0/B1

- Reading source code, dependency metadata, committed case metadata, candidate
  registries, and label sidecars for identity checks.
- Checking that roots belong to the frozen registry without ranking anything.
- Inspecting timestamp magnitudes, headers, units, and half-open window logic.
- Compiling or importing source without invoking a real baseline case.
- Calling public adapter logic with synthetic names and timestamps.
- Calling a baseline only on a synthetic/minimal fixture if needed to validate
  schema semantics; no real label may be attached.
- Counting canonical cases, candidates, terminal status records, missing
  records, or timestamp-unit conformance.

## Mechanical controls

1. B0/B1 code exposes no aggregate performance evaluator.
2. Case-result persistence accepts no root label, root rank, AC, Avg@5, MRR,
   winner, delta, or comparison field.
3. The protocol audit reads `inputs.jsonl`, `sources.jsonl`, and registries;
   labels are read only by frozen identity tests and never passed to adapters.
4. Exactly 90 terminal records are required per selected method and dataset.
5. Silent fallback signatures are converted to `METHOD_FAILURE`.
6. The execution-authorization matrix is frozen before any real invocation.
7. Full execution is a later, separately authorized phase.

## Breach handling

If a real baseline outcome is exposed, immediately persist a
`PERFORMANCE_FIREWALL_BREACH` record containing time, command or source, methods,
datasets/cases affected, fields exposed, and containment action. Do not delete
or hide the record. Stop protocol decision-making and request user review.

## B0/B1 breach register

`NONE` as of the protocol-freeze commit. Existing Ada-RCA frozen evidence was
read as required; no RCAEval baseline performance value, case root rank,
aggregate, winner table, or Ada-RCA/baseline delta was generated or inspected.
