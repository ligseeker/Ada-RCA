# RCAEval RE2-TT Published Context and Non-Interference Audit

Date: 2026-08-27  
Status: **BASELINE_SELECTION_NON_INTERFERENCE_PASS**  
Baseline-selection freeze commit:
`41bfd10bdfc76861736ad1ea0268bf65255df52d`  
First reference inspection: after the freeze commit above

## 1. Source and evidence status

Requested source:
`docs/RCAEVAL_RE2_TT_TABLE6_PUBLISHED_REFERENCE.md`

Source SHA-256:
`20c023fad3795274f9f20f4925cf37b494fb31adf208160c01833180b4cab030`

The source is the user's human-extracted and human-verified transcription of
RCAEval paper Table 6. It is accepted as the requested published source for
this round. No PDF extraction, OCR, ACM access, alternative webpage, numeric
correction, or source substitution was performed.

**Human-verified published reference; not reproduced by Ada-RCA.**

The source is context only. It contains no Ada-RCA-generated case-level
predictions and cannot support metric recomputation, paired bootstrap,
statistical significance, same-protocol, or independent-reproduction claims.

## 2. Coverage

The source title describes eight baselines, and the table contains eleven
data-source/method rows because BARO, CIRCA, and RCD also appear as
multi-source variants. The eight unique method names are BARO, CausalRCA,
CIRCA, MicroCause, RCD, MicroRank, TraceRCA, and PDiagnose.

It covers RE2-TT only. For each row it reports CPU, MEM, DISK, SOCKET, DELAY,
and LOSS, plus AVERAGE, with AC@1, AC@3, and Avg@5. It does not report RE2-OB,
AC@5, MRR, runtime, execution/failure status, case-level rankings, candidate
coverage, or uncertainty.

Relationship to the performance-blind frozen matrix:

- Tier A is fully represented: metric BARO, TraceRCA, and multi-source BARO.
- Tier B is fully represented: CIRCA, MicroRank, RCD, MicroCause, and
  CausalRCA.
- Tier C is fully represented as published context: multi-source CIRCA,
  PDiagnose, and multi-source RCD.

Published coverage does not establish that the local pinned implementation,
preprocessing path, failure handling, or actual consumed modalities reproduce
the paper result. In particular, the static compatibility audit's
implementation findings remain controlling for future reproduction.

## 3. Descriptive context

Across the eleven published AVERAGE rows in the requested source:

- AC@1 ranges from 0.06 to 0.69;
- AC@3 ranges from 0.11 to 0.82; and
- Avg@5 ranges from 0.13 to 0.81.

Across individual fault cells, the source includes values from 0 to 1. These
ranges describe the transcription; they are not a ranking criterion and do not
alter the frozen reproduction plan.

For context only, frozen Ada-RCA's descriptive RE2-TT replay is AC@1
0.7111111111, AC@3 0.8666666667, and Avg@5 0.8511111111. This juxtaposition is
not a reproduced external comparison. Ada-RCA is root-label supervised and
cross-case trained under known-root x known-fault new-repetition OOF, while the
audited RCAEval paths are generally case-wise and root-label-free and differ in
telemetry, candidate, preprocessing, and output assumptions. No superiority,
SOTA, margin, significance, or morphology-mechanism conclusion is authorized.

The source provides no published RE2-OB result. No OB external-baseline value
is inferred.

## 4. Adversarial non-interference audit

The post-read audit compares the committed freeze artifact at `41bfd10` with
the current matrix. The freeze artifact was not modified.

1. **Tier A methods changed?** No. They remain BARO, TraceRCA, and multi-source
   BARO.
2. **Tier B methods changed?** No. They remain CIRCA, MicroRank, RCD,
   MicroCause, and CausalRCA.
3. **Tier C methods changed?** No. They remain multi-source CIRCA, PDiagnose,
   and multi-source RCD.
4. **Reproduction priority changed?** No. Tier A remains BARO, TraceRCA, then
   multi-source BARO; Tier B engineering order also remains unchanged.
5. **Was performance-based reasoning added to selection rationale?** No. The
   freeze artifact and compatibility classifications are unchanged.
6. **Did protocol comparability change because of performance?** No. Static
   learning, candidate, telemetry, preprocessing, and output facts remain the
   basis.
7. **Did reproduction effort change because of performance?** No. Environment,
   dependency, adapter, provenance, and implementation facts remain the basis.
8. **Was a previously unselected method added because its published value was
   high?** No.
9. **Was a method deleted or demoted because its published value was low?** No.
10. **Did any result-based rescue logic appear?** No. No selection, method,
    adapter, dataset, or protocol rescue was proposed.

Adversarial check: the source contains values for every Tier A/B/C entry, so it
could have supported post-hoc promotion, demotion, or reprioritization. None
occurred. Any future desire to change the matrix after seeing these values must
be recorded only as a post-freeze human-review note and cannot modify P6-G0
without new human authorization.

**BASELINE_SELECTION_NON_INTERFERENCE_PASS**

## 5. Claim and action boundary

Published context does not widen Ada-RCA's scientific claim. It does not
authorize untouched confirmation, independent replication, unseen-root or
unseen-fault generalization, cross-system generalization, causal RCA, universal
morphology, SOTA, topology claims, or statistical comparison with published
rows.

No external baseline was executed. No runtime benchmark, Ada-RCA modification,
retraining, hyperparameter search, dataset expansion, thesis writing, or
GradPaper synchronization was performed.

**P6-G0 = FROZEN - AWAITING HUMAN REVIEW**

**STOPPED - no external baseline reproduction authorized**
