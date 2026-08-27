# Ada-RCA Final Evaluation Protocol V1.0

Status: **FROZEN BEFORE EXTERNAL-BASELINE PERFORMANCE INSPECTION**  
Date: 2026-08-27  
Scope: final evaluation governance for standalone coarse-grained service-level
RCA on RCAEval RE2-OB and RE2-TT.

This protocol does not reopen method development. The final operational method
remains the frozen 68-dimensional Z2 event-relative multimodal representation
with event-level conditional-logit ranking, lambda 1.0, train-fold-only
`StandardScaler`, deterministic float64 fitting, repetition-based three-fold
OOF, and a complete legal candidate ranking. P3-G1 and P4-G0 remain
`NO-GO / CLOSED`; integrity remains `INTEGRITY_VALID`, the scientific claim is
`SCIENTIFIC_CLAIM_RESTRICTED`, and implementation status is
`FINAL_METHOD_IMPLEMENTATION_FROZEN`.

No RCAEval Table 6 performance value was inspected in freezing this document.

## 1. Scientific questions and evidence layers

Final evaluation answers two different questions and must not merge their
interpretations.

### Layer I: controlled internal scientific evidence

Layer I asks whether Ada-RCA's event-relative representation contains useful
RCA information. It uses only existing Z0, Z1, Z2, Z3, Z3-SHUFFLE, A0 versus
A2, and S0/S1/S2/S3 evidence. It supports temporal-information interpretation,
compact-representation justification, and shortcut falsification within the
already studied corpus. It is not reopened for optimization or rerun.

### Layer II: external benchmark competitiveness

Layer II asks where the frozen Ada-RCA result lies on the RE2 benchmark using a
small future set of external RCA baselines. This layer primarily measures
benchmark competitiveness. Unless a close protocol match is independently
established, it does not show that the morphology representation is
scientifically superior to an external algorithm.

External benchmark comparison evaluates benchmark competitiveness under
heterogeneous learning assumptions unless a closer protocol match is
explicitly established.

## 2. Scope, task, and candidate semantics

The only authorized datasets are RE2-OB and RE2-TT. RE2-SS, RE1, RE3, GAIA,
and all new datasets are excluded absent new human authorization.

The primary task is coarse-grained service-level RCA. Every result represents a
ranked list of root-cause services. Metric-level or indicator-level localization
must not be mixed into the primary service-level comparison. Fault display
aliases may normalize capitalization or presentation only; they must not alter
ground-truth semantics.

Ada-RCA uses the complete label-free legal candidate registry for each case.
Every external method's native candidate and output semantics must be recorded
before comparison. Converting operation- or metric-level output to services is
an adapter operation and must be audited for name mapping, deduplication,
coverage, and information loss. Missing candidates must not be silently treated
as a complete ranking.

## 3. Metrics and reporting granularity

Primary headline metrics are:

- AC@1;
- AC@3;
- Avg@5.

Secondary metrics are AC@5, MRR when a legitimate full ranking exists, runtime,
and execution/failure status. S0 in the Final Audit reaches AC@5 = 1.0 from the
train-seen root universe alone. AC@5 therefore has limited discrimination and
must not be the primary performance claim.

Formal results must report RE2-OB and RE2-TT separately; a pooled 180-case score
cannot replace either dataset result. When legal outputs permit it, each dataset
must also report CPU, MEM, DISK, SOCKET, DELAY, and LOSS separately, with AC@1,
AC@3, and Avg@5 as the fault-level primary metrics.

## 4. Performance-blind baseline eligibility

External-baseline inclusion is decided without published or reproduced
performance. The compatibility audit and reproduction matrix may use only:

1. service-level task and ground-truth compatibility;
2. minimum coverage of metric, trace, and multi-source method families;
3. actual consumed telemetry and derived inputs, including raw/derived form,
   event-window semantics, anchor dependence, and topology if any;
4. availability and provenance of the RCAEval and original implementations;
5. environment and auxiliary-runtime feasibility;
6. output and service-name compatibility;
7. objectively evidenced reproduction effort; and
8. scientific diversity in modality, algorithm, or inference assumptions.

Paper category alone does not establish an input-condition match. A new method
should add a scientifically distinct role rather than a redundant implementation
of an already represented family. The objective is the smallest defensible
representative matrix, not reproduction of every RCAEval method.

### 4.1 Reproduction effort

`LOW` means the method is already included in a pinned usable RCAEval
environment, needs no external runtime or algorithm patch, and requires only
adapter-level integration.

`MEDIUM` means a separate Python environment or limited auxiliary dependency
stack is needed, but the official execution path is clear and no
algorithm-semantic modification is required.

`HIGH` requires factual evidence such as an unavailable or obsolete dependency,
external service, incompatible language/runtime, substantial patch, or unclear
source provenance. The phrase "implementation complex" is not sufficient.

Unresolved facts are recorded as `UNKNOWN - REQUIRES EXECUTION AUDIT`; they are
not guessed.

## 5. Statistical pairing and protocol comparability

These are separate dimensions.

Statistical pairing is `PAIRABLE` only when both methods can produce a clear
case-level ranking utility on the same failure cases. It is `NOT_PAIRABLE` when
a legal one-to-one case-level comparison cannot be formed. Static uncertainty
before execution may be recorded as `UNKNOWN - REQUIRES EXECUTION AUDIT` in the
compatibility audit, but a statistical analysis requires a resolved status.

