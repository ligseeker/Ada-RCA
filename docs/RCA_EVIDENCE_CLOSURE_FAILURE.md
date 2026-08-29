# Ada-RCA Evidence Closure Failure Report

## Material Passport

- Artifact type: reproducibility and evidence-integrity validation
- Evidence source: committed repository artifacts only
- Audit start: `53c9face2c96761c9114edb558eb6d8666a38dc6`
- V1 scientific reference: `bed295326e567395e725caa82840a534dcc0b1de`
- Verification status: **ANALYZED — GATE 0 FAILED**
- Terminal scientific state: `RCA_EVIDENCE_NOT_CLOSED`
- Machine-readable evidence: `artifacts/evidence_closure/input_manifest.json`

## A. Repository

- Worktree: `/home/zhangll24/RCA_project/Ada-RCA-evidence`
- Branch: `research/evidence-closure`
- Starting HEAD: `53c9face2c96761c9114edb558eb6d8666a38dc6`
- Remote `research/performance-optimization`: independently resolved by
  `git ls-remote` to the same starting commit.
- The source worktree was clean. The experiment-record branch was not modified.

## B. Frozen Evidence Inventory

| Track | Dataset | Primary source | SHA-256 | Events | Folds | Candidate registry | Root mapping | Complete ranking |
|---|---|---|---|---:|---|---|---|---|
| V1-SCIENTIFIC | RE2-OB | `artifacts/final_method/re2ob/predictions.jsonl` | `1d3bbc30869062c30569bd7b752cc2520d8e1337b8861bf11e55bbd69eaf5ff5` | 90 | 0/1/2: 30/30/30 | PASS, 11 per case | PASS | PASS, 990 entries |
| V1-SCIENTIFIC | RE2-TT | `artifacts/final_method/re2tt/predictions.jsonl` | `e937897d182735651959ad9449a7d6837ac71b029bec0fe90e143395009dd57d` | 90 | 0/1/2: 30/30/30 | PASS, 68 per case | PASS | PASS, 6,120 entries |
| GLOBAL-OPT | RE2-OB | `artifacts/opt/final/GLOBAL-OPT/re2ob/predictions.jsonl` | `1d3bbc30869062c30569bd7b752cc2520d8e1337b8861bf11e55bbd69eaf5ff5` | 90 | 0/1/2: 30/30/30 | PASS, 11 per case | PASS | PASS, 990 entries |
| GLOBAL-OPT | RE2-TT | `artifacts/opt/final/GLOBAL-OPT/re2tt/predictions.jsonl` | `e937897d182735651959ad9449a7d6837ac71b029bec0fe90e143395009dd57d` | 90 | 0/1/2: 30/30/30 | PASS, 68 per case | PASS | PASS, 6,120 entries |
| PER-DATASET-OPT | RE2-OB | `artifacts/opt/final/PER-DATASET-OPT/re2ob/case_ranks.csv` | `dd1d6ec06e96e627320f8978f4c2c9deb19c4c7a5b9226e624cb0349accaf7c7` | 90 | 0/1/2: 30/30/30 | Source registry PASS; prediction coverage not auditable | PASS | **FAIL: root rank only; 0/990 entries frozen** |
| PER-DATASET-OPT | RE2-TT | `artifacts/opt/final/PER-DATASET-OPT/re2tt/case_ranks.csv` | `8758769c66809804faf168b2a5e0a4601f0a40990b2c183dcff314780b52b700` | 90 | 0/1/2: 30/30/30 | Source registry PASS; prediction coverage not auditable | PASS | **FAIL: root rank only; 0/6,120 entries frozen** |

All listed sources are byte-identical to their blobs at `53c9face...`.
Event IDs are unique and expected case coverage is exact. V1 and GLOBAL
rankings contain exactly one entry per legal candidate, contain each root, and
equal the deterministic descending-score ordering with candidate-name tie
breaking.

The two PER-DATASET CSV names are misleadingly redundant: `case_ranks.csv` and
`outer_predictions.csv` are byte-identical. Both contain only `case_id`, fold,
root, fault type, and root rank. Neither contains candidate scores or a complete
ranking. The same files in `artifacts/opt/o4_nested` are also byte-identical.
Git history introduces no earlier complete PER-DATASET prediction artifact.

V1 remains traceable to `bed295...`: that commit is an ancestor of the frozen
optimization commit, and both current V1 prediction files are byte-identical to
the files stored at `bed295...`.

### Fatal Gate 0 finding

For both datasets, PER-DATASET-OPT is:

- `FROZEN_PREDICTION_EVIDENCE_UNAVAILABLE`; and
- `RANKING_COMPLETENESS_FAILURE`.

The root-rank rows preserve enough information to reproduce rank-derived
aggregate metrics, but they do not preserve the complete prediction result
required to test no missing legal candidate, no duplicate candidate, score to
ranking consistency, or ranking determinism. Re-fitting the model would create
a new stochastic result rather than recover the frozen result and is forbidden.
This is therefore a fatal, not merely documentary, evidence defect under the
frozen-prediction and incomplete-ranking rules.

## C. Independent Metric Reconstruction

**NOT RUN — BLOCKED BY GATE 0.** No independently reconstructed AC@1, AC@3,
AC@5, Avg@5, or MRR is promoted as closure evidence. Legacy final metrics remain
historical values, not revalidated values.

## D. Bootstrap Forensic Audit

**NOT RUN — BLOCKED BY GATE 0.** The observed legacy direction/CI discrepancy
remains unresolved. No corrected CI or discrepancy classification is emitted.
The legacy `artifacts/opt/final/bootstrap.json` was not modified.

