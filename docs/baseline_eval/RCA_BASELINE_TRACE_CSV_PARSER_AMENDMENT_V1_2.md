# RCAEval Raw-Trace CSV Parser Amendment V1.2

Status: **AUTHORIZED — PERFORMANCE-BLIND PROTOCOL-PRESERVING REPAIR**
Date: 2026-09-01
Scope: MicroRank, TraceRCA, and mmBARO raw-trace input loading

## 1. Incident

TraceRCA attempt `tracerca-a1-20260831` and mmBARO attempt
`mmbaro-a1-20260831` both terminated after 59 RE2-OB records at the same opaque
case, `re2ob-f30e2feeaa5218b8`. The case worker exited with signal 11
(`SIGSEGV`; shell status 139) before it could persist a terminal record.

Python fault-handler stacks independently localized both crashes to Pandas
2.3.3's native C CSV parser while `_read_csv_source` was reading the raw
`traces` role. The failure reproduced both through the preloaded server/fork
path and through a direct worker process, excluding the method server and
cross-worktree concurrency as causes.

The frozen CSV is structurally valid: the standard-library parser observed
365,484 data rows, 11 header columns, and 11 fields in every row. Pandas'
Python engine loaded the same 365,484-by-11 table. With only the parser engine
changed in a diagnostic probe, the previously crashing case reached `SUCCESS`
for both TraceRCA and mmBARO. No label, root rank, or metric was joined or
inspected during diagnosis.

## 2. Frozen repair

For the logical source role `traces`, `_read_csv_source` must call
`pandas.read_csv(path, engine="python")`. Every other CSV role retains its
existing `pandas.read_csv(path)` behavior. No source bytes, columns, rows,
timestamps, trace-window rules, adapters, native method calls, seeds,
candidates, failure denominators, or metric rules change.

This repair also applies prospectively to MicroRank because it shares the same
raw-trace loader. The Python package environment is unchanged, so the already
frozen common-environment identity remains valid. New records bind the repair
through their new execution commit; no environment mutation or dependency
selection is authorized.

## 3. Attempt disposition

The incomplete TraceRCA and mmBARO A1 attempts are retained as execution
evidence and must not be deleted, overwritten, or resumed. MicroRank A1 is also
retained and restarted prospectively because one canonical attempt may not mix
the old and repaired execution commits.

After committing each incomplete A1 record directory, the repair commit may be
integrated into that method's existing task branch. Each method then starts
from case 1 under a new A2 attempt ID, using the unchanged frozen environment:

- `microrank-a2-20260901`;
- `tracerca-a2-20260901`; and
- `mmbaro-a2-20260901`.

There is no automatic retry and no selection between A1 and A2 by outcome. A2
is the only protocol-valid repaired attempt and must still produce exactly 90
terminal records per dataset before its method prediction lock is valid.

## 4. Integrity and firewall

The regression test executes the actual crashing trace read in a subprocess,
so a native parser crash is observed as a nonzero test result rather than
terminating the test runner. A separate scope test ensures that only the raw
trace role uses the Python engine.

Existing A1 terminal statuses, including mmBARO `DATA_FAILURE` records, remain
unchanged evidence. The repair does not authorize reading predictions,
calculating metrics, joining labels, changing the 3,600-second timeout, or
reopening any frozen Ada-RCA decision.

Final decision: `TRACE_CSV_NATIVE_PARSER_REPLACED_WITH_PYTHON_ENGINE_V1_2`.
