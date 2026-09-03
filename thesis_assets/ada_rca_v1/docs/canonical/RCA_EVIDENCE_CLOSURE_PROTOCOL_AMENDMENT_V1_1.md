# RCA Evidence Closure Protocol Amendment V1.1

Status: **POST-AUDIT PROTOCOL CLARIFICATION**  
Original frozen protocol: `docs/RCA_EVIDENCE_CLOSURE_PROTOCOL.md`  
Frozen optimization commit: `53c9face2c96761c9114edb558eb6d8666a38dc6`  
V1 scientific reference: `bed295326e567395e725caa82840a534dcc0b1de`  
Gate 0 audit result: `RCA_EVIDENCE_NOT_CLOSED` at
`4e4d1f5694617723a6707b10d133f56e1284c2b4`

## Amendment status and timing

This document is a **post-audit clarification**. It is not, and must not be
represented as, the original preregistration or as a pre-observation change to
the frozen protocol. The original Gate 0 result and all legacy artifacts remain
part of the immutable audit record.

This amendment is committed before the corrected Gate 1 metric reconstruction
and Gate 2 bootstrap results are calculated or inspected. At the amendment
commit, neither
`artifacts/evidence_closure/metric_reconstruction_v1_1.json` nor
`artifacts/evidence_closure/bootstrap_corrected_v1_1.json` exists. Git commit
ancestry and the later artifact-introducing commits provide the executable
ordering evidence.

## Confirmed internal inconsistency

The frozen protocol's Gate 1 says:

> Derive root ranks from complete frozen rankings when available, otherwise use
> an explicitly identified immutable root-rank artifact.

This text explicitly permits an immutable root-rank artifact as the scientific
input to independent rank-metric reconstruction when a complete ranking is not
available.

The Gate 0 implementation, however, assigns every root-rank-only source both
`ranking_completeness = FAIL` and
`frozen_prediction_status = FROZEN_PREDICTION_EVIDENCE_UNAVAILABLE`. It then
promotes both states to fatal defects and emits `downstream_gate_authorization =
STOP`. The Gate 0 failure report simultaneously records that the PER-DATASET
root-rank rows preserve enough information to reproduce rank-derived aggregate
metrics.

Therefore the protocol authorizes a root-rank fallback for Gate 1, while its
Gate 0 implementation prevents that authorized fallback solely because the
same artifact cannot establish complete candidate-level ranking integrity.
This is `PROTOCOL_INTERNAL_INCONSISTENCY_CONFIRMED`.

The amendment does not change the Gate 0 factual finding: complete
PER-DATASET candidate scores and rankings are absent and cannot be regenerated.
It separates the evidence requirements for two different scientific claims.

## Sole rationale

Different scientific claims require different levels of frozen evidence.

Candidate-level claims about a complete score/ranking object require the whole
immutable object. Metrics that are mathematical functions only of the true
root's rank can be independently reconstructed from an immutable, complete,
provenance-valid case-level root-rank artifact. Evidence sufficient for the
second class of claim does not become evidence for the first.

This clarification is not justified by a desire to continue an experiment, to
rescue performance, or to obtain a passing V1 result. Any rank-metric mismatch,
provenance failure, invalid pairing, leakage finding, or material change in the
method-selection interpretation retains its specified stopping consequence.

## Evidence level 1: `FULL_RANKING_INTEGRITY`

A track-dataset result may be labelled `FULL_RANKING_INTEGRITY_PASS` only when
all of the following are established from immutable frozen artifacts:

- a complete candidate ranking is present;
- complete candidate scores are present where the frozen output format expects
  scores;
- every legal candidate is represented exactly once;
- no candidate is duplicated;
- the labelled root is present;
- scores and ranking order are consistent;
- ties and candidate ordering follow the deterministic frozen rule; and
- case and fold provenance are valid.

Failure or absence of any required candidate-level evidence prevents this
label. A root-rank-only artifact can never receive
`FULL_RANKING_INTEGRITY_PASS`.

## Evidence level 2: `RANK_METRIC_SUFFICIENT`

A track-dataset result may be labelled `RANK_METRIC_SUFFICIENT_PASS` when all
of the following are established:

- the root-rank source is a committed immutable artifact;
- its SHA-256 digest is recorded;
- it contains exactly the expected 90 cases;
- case IDs are unique;
- folds are valid and agree with the canonical fold assignment;
- root and fault mappings agree with the canonical sidecar;
- each root belongs to the legal candidate registry;
- every root rank is an integer;
- every root rank satisfies `1 <= root_rank <= candidate_count`;
- no model re-fit is required;
- the artifact is traceable to the frozen optimization commit; and
- no root rank has been modified after the audit began.

For a complete frozen ranking, the root rank must be independently derived from
that ranking and the same case, fold, root, registry, immutability, and range
checks apply. Thus a full-ranking track does not receive this label merely by
possessing a ranking; it must also satisfy the root-rank sufficiency checks.

`RANK_METRIC_SUFFICIENT_PASS` authorizes only:

- AC@1, AC@3, and AC@5;
- Avg@5;
- MRR;
- case-level paired bootstrap of those rank-derived metrics; and
- fault-stratified rank-metric diagnostics.

It does not support:

- full candidate-ranking completeness;
- absence of duplicate candidates in a missing ranking;
- score/ranking consistency;
- deterministic candidate ordering;
- score calibration; or
- candidate-level prediction reproducibility.

PER-DATASET-OPT must permanently retain
`FULL_RANKING_INTEGRITY_NOT_AUDITABLE`, even if it receives
`RANK_METRIC_SUFFICIENT_PASS`.

## Gate routing under this clarification

Gate 0 is decomposed into claim-specific evidence classifications:

1. `FULL_RANKING_INTEGRITY` controls candidate-level ranking-integrity claims.
2. `RANK_METRIC_SUFFICIENT` controls Gate 1 rank-metric reconstruction and,
   only after Gate 1 passes, Gate 2 paired rank-metric bootstrap.

A failure of `FULL_RANKING_INTEGRITY` remains fatal for candidate-level claims
but is not, by itself, a fatal defect for root-rank-only scientific quantities.
A failure of `RANK_METRIC_SUFFICIENT` is fatal for that track-dataset's Gate 1
metrics and all dependent bootstrap claims. A reconstructed metric mismatch
beyond the declared numeric tolerance remains fatal and stops bootstrap.

No missing candidate ranking may be imputed, reconstructed by model fitting, or
treated as indirectly verified by matching aggregate metrics. No method,
feature, search space, frozen prediction, score, ranking, or root rank may be
changed.

## Post-audit safety restriction

Because this clarification follows the Gate 0 audit, the maximum terminal state
available in this audit is `RCA_FREEZE_READY_WITH_LIMITATION` when V1 evidence
is otherwise valid but PER-DATASET full-ranking evidence remains incomplete.
This amendment cannot authorize an unconditional
`RCA_SCIENTIFIC_FREEZE_READY` state.

The other allowed terminal states remain:

- `RCA_EVIDENCE_CLOSED_HUMAN_DECISION_REQUIRED` when corrected evidence is
  closed but materially changes the previous method-selection interpretation;
  and
- `RCA_EVIDENCE_NOT_CLOSED` when core rank-metric, provenance, statistical, or
  leakage evidence fails.

Only a later explicit human decision may alter this post-audit safety ceiling.