## E. Telemetry Information-Loss Audit

**NOT RUN — DOWNSTREAM SCIENTIFIC WORK STOPPED.** No candidate-case funnel,
zero-MAD mechanism, or raw-record claim is emitted.

## F. Historical Reference Status

**NOT NORMALIZED — DOWNSTREAM SCIENTIFIC WORK STOPPED.** Existing historical
artifacts were not changed. No C1-I search was rerun.

## G. Ranker Status

**NOT NORMALIZED BY THIS AUDIT.** Existing files were not rewritten. Their
presence in the frozen search-space record does not cure the Gate 0 defect.

## H. Leakage / Shortcut Audit

**NOT RE-VALIDATED BY THIS AUDIT.** Existing label-firewall tests passed in the
repository suite, but this report does not upgrade that observation beyond
`NO_EXPLICIT_LABEL_LEAKAGE_DETECTED`. Service/telemetry fingerprint risk remains
unresolved.

## I. Optimization Interpretation

**WITHHELD.** A scientific GLOBAL-versus-V1 or PER-DATASET-versus-V1 conclusion
is not issued because the PER-DATASET frozen prediction evidence is incomplete.
The legacy aggregate numbers and bootstrap artifact remain historical records.

## J. Thesis Claim Matrix

**NOT GENERATED.** Gate 0 did not authorize the claim matrix. No thesis-facing
claim is upgraded on the basis of this audit.

## K. Tests

- `python -m unittest tests.test_evidence_closure_gate0 -v`: 8 passed.
- `python -m unittest discover -s tests -v`: 67 passed.
- `pytest -q`: unavailable in the existing environment; no dependency was
  installed.

The new tests validate frozen SHA identity, case counts, fold coverage,
root/candidate registry integrity, complete V1/GLOBAL rankings, explicit
PER-DATASET incompleteness, V1 commit traceability, STOP behavior, and output
separation from frozen prediction paths.

Tests passing does not supply the missing PER-DATASET rankings.

## L. Files Changed

- `docs/RCA_EVIDENCE_CLOSURE_PROTOCOL.md`
- `docs/RCA_EVIDENCE_CLOSURE_FAILURE.md`
- `src/rca/evidence_closure.py`
- `scripts/run_evidence_closure_gate0.py`
- `tests/test_evidence_closure_gate0.py`
- `artifacts/evidence_closure/input_manifest.json`

No frozen prediction, score, ranking, metric, bootstrap, feature, model-state,
source, fold, registry, or root-mapping artifact was modified.

## M. Commits

The audit uses self-contained protocol and Gate 0/failure commits. No downstream
phase commit is manufactured after the fatal upstream failure.

## N. FACT

- Remote and local `research/performance-optimization` resolved to
  `53c9face2c96761c9114edb558eb6d8666a38dc6` at audit start.
- V1 and GLOBAL each preserve complete, deterministic rankings for 90 cases per
  dataset.
- V1 and GLOBAL prediction files are byte-identical within each dataset.
- PER-DATASET preserves 90 unique root-rank rows per dataset with exact case,
  fold, fault, and root correspondence.
- PER-DATASET does not preserve candidate scores or complete candidate rankings
  in the committed repository or its relevant Git history.
- No model fit or optimization search was executed during this audit.

## O. INFERENCE

- The PER-DATASET root ranks likely came from the nested-OOF run described by
  the committed selection trace, because the final and O4 root-rank files are
  byte-identical. This does not prove the omitted full rankings.
- The root-rank rows could reproduce rank-based aggregates, but metric
  reproducibility alone would not establish complete prediction integrity.

## P. NOT SUPPORTED

This audit does not support:

- any corrected bootstrap interval or direction classification;
- selection of V1, GLOBAL, or PER-DATASET as a scientifically frozen method;
- universal superiority of FULL-Z2 or any representation;
- benefits from topology, timing/order modelling, or candidate-relative
  representation;
- causal root-cause discovery, unseen-system/root generalization, SOTA, or
  untouched independent external confirmation;
- absence of all leakage or telemetry/service shortcuts; or
- empirical rejection of ranker families that were not executed.

## Q. Limitations and Fallacy Scan

### Fatal

- Missing complete frozen PER-DATASET rankings for RE2-OB and RE2-TT.
- Candidate-row completeness, duplicate-candidate absence, score/ranking
  consistency, and deterministic ordering are therefore unverifiable for that
  result.

### Non-fatal observations

- The repository test suite is healthy, but tests cannot reconstruct missing
  scientific evidence.
- The raw telemetry audit, external-test limitation, tree-ranker availability,
  and fingerprint risk were not reached; they are not used to justify the
  terminal decision.

The validate-mode fallacy scan covered 11/11 categories. Simpson's paradox,
ecological fallacy, Berkson selection, collider bias, base-rate neglect,
regression to the mean, and reverse causality cannot be assessed from Gate 0
inventory alone and are not claimed absent. Case attrition/survivorship is not
observed in the frozen row counts, but candidate-ranking attrition is the fatal
finding. Look-elsewhere and garden-of-forking-path risks remain relevant to the
legacy optimization study and are not converted into confirmatory evidence.
No causal interpretation is permitted from ranking accuracy, addressing the
correlation-versus-causation category.

## R. Final Decision

`RCA_EVIDENCE_NOT_CLOSED`

No `docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md`,
`docs/RCA_THESIS_RESULTS_PACKAGE.md`, or
`docs/RCA_THESIS_CLAIM_MATRIX.md` is generated.
