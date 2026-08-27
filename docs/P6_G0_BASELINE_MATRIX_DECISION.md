# P6-G0 Performance-Blind Baseline Matrix Decision

Decision date: 2026-08-27  
Status: **BASELINE SELECTION FROZEN**  
Governing protocol commit: `e8ca4c2`  
Compatibility audit commit: `ab352e7`

This decision freezes the smallest defensible future external-baseline matrix
for the final evaluation of frozen Ada-RCA on RE2-OB and RE2-TT. It was made
after static compatibility and environment audit and before any inspection of
`docs/RCAEVAL_RE2_TT_TABLE6_PUBLISHED_REFERENCE.md`.

No published or reproduced external-baseline performance, remembered score,
relative numerical position, or anticipated winner was used. The immutable
freeze SHA is the first commit containing this document and is to be recorded
in the post-freeze context audit and final report without rewriting this file.

## 1. Decision principles

The matrix covers metric, trace, and multi-source families with one Tier A
representative each. Selection uses service-level task fit, official RCAEval
implementation availability, output adaptability, objective environment
feasibility, actual consumed telemetry, and distinct scientific role. Tier A
is intentionally not a catalog of all available methods.

All Tier A methods remain subject to a future non-performance integration gate:
timestamp units, event windows, service projection, legal-candidate completion,
silent fallback detection, and F-A--F-E status persistence must pass before a
performance run is valid. This gate does not reopen method selection and does
not allow algorithm-semantic patches.

## 2. Tier A - Minimum Representative Reproduction Set

### A1. BARO - metric representative

Performance-blind rationale:

- official callable RCAEval implementation at `RCAEval/e2e/baro.py::baro`;
- consumes the official derived metric time series under explicit per-case
  pre/post anchor semantics;
- case-wise, root-label-free robust scaling and anomaly ranking provide a clear
  learning-assumption contrast to Ada-RCA's supervised cross-case scorer;
- local Python 3.10 RCAEval environment contains the dependency stack;
- objective effort is `LOW`: adapter, output validation, and failure
  instrumentation only; and
- provides the metric-statistical family without duplicating a graph learner.

Frozen role: minimum metric-based benchmark representative.

### A2. TraceRCA - trace representative

Performance-blind rationale:

- official callable RCAEval implementation at
  `RCAEval/e2e/tracerca.py::tracerca`;
- consumes raw spans and derives operation latency anomalies, support, and
  confidence, providing genuinely trace-native evidence;
- simpler execution and output path than the alternative trace graph/spectrum
  implementation while retaining a distinct trace-statistical assumption;
- dependency requirements are already local and objective effort is `LOW`;
- operation-to-service projection is auditable; and
- directly fills the trace family not represented by BARO.

The common RCAEval runner's metric-input mismatch and the seconds/microseconds
question are frozen pre-execution adapter/unit-audit requirements. They are not
reasons to replace TraceRCA after performance is known.

Frozen role: minimum trace-based benchmark representative.

### A3. Multi-source BARO (`mmbaro`) - multi-source representative

Performance-blind rationale:

- official exported RCAEval implementation at
  `RCAEval/e2e/baro.py::mmbaro`;
- actual code combines derived metric and log time-series scores, with trace
  branches present but gated by literal dataset keys;
- uses the same transparent robust anomaly-scoring family as BARO, isolating
  the practical effect of adding a modality family without introducing a new
  supervised learner;
- local dependencies are available and objective effort is `LOW`;
- the needed work is a source-dictionary, window, dataset-key, and service-name
  adapter audit rather than algorithm modification; and
- it is the only audited low-effort callable candidate that provides actual
  multi-source consumption on the pinned checkout.

The future report must state the exact modalities actually activated on RE2.
If the trace branch cannot be activated without semantic modification, the
method remains metric+derived-log multi-source and must not be described as
metric+log+trace.

Frozen role: minimum multi-source benchmark representative.

## 3. Tier A execution priority

The frozen validation/reproduction sequence is:

1. BARO, to establish the common metric/service/evaluator and failure-status
   adapter;
2. TraceRCA, to establish the raw-trace timestamp and operation-to-service
   adapter; and
3. multi-source BARO, to establish aligned multi-source windows and record the
   exact activated modalities.

This is an engineering dependency order, not a performance ranking. Published
performance cannot alter it.

