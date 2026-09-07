# RCAEval BARO Final Comparison Integration Amendment V1

Status: **FROZEN — PERFORMANCE-INDEPENDENT SCOPE COMPLETENESS AMENDMENT**  
Date: 2026-09-07  
Scope: **final thesis-facing composite comparison only**

This amendment restores the already completed BARO evidence to the final
RCAEval baseline comparison. It does not authorize a baseline rerun, method
development, adapter search, parameter change, rescue execution, or any change
to Ada-RCA or the pinned RCAEval checkout.

## Motivation

BARO was part of the original RCAEval confirmatory baseline registry. It
completed the V1 execution track for both frozen datasets and its label-free
method prediction lock is already frozen. The V2 rescue protocol did not rerun
BARO because BARO had already completed, not because BARO was scientifically
excluded.

The V2 rescue scope was limited to the other baselines that had not yet closed
their execution evidence. CausalRCA was subsequently restored as an additive
V2 CPU extension under an explicit combined-lock amendment. This amendment
therefore restores BARO into the final thesis-facing comparative baseline set
as a **scope completeness decision**, made independently of BARO performance.

## Scope

The final baseline set and stable reporting order are:

```text
BARO
CIRCA
MicroCause
MicroRank
TraceRCA
mmBARO
CausalRCA
```

Ada-RCA remains the user method and is reported as a separate final comparison
row. It is not counted as a baseline.

The evaluation universe remains exactly 90 cases for each of `RE2-OB` and
`RE2-TT`. The datasets remain separate and are never pooled.

## Chronology and provenance disclosure

The six-method V2 evaluation already exists and remains byte-immutable. BARO's
prediction evidence was frozen earlier on the V1 execution track, while
CIRCA, MicroCause, MicroRank, TraceRCA, and mmBARO were closed on the V2 rescue
track and CausalRCA was closed on the V2 CPU additive-extension track.

Accordingly, the final result is explicitly named
`FINAL_COMPOSITE_SEVEN_BASELINE_COMPARISON`. It must not be described as
`SEVEN_METHOD_ORIGINAL_PRELABEL_GLOBAL_LOCK`: the seven baselines were not
simultaneously frozen under one original pre-label global lock. BARO's own
prediction was label-free and frozen before this integration, and this scope
decision was frozen before any new BARO performance evaluation. The existing
six-method performance was not used to decide whether BARO belongs in scope.

The machine-readable scope lock at
`artifacts/baseline_eval/final_comparison_v3/scope_lock_v3.json` binds the BARO
V1 method lock, the combined six-method V2 global lock, the frozen input
manifest, the pinned RCAEval commit, the immutable Ada-RCA identity, and this
amendment. It is a scope/evidence lock, not a new prediction lock.

## Evaluation and reporting rules

After the committed scope lock, BARO may be evaluated only from its existing
frozen case records and method lock. The final comparison uses the already
frozen V2 six-method JSON values by exact identity, and uses the frozen Ada-RCA
metrics by exact identity. BARO contributes `AC@1`, `AC@3`, `AC@5`, and
`Avg@5` separately for each dataset and fault stratum. BARO MRR remains
`NOT-IDENTIFIABLE`; no candidate completion or ranking reconstruction is
legal.

The final robustness table includes evidence-track labels rather than
claiming identical execution generations. The final comparability table
retains the material distinction between Ada-RCA's supervised cross-case
complete service ranking and the RCAEval baselines' mostly case-wise
unsupervised partial service projections.

Paired fault-stratified bootstrap uses the frozen design of 10,000 resamples
with seed `20260827`, analyzes `RE2-OB` and `RE2-TT` separately, and adds only
the newly evaluated BARO rows. Existing six-method bootstrap rows are copied
and identity-checked from the immutable V2 artifact.

## No rerun and immutability

- BARO is not rerun.
- CIRCA, MicroCause, MicroRank, TraceRCA, mmBARO, and CausalRCA are not rerun.
- Ada-RCA is not retrained or recomputed.
- The pinned RCAEval source is not modified.
- BARO prediction records and its prediction lock are not modified.
- The combined six-method V2 prediction lock and all V2 evaluation JSON files
  are not modified.
- Historical V1/V2 protocols and the historical six-method V2 report retain
  their original wording and provenance.

## Claim boundary

The composite comparison supports a comparison under the frozen case
universes and legally aligned top-k service-projection metrics. It does not
support an SOTA, universally superior, same-protocol superiority, causal
superiority, unseen-system generalization, or unseen-root generalization
claim. Execution generations and supervision/output completeness remain
materially different and must be stated with the results.