Protocol comparability is:

- `P1_CLOSE_PROTOCOL_MATCH`: learning task, root semantics, and
  candidate/evaluation setup are close;
- `P2_BENCHMARK_COMPARABLE_WITH_MATERIAL_DIFFERENCES`: benchmark context is
  valid but supervision, candidate universe, preprocessing, telemetry, or
  inference assumptions differ materially;
- `P3_CONTEXT_ONLY`: published/reference context only.

A reproduced method may be `PAIRABLE` and P2 at the same time: mathematical
case-level comparison is possible while scientific interpretation remains
qualified.

## 6. Supervision and fairness disclosure

Every method must record whether it uses root-label training, cross-case
training, case-wise unsupervised inference, pretraining, or external knowledge.
Ada-RCA is root-label supervised, cross-case trained, and evaluated as
known-root x known-fault new-repetition OOF. Many RCAEval methods may be
case-wise or unsupervised. These are learning-assumption differences, not facts
to hide or post-hoc penalties.

`Ada-RCA > external baseline` alone must never be used to conclude that the
morphology mechanism is superior. The final table and prose must state the
supervision and information conditions beside every score.

## 7. Execution failure taxonomy

Failure handling is frozen before any external method is run.

### F-A: algorithmic no-output or method failure

The legal input reached the method correctly, but numerical failure, empty
output, no ranking, or a method-defined failure occurred. A robustness view may
assign utility zero, and must report failure rate separately. The primary table
must retain the explicit execution status.

### F-B: officially unsupported input

The official method explicitly does not support an otherwise legal benchmark
case or input. Such cases remain visible. The primary complete-case scientific
metric is not computed by silently deleting them. The frozen robustness view
assigns utility zero to F-B cases only when the method was selected as
applicable to that dataset; the unsupported rate and successful-subset metric,
if shown, must be separate and clearly labeled.

### F-C: environment or dependency failure

Missing packages, incompatible Python, compilation failure, or unavailable
runtime are not localization errors. The scientific metric is `NR / NOT RUN`,
not zero.

### F-D: project adapter or integration failure

Service mapping, serialization, path, or evaluator defects in this project make
the run `INVALID RUN`. They must be repaired and rerun before interpretation;
they are not baseline failures.

### F-E: data integrity failure

Data-integrity failure is reported separately and stops the affected
comparison. It cannot be converted to a method score.

The RCAEval wrapper's own exception fallback or successful-subset evaluator is
not automatically adopted: raw execution status and output validity must be
audited under this taxonomy.

## 8. Reproduced and published evidence

`Reproduced` evidence is generated by this project and includes case-level
predictions. Subject to pairing and integrity, its metrics may be recomputed and
its case-level differences bootstrapped.

`Published reference` evidence comes from a paper or human-verified
transcription. It is context only. It cannot support paired bootstrap,
significance, same-protocol, or independent-reproduction claims. Published-only
rows must be explicitly marked and must never be silently combined with
reproduced rows.

## 9. Statistical policy

Only reproduced, integrity-valid, `PAIRABLE` methods qualify for paired
analysis. Use paired failure cases, fault-stratified bootstrap, 10,000
resamples, seed `20260827`, with RE2-OB and RE2-TT analyzed separately. The
primary contrast is Delta Avg@5; Delta AC@1 is secondary. No bootstrap, p-value,
or significance comparison is permitted for published-only references. The
evaluation will not conduct a large family of multiple hypothesis tests.

## 10. Runtime policy

Runtime is supplementary evidence and cannot alter method selection. Future
runs should use the same machine where feasible and record hardware,
environment, warm/cold condition, and failures. Training and inference must be
separated; preprocessing and model ranking must also be separated. Ada-RCA may
not report only `beta @ z`, and external methods should be timed at the closest
comparable boundary. Repeated timings use a robust summary such as the median.

## 11. Frozen final evidence tables

### Table A: External Benchmark Context

Columns include method, modality, root-label training, cross-case training,
pairing status, protocol comparability, separate OB and TT AC@1/AC@3/Avg@5,
execution status/failure rate, and runtime when available. Published-only rows
are explicitly marked.

### Table B: Internal Representation Evidence

This table uses only existing Z0, Z1/A0, Z2/A2, Z3, and Z3-SHUFFLE evidence. It
does not trigger optimization or rerun.

### Table C: Shortcut Falsification

This table contains S0, S1, S2, and final Z2. S3 remains a separate
service-identity diagnostic rather than an RCA baseline.

### Table D: Fault-Level Evidence

Fault-level evidence is reported separately for RE2-OB and RE2-TT using the
six frozen fault semantics.

## 12. Claim boundary and stop conditions

Final evaluation does not authorize untouched confirmation, independent
replication, unseen-root or unseen-fault generalization, cross-system
generalization, causal RCA, a universal morphology mechanism, SOTA, topology
being unnecessary, full trajectories being universally ineffective, or
candidate-relative information being universally useless.

This freeze authorizes only static compatibility classification and a future
baseline-selection decision. It does not authorize external baseline execution,
runtime benchmarking, Ada-RCA modification, retraining, hyperparameter search,
new datasets, thesis writing, or GradPaper synchronization.
