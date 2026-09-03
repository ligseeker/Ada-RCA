# Evidence-Level Semantic Correction V1.1

Status: **CANONICAL GATE 5 INTERPRETATION LAYER**
Machine-readable artifact:
`artifacts/evidence_closure/evidence_semantic_correction_v1_1.json`

## Scope

This document corrects the meaning of subcheck statuses in
`metric_reconstruction_v1_1.json`. It does not rewrite that Gate 1 artifact,
the Gate 0 failure report, or any frozen prediction, score, ranking, root-rank,
feature, or bootstrap artifact. Those files remain immutable historical
evidence.

The canonical status meanings are:

- `PASS`: the claim was directly verified from available immutable evidence;
- `FAIL`: available evidence directly contradicts the required condition; and
- `NOT_AUDITABLE`: the required object was not frozen, so the condition cannot
  be evaluated.

Missing evidence is not affirmative contradictory evidence. Conversely,
root-rank metric reproducibility does not reconstruct or validate the missing
complete ranking.

## PER-DATASET semantic correction

The prior Gate 1 artifact correctly assigns both PER-DATASET datasets the
overall status `FULL_RANKING_INTEGRITY_NOT_AUDITABLE`. Its eight nested full-
ranking checks were nevertheless all encoded as `FAIL`. Gate 5 separates those
subchecks by their actual evidence object.

### Historical `FAIL` values corrected to `NOT_AUDITABLE`

For both RE2-OB and RE2-TT:

| Historical Gate 1 check | Canonical interpretation |
|---|---|
| `immutable_complete_candidate_ranking` | `NOT_AUDITABLE`: no complete candidate ranking was frozen |
| `complete_candidate_scores_where_expected` | `NOT_AUDITABLE`: no complete candidate score object was frozen |
| `every_legal_candidate_exactly_once` | `NOT_AUDITABLE`: membership cannot be checked in the missing ranking |
| `no_duplicate_candidate` | `NOT_AUDITABLE`: duplicate absence cannot be checked in the missing ranking |
| `root_present` | `NOT_AUDITABLE` for root presence in the missing complete ranking; root mapping and legal-registry membership pass separately |
| `score_to_ranking_consistency` | `NOT_AUDITABLE`: neither complete scores nor the complete ranking are available |
| `deterministic_tie_and_order_consistency` | `NOT_AUDITABLE`: ordering cannot be checked without scores and the complete ranking |

The canonical layer additionally records `score_calibration` and
`complete_candidate_level_reproducibility` as `NOT_AUDITABLE`. These were not
separate historical subchecks, but they are candidate-level properties of the
same missing object.

### Historical `FAIL` corrected to `PASS`

`valid_fold_and_case_provenance` becomes
`case_and_fold_provenance_from_root_rank_artifact = PASS`. The immutable
root-rank artifact directly establishes exact 90-case coverage, unique case
IDs, valid 30/30/30 folds, and agreement with the canonical fold assignment.
The historical check was false only because its implementation incorrectly
required `spec["kind"] == "full"` before recognizing the already verified
provenance.

### Directly verified checks that remain `PASS`

For both PER-DATASET datasets, the canonical root-rank evidence directly
verifies:

- case coverage and case-ID uniqueness;
- fold provenance;
- root and fault mapping;
- root membership in the legal candidate registry;
- integer root ranks within the legal candidate-count range;
- committed-artifact immutability and absence of post-audit modification;
- recorded SHA-256 identity and traceability to the frozen optimization
  commit; and
- no requirement for model re-fit.

These checks support `RANK_METRIC_SUFFICIENT_PASS`. They do not support any
property of the absent complete score/ranking object.

## Canonical evidence-level decision

| Track | Dataset | FULL_RANKING_INTEGRITY | RANK_METRIC_SUFFICIENT |
|---|---|---|---|
| V1-SCIENTIFIC | RE2-OB | `FULL_RANKING_INTEGRITY_PASS` | `RANK_METRIC_SUFFICIENT_PASS` |
| V1-SCIENTIFIC | RE2-TT | `FULL_RANKING_INTEGRITY_PASS` | `RANK_METRIC_SUFFICIENT_PASS` |
| GLOBAL-OPT | RE2-OB | `FULL_RANKING_INTEGRITY_PASS` | `RANK_METRIC_SUFFICIENT_PASS` |
| GLOBAL-OPT | RE2-TT | `FULL_RANKING_INTEGRITY_PASS` | `RANK_METRIC_SUFFICIENT_PASS` |
| PER-DATASET-OPT | RE2-OB | `FULL_RANKING_INTEGRITY_NOT_AUDITABLE` | `RANK_METRIC_SUFFICIENT_PASS` |
| PER-DATASET-OPT | RE2-TT | `FULL_RANKING_INTEGRITY_NOT_AUDITABLE` | `RANK_METRIC_SUFFICIENT_PASS` |

No genuine `FAIL` remains after applying the status definitions to the
available evidence. This does not cure the limitation: PER-DATASET complete
candidate rankings, duplicate absence, score/ranking consistency,
deterministic candidate ordering, score calibration, and complete candidate-
level reproducibility remain permanently unauditable.
