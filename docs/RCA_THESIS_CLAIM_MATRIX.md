# Ada-RCA Thesis Claim Matrix

Status: **CANONICAL THESIS CLAIM BOUNDARY**

This matrix is the authoritative Gate 5 mapping from claim text to evidence.
`SUPPORTED` means the exact bounded claim has direct immutable evidence;
`CONDITIONALLY SUPPORTED` means the stated result is usable only with the
listed dataset, protocol, comparator, and development/post-selection
qualification. `NOT SUPPORTED` and `NOT TESTED` must not be rewritten as weak
positive claims.

| Claim | Status | Evidence Class | Exact Comparator | Evidence Artifact | Limitation |
|---|---|---|---|---|---|
| 1. Ada-RCA performs service-level root-cause ranking on RE2-OB and RE2-TT. | SUPPORTED | FROZEN-SCIENTIFIC | V1 true-root rank within the fixed 11-service OB and 68-service TT candidate registries, 90 cases per dataset | `artifacts/evidence_closure/metric_reconstruction_v1_1.json`; `artifacts/final_method/{re2ob,re2tt}/predictions.jsonl` | Confirmed failure-event, known-system, known candidate universe; this is ranking, not causal discovery. |
| 2. V1 results are independently reproducible from frozen predictions/rankings. | SUPPORTED | FROZEN-SCIENTIFIC | Independent root-rank formulas versus committed V1 metrics for AC@1/3/5, Avg@5, and MRR | `artifacts/evidence_closure/metric_reconstruction_v1_1.json`; `docs/INDEPENDENT_METRIC_RECONSTRUCTION_V1_1.md` | Reproduces the frozen result; it is not a new external experiment. |
| 3. GLOBAL optimization improves V1. | NOT SUPPORTED | FROZEN-SCIENTIFIC | GLOBAL-OPT minus V1 on both datasets | `artifacts/evidence_closure/bootstrap_corrected_v1_1.json`; `artifacts/evidence_closure/metric_reconstruction_v1_1.json` | Predictions are byte-identical and every point delta and CI is exactly zero. |
| 4. PER-DATASET optimization improves Avg@5 consistently across datasets. | NOT SUPPORTED | DEVELOPMENT-NESTED-OOF | PER-DATASET-OPT minus V1 Avg@5 on OB and TT | `artifacts/evidence_closure/bootstrap_corrected_v1_1.json` | OB point delta is negative; TT is positive but its CI crosses zero. PER-DATASET full-ranking integrity is not auditable. |
| 5. PER-DATASET optimization improves TT AC@1. | CONDITIONALLY SUPPORTED | DEVELOPMENT-NESTED-OOF | PER-DATASET-OPT minus V1 on TT AC@1 | `artifacts/evidence_closure/bootstrap_corrected_v1_1.json`; `artifacts/evidence_closure/metric_reconstruction_v1_1.json` | Frozen root ranks show a dataset-specific positive signal; the percentile CI touches zero, benchmarks are reused, and complete PER-DATASET rankings are unavailable. |
| 6. Multimodal observability information contributes useful ranking evidence. | CONDITIONALLY SUPPORTED | DEVELOPMENT-NESTED-OOF | OB: FULL-Z2 versus Z1-M; TT: M+TL versus Z1-M, at the representation-screen lambda within each outer-train split | `artifacts/opt/o4_nested/{re2ob,re2tt}/selection_trace.json`; `docs/OPT_SEARCH_SPACE_FREEZE_V1.md` | Applies only to these exact frozen combinations and inner development comparisons; it does not isolate every modality or establish universal multimodal benefit. |
| 7. Trace Error contributes candidate-discriminative information under the frozen Z2 representation. | NOT SUPPORTED | AUDIT-DERIVED-LIMITATION | Frozen 17D Trace Error block versus the same matrices with that block omitted algebraically | `artifacts/evidence_closure/trace_error_representation_invariant.json` | Every row has the same TE vector and no case has within-case candidate variation; no replacement representation was tested. |
| 8. Trace Latency contributes useful ranking information. | CONDITIONALLY SUPPORTED | DEVELOPMENT-NESTED-OOF | TT M+TL versus M+TE, with M+TE exactly equivalent to Z1-M in the frozen screens | `artifacts/opt/o4_nested/re2tt/selection_trace.json`; `artifacts/evidence_closure/trace_error_representation_invariant.json` | TT inner screens favor the exact M+TL combination in all three outer folds; this is not an isolated outer-test TL ablation or a cross-dataset universal claim. |
| 9. FULL-Z2 is universally optimal. | NOT SUPPORTED | DEVELOPMENT-NESTED-OOF | FULL-Z2 versus all screened representations by outer fold and dataset | `artifacts/opt/o4_nested/{re2ob,re2tt}/selection_trace.json`; `docs/OPT_NESTED_SELECTION_RESULTS.md` | TT selects M+TL in all three outer folds; the searched family is small and fixed. |
| 10. Event-relative representation is empirically useful. | CONDITIONALLY SUPPORTED | DEVELOPMENT-NESTED-OOF | Z3 versus Z3-SHUFFLE, which preserves values/masks but destroys aligned temporal positions | `artifacts/bootstrap/p3_g1_bootstrap.json`; `docs/P3_G1_DECISION.md` | Supports aligned temporal organization relative to this deterministic shuffle only; P3-G1 still fails the Z3-versus-Z1 cross-dataset gate. |
| 11. Stage-aware representation is superior. | NOT TESTED | NOT-TESTED | None; no stage-aware representation appears in the frozen search space | `docs/OPT_SEARCH_SPACE_FREEZE_V1.md` | No executed comparator exists. |
| 12. Candidate-relative representation is superior. | NOT SUPPORTED | DEVELOPMENT-NESTED-OOF | P4 A1 (Z1-REL) versus A0 (Z1-ABS) on both datasets | `artifacts/p4_g0/bootstrap/p4_g0_bootstrap.json`; `docs/P4_G0_DECISION.md` | TT is positive but OB is negative and the preregistered cross-dataset consistency condition fails. |
| 13. Topology propagation improves RCA. | NOT TESTED | NOT-TESTED | None; no topology method was executed | `docs/OPT_SEARCH_SPACE_FREEZE_V1.md`; `docs/OPT_FINAL_DECISION.md` | Topology/GNN work is outside the frozen executed scope. |
| 14. Timing/order modeling improves RCA. | NOT TESTED | NOT-TESTED | None; no dedicated timing/order model was executed | `docs/OPT_SEARCH_SPACE_FREEZE_V1.md`; `docs/P3_G1_DECISION.md` | Temporal alignment versus shuffle was tested under claim 10, but a timing/order model was not. |
| 15. Ada-RCA performs causal root-cause discovery. | NOT SUPPORTED | AUDIT-DERIVED-LIMITATION | Service-ranking predictions versus labelled roots in observational benchmark events; no causal intervention comparator | `docs/RCA_FINAL_METHOD_FREEZE_V1.0.md`; `docs/P4_CONTEXT_DIAGNOSTIC_LIMITATION.md` | Ranking association and a descriptive foreign-context diagnostic do not establish causality. |
| 16. Ada-RCA generalizes to unseen systems. | NOT TESTED | NOT-TESTED | None; evaluation is limited to RE2-OB and RE2-TT | `artifacts/evidence_closure/metric_reconstruction_v1_1.json`; `docs/FINAL_EVIDENCE_SUMMARY.md` | No untouched cross-system dataset was evaluated. |
| 17. Ada-RCA generalizes to unseen roots. | NOT SUPPORTED | POST-HOC-DIAGNOSTIC | P4 LOSO diagnostics across held-out roots within the same benchmark systems | `artifacts/p4_g0/loso/{re2ob,re2tt}.json`; `docs/P4_G0_DECISION.md` | Root-macro direction is positive but per-root effects are heterogeneous; this is not an untouched unseen-root evaluation. |
| 18. Results constitute untouched external confirmation. | NOT SUPPORTED | AUDIT-DERIVED-LIMITATION | Frozen V1/P3/P4 results versus an untouched external test set | `docs/FINAL_EVIDENCE_SUMMARY.md`; `docs/FINAL_METHOD_DECISION.md` | P3, P4, final synthesis, and optimization reuse the same development benchmarks; no external test exists. |
| 19. Ada-RCA is SOTA. | NOT SUPPORTED | AUDIT-DERIVED-LIMITATION | Ada-RCA versus same-protocol, independently reproduced external baselines | `docs/BASELINE_COMPATIBILITY_MATRIX.md`; `docs/FINAL_EVIDENCE_SUMMARY.md` | No compatible head-to-head baseline evidence supports a SOTA claim. |
| 20. XGBoost ranker performs worse than Conditional Logit. | NOT TESTED | NOT-TESTED | None; XGBoost ranker was not executed | `artifacts/evidence_closure/provenance_normalization_v1_1.json` | Dependency unavailable is not a negative performance result. |
| 21. LightGBM ranker performs worse than Conditional Logit. | NOT TESTED | NOT-TESTED | None; LightGBM ranker was not executed | `artifacts/evidence_closure/provenance_normalization_v1_1.json` | Dependency unavailable is not a negative performance result. |
| 22. Current robust scaling can lose zero-baseline sparse Trace Error emergence signals. | SUPPORTED | POST-HOC-DIAGNOSTIC | RE2-OB pre-all-zero/post-positive TE pairs versus frozen MAD/IQR scale-valid rule | `artifacts/evidence_closure/telemetry_information_loss_v1_1.json`; `docs/TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md` | The mechanism is observed for 30 OB candidate-case pairs; it does not show that a sparse-aware replacement improves ranking. |
| 23. There is no label leakage. | NOT SUPPORTED | AUDIT-DERIVED-LIMITATION | Absolute absence claim versus the bounded label-firewall, split, and shortcut checks | `artifacts/opt/diagnostics/shortcut_audit.json`; `docs/EVIDENCE_ERRATA.md` | Bounded checks cannot prove absence of all shortcuts; service/telemetry fingerprint risk remains. |
| 24. No explicit root/fault leakage was detected. | SUPPORTED | FROZEN-SCIENTIFIC | Predictive feature/input path and nested split/scaler scope versus explicit root/fault fields | `artifacts/opt/diagnostics/shortcut_audit.json`; `tests/test_label_firewall.py`; `tests/test_p4_label_firewall.py` | Supports only `NO_EXPLICIT_LABEL_LEAKAGE_DETECTED`; it does not exclude indirect service or telemetry fingerprints. |

## Status counts

| Status | Count |
|---|---:|
| SUPPORTED | 4 |
| CONDITIONALLY SUPPORTED | 4 |
| NOT SUPPORTED | 10 |
| NOT TESTED | 6 |

## Thesis wording boundary

The thesis may state the four supported claims exactly as bounded above and may
use the four conditional claims only with their comparator and limitation in
the same passage. It must not convert a dataset-specific signal, an inner
development comparison, a diagnostic, missing execution, or a failed
cross-dataset gate into a general positive conclusion.
