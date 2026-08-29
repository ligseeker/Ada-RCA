# P6-G1 Integration Qualification Decision

Decision date: 2026-08-29  
Branch: `exp/p6-baselines`  
Governing protocol: `docs/P6_E4_TIER_A_INTEGRATION_QUALIFICATION_PROTOCOL.md`  
Qualification report: `docs/P6_E4_TIER_A_INTEGRATION_QUALIFICATION_REPORT.md`

## 1. Fixed Gate Rule

P6-G1 is GO only when all frozen Tier-A methods are READY:

`BARO == READY AND TraceRCA == READY AND mmBARO == READY`

Otherwise P6-G1 is PARTIAL and awaits human review. A blocked method cannot be
replaced automatically by a Tier-B method.

## 2. Qualification Inputs

| Tier-A method | P6-E4 status | Controlling evidence |
|---|---|---|
| BARO | `READY` | All frozen smoke executions succeeded with deterministic, valid service projection |
| TraceRCA | `BLOCKED / UNSUPPORTED_INPUT` | Deterministic F-A upstream failure on one frozen TT smoke case; no semantic patch permitted |
| mmBARO | `BLOCKED / SEMANTIC_AMBIGUITY` | No explicit upstream evidence establishes the `re2-*` to `mm-*` dataset alias |

The performance firewall passed. No localization performance, correctness,
root-position, comparative, bootstrap, runtime-comparison, or published-result
signal entered this decision.

## 3. Gate Evaluation

The fixed conjunction is false because TraceRCA and mmBARO are not READY.

**P6-G1 = PARTIAL — AWAITING HUMAN REVIEW**

## 4. Consequence

- Tier A remains BARO, TraceRCA, and mmBARO without replacement.
- Tier B is not executed or promoted.
- The TraceRCA upstream failure is preserved as raw F-A evidence and is not
  converted to a localization score.
- The mmBARO trace channel is not activated through an unsupported alias.
- Ada-RCA and the frozen scientific baseline remain unchanged.
- Formal P6-E5 baseline reproduction is not authorized or executed.

**STOPPED — formal P6-E5 baseline reproduction has NOT been executed.**