## 4. Tier B - Conditional Additions

Tier B methods are not part of the minimum reproduction set. A method may be
promoted for a future human-authorized run only if Tier A has a protocol-valid
path, the addition supplies a distinct scientific role, its environment is
feasible, and no substantial algorithm-semantic modification is needed.
Published score is never a promotion criterion.

### B1. CIRCA

Adds a metric causal-graph plus regression/hypothesis-test family beyond BARO.
The implementation and dependencies are local (`LOW`), but the literal
`dataset="ob"` graph-construction argument on TT and exception-to-dummy fallback
must be resolved by integration validation. It is conditional because metric
coverage already exists in Tier A.

### B2. MicroRank

Adds a trace coverage-graph, PageRank, and spectrum family beyond TraceRCA. It
shares the raw-trace timestamp and service-projection prerequisites and returns
only native top-5 operations. It is conditional on the TraceRCA adapter proving
that the official RE2 raw trace semantics can be handled without algorithm
changes.

### B3. RCD

Adds F-node distribution-change causal discovery beyond BARO/CIRCA. It requires
a separate Python 3.8 dependency environment (`MEDIUM`) and may return a partial
indicator list. It is conditional on a clean official environment and an
audited complete-candidate policy.

### B4. MicroCause

Adds lagged PCMCI, partial-correlation, SLI, and random-walk assumptions. The
required Python 3.10 packages are present (`LOW`), but deterministic execution,
SLI naming, and output completeness require audit. It is conditional because
metric-family coverage is already satisfied and its additional inference stack
does not add a new telemetry modality.

### B5. CausalRCA

Adds a within-case neural graph-learning/PageRank family. The torch stack is
present (`LOW` under the frozen effort definition), but deterministic controls,
empty-graph behavior, and service-candidate output require audit. It is
conditional because it adds an algorithm family, not new telemetry coverage,
and is not needed for the minimum matrix.

Frozen Tier B engineering order is CIRCA, MicroRank, RCD, MicroCause,
CausalRCA. The order reflects incremental adapter reuse and environment burden,
not expected performance.

## 5. Tier C - Reference / Do-Not-Prioritize

### C1. Multi-source CIRCA

No callable multi-source CIRCA implementation or source provenance was found in
the pinned RCAEval Python code or all-branch `mmcirca` search. The existing
`circa()` is metric-only. Effort is `HIGH`, protocol status is P3 context only,
and the method is not pairable from the audited checkout. Do not prioritize
without a human-supplied official source and a new compatibility audit.

### C2. PDiagnose

The RCAEval file is a hard-coded single-case demo, is not exported, accepts no
general case input, applies no explicit event window to its log count, and
prints rather than returns its service ranking. Generalization would require
substantial integration/semantic work (`HIGH`). It is scientifically
multi-source but not part of the executable minimum matrix.

### C3. Multi-source RCD (`mmrcd`)

Although the function accepts a multi-source dictionary, the audited ranking
computation consumes metrics only; log and trace values are loaded but unused.
It therefore duplicates metric RCD rather than adding demonstrated multi-source
coverage, while also requiring a separate environment and adapter (`MEDIUM`).
Do not prioritize it as a multi-source representative.

## 6. Exact frozen matrix

| Tier | Methods | Frozen scientific coverage |
|---|---|---|
| A | BARO; TraceRCA; multi-source BARO | metric statistical; trace statistical; metric+derived-log multi-source statistical |
| B | CIRCA; MicroRank; RCD; MicroCause; CausalRCA | conditional graph, trace-graph, distribution-change, temporal-causal, and neural-graph diversity |
| C | multi-source CIRCA; PDiagnose; multi-source RCD | unavailable path; substantial integration; nominal multi-source redundancy |

This exact Tier A/B/C membership, the priority order, and the rationales above
are immutable after the freeze commit. Published context may reveal values or
coverage but cannot add, remove, promote, demote, or reprioritize a method.

## 7. Decision boundary

P6-G0 freezes a proposed future matrix only. It does not authorize any external
baseline performance or runtime experiment. It does not modify Ada-RCA,
datasets, splits, candidates, features, scorer, lambda, or scientific claims.

**P6-G0 = FROZEN - AWAITING HUMAN REVIEW**

**STOPPED - no external baseline reproduction authorized**
