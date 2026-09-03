# Ada-RCA Thesis Results Package

Canonical freeze state: `RCA_FREEZE_READY_WITH_LIMITATION`.

This is the thesis-facing results entrypoint. It packages only evidence that is
traceable to frozen artifacts and preserves the distinction between scientific
results, development evidence, post-hoc diagnostics, limitations, and methods
that were not tested. The complete claim boundary is in
`docs/RCA_THESIS_CLAIM_MATRIX.md`.

# 1. Task

Ada-RCA addresses service-level root-cause ranking for a confirmed failure
event. Given prediction-visible Metrics, Logs, Trace Error, Trace Latency, and a
fixed candidate-service registry, it ranks the legal candidate services. This
is supervised service ranking, not failure detection or causal discovery.

The frozen V1 task contains 90 RE2-OB cases with 11 candidates per case and 90
RE2-TT cases with 68 candidates per case. Source:
`artifacts/evidence_closure/metric_reconstruction_v1_1.json`.

# 2. Protocol

V1 uses the frozen 68-dimensional Z2 representation: four telemetry channels,
each containing eight base and nine morphology fields. It uses event-level
Conditional Logit with train-fold-only standardization and L2 lambda `1.0`.
The two datasets are evaluated separately with three frozen folds. Sources:
`src/rca/final_method.py`, `artifacts/final_method/re2ob/replay_audit.json`, and
`artifacts/final_method/re2tt/replay_audit.json`.

Protocol Amendment V1.1 is disclosed as a post-audit clarification. It
separates complete-ranking integrity from root-rank metric sufficiency; it does
not recreate missing PER-DATASET rankings. Sources:
`docs/RCA_EVIDENCE_CLOSURE_PROTOCOL_AMENDMENT_V1_1.md` and
`artifacts/evidence_closure/evidence_semantic_correction_v1_1.json`.

# 3. Main V1 results

Canonical numeric source:
`artifacts/evidence_closure/metric_reconstruction_v1_1.json`.

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |

Both V1 datasets have `FULL_RANKING_INTEGRITY_PASS` and
`RANK_METRIC_SUFFICIENT_PASS`. The metrics were independently reconstructed
from complete frozen rankings and match the committed V1 metrics. This supports
performance statements only within the frozen datasets, task, candidate
registries, folds, and protocol.

# 4. Major ablations and negative results

## 4.1 Event-relative morphology trajectory gate

The preregistered P3 comparison did not support Z3 over Z1 consistently across
datasets and closed with `P3-G1 = NO-GO`. The deterministic shuffle comparison
does support the narrower interpretation that aligned temporal organization
contained ranking evidence relative to that exact control. Canonical numeric
source: `artifacts/bootstrap/p3_g1_bootstrap.json`.

| Avg@5 comparison | RE2-OB point [95% CI] | RE2-TT point [95% CI] | Equal-dataset mean point [95% CI] |
|---|---|---|---|
| Z3 - Z1 | +0.013333 [-0.013333, +0.042222] | -0.055556 [-0.157778, +0.046667] | -0.021111 [-0.074444, +0.031111] |
| Z3 - Z3-SHUFFLE | +0.184444 [+0.124444, +0.246667] | +0.262222 [+0.157778, +0.364444] | +0.223333 [+0.163333, +0.283333] |

## 4.2 Candidate-relative representation gate

The preregistered P4 A1-A0 comparison improved TT but was negative on OB, so
the required cross-dataset condition failed and `P4-G0 = NO-GO`. Canonical
numeric source: `artifacts/p4_g0/bootstrap/p4_g0_bootstrap.json`.

| Avg@5 comparison | RE2-OB point [95% CI] | RE2-TT point [95% CI] | Equal-dataset mean point [95% CI] |
|---|---|---|---|
| A1 - A0 | -0.004444 [-0.024444, +0.017778] | +0.066667 [+0.011111, +0.124444] | +0.031111 [+0.001111, +0.062222] |

The positive pooled interval does not override the preregistered requirement
that both dataset point effects be positive. Neither P3 nor P4 constitutes
untouched external confirmation.

## 4.3 Trace Error frozen block

The frozen Trace Error block is not candidate-discriminative in either dataset.
Its exact invariant is reported in Section 8. This is a representation audit,
not a new ablation, model fit, or sparse-feature experiment.

# 5. Optimization post-study

Canonical numeric source:
`artifacts/evidence_closure/metric_reconstruction_v1_1.json`.

| Track | Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---|---:|---:|---:|---:|---:|
| GLOBAL-OPT | RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| GLOBAL-OPT | RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |
| PER-DATASET-OPT | RE2-OB | 0.8555555556 | 0.9777777778 | 0.9888888889 | 0.9511111111 | 0.9157407407 |
| PER-DATASET-OPT | RE2-TT | 0.7888888889 | 0.8555555556 | 0.9000000000 | 0.8577777778 | 0.8392494434 |

GLOBAL-OPT predictions are byte-identical to V1. PER-DATASET-OPT retains
`RANK_METRIC_SUFFICIENT_PASS` but permanently has
`FULL_RANKING_INTEGRITY_NOT_AUDITABLE`, because complete candidate scores and
rankings were not frozen. Source:
`artifacts/evidence_closure/metric_reconstruction_v1_1.json`.

The executed optimization scope is Conditional Logit, six frozen
representation combinations, and lambda grid `{0.1, 1.0, 10.0}`. XGBoost and
LightGBM are `NOT EXECUTED — DEPENDENCY UNAVAILABLE`; they are not negative
performance results. Source:
`artifacts/evidence_closure/provenance_normalization_v1_1.json`.

# 6. Corrected paired bootstrap

The canonical direction is `Delta = Candidate - V1`. The frozen estimator uses
10,000 paired fault-stratified case resamples with seed `20260829`. Canonical
numeric source: `artifacts/evidence_closure/bootstrap_corrected_v1_1.json`.

| Candidate | Dataset | Metric | Point | Corrected 95% CI |
|---|---|---|---:|---:|
| GLOBAL-OPT | RE2-OB | Avg@5 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-OB | AC@1 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-OB | MRR | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-TT | Avg@5 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-TT | AC@1 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| GLOBAL-OPT | RE2-TT | MRR | 0.0000000000 | [0.0000000000, 0.0000000000] |
| PER-DATASET-OPT | RE2-OB | Avg@5 | -0.0111111111 | [-0.0266666667, 0.0000000000] |
| PER-DATASET-OPT | RE2-OB | AC@1 | -0.0222222222 | [-0.0555555556, 0.0000000000] |
| PER-DATASET-OPT | RE2-OB | MRR | -0.0157407407 | [-0.0379629630, 0.0000000000] |
| PER-DATASET-OPT | RE2-TT | Avg@5 | +0.0066666667 | [-0.0333333333, +0.0466666667] |
| PER-DATASET-OPT | RE2-TT | AC@1 | +0.0777777778 | [0.0000000000, +0.1555555556] |
| PER-DATASET-OPT | RE2-TT | MRR | +0.0357775552 | [-0.0132650477, +0.0870892761] |

The corrected result is `NO_CLEAR_OPTIMIZATION_GAIN`: there is no shared gain
and no consistent cross-dataset Avg@5 improvement. The TT AC@1 result is a
dataset-specific positive signal; its interval touches zero. The legacy
bootstrap intervals are superseded and must not be used as thesis evidence.

# 7. Telemetry information loss

Canonical numeric source:
`artifacts/evidence_closure/telemetry_information_loss_v1_1.json`.

| Dataset | Modality | Eligible | Mapped | Scale valid | Feature active |
|---|---|---:|---:|---:|---:|
| RE2-OB | Metric | 990 | 990 | 990 | 990 |
| RE2-OB | Log | 990 | 812 | 807 | 807 |
| RE2-OB | Trace Error | 990 | 900 | 0 | 0 |
| RE2-OB | Trace Latency | 990 | 900 | 374 | 374 |
| RE2-TT | Metric | 6,120 | 6,120 | 6,120 | 6,120 |
| RE2-TT | Log | 6,120 | 1,787 | 1,707 | 1,707 |
| RE2-TT | Trace Error | 6,120 | 2,347 | 0 | 0 |
| RE2-TT | Trace Latency | 6,120 | 2,347 | 847 | 847 |

For RE2-OB, 30 candidate-case pairs have an all-zero/constant pre-event Trace
Error baseline and a positive post-event signal, and all 30 are rejected by
the frozen scale rule. This directly establishes an information-loss
mechanism. It does not establish that a sparse-aware replacement improves RCA.
Source: `artifacts/evidence_closure/telemetry_information_loss_v1_1.json`.

# 8. Trace Error representation invariant

Canonical numeric source:
`artifacts/evidence_closure/trace_error_representation_invariant.json`.

| Dataset | Candidate-case rows | All-zero rows | Nonzero rows | Unique vectors | Nonzero-variance dimensions | Discriminative cases |
|---|---:|---:|---:|---:|---:|---:|
| RE2-OB | 990 | 0 | 990 | 1 | 0 | 0 / 90 |
| RE2-TT | 6,120 | 0 | 6,120 | 1 | 0 | 0 / 90 |

Every frozen 17D TE vector is
`[0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0]`: only
`base.onset_missing` is nonzero. Therefore the block is globally nonzero but
has no across-case or within-case candidate variation. Removing it changes raw
feature vectors only by a constant-across-candidate block and cannot change
within-case Conditional Logit utility differences.

Final classification:
`TRACE_ERROR_EFFECTIVELY_NONDISCRIMINATIVE_IN_FROZEN_Z2`.

# 9. Limitations

- Scientific: the protocol amendment is post-audit; development benchmarks
  were reused; there is no untouched external test or causal design.
- Provenance: PER-DATASET full rankings are unavailable; raw-record to
  derived-cell lineage is not fully auditable; recovered historical evidence
  is protocol-incompatible as a comparator.
- Statistical: corrected intervals condition on fixed frozen root ranks and do
  not include search, benchmark reuse, system sampling, or method-development
  uncertainty.
- Dataset: only the known RE2-OB and RE2-TT systems and fixed candidate
  registries are covered; unseen-system and unseen-root claims are unavailable.
- Leakage/shortcut: no explicit root/fault leakage was detected, but stable
  service-specific coverage, availability, or telemetry fingerprints may
  remain.
- Scope: tree rankers and topology, stage-aware, dedicated timing/order,
  neural, ensemble, and sparse-aware replacement methods were not executed.
- Representation: frozen robust scaling removes candidate-discriminative Trace
  Error content and loses the documented RE2-OB emergence signals.

Canonical limitation sources:
`artifacts/evidence_closure/final_decision_v1_1.json`,
`artifacts/evidence_closure/evidence_semantic_correction_v1_1.json`,
`artifacts/evidence_closure/telemetry_information_loss_v1_1.json`, and
`artifacts/evidence_closure/trace_error_representation_invariant.json`.

# 10. Claim-safe thesis wording

Safe main-result wording:

> Under the frozen three-fold protocol on RE2-OB and RE2-TT, Ada-RCA V1
> reproduced the service-ranking metrics reported in Section 3 from complete
> frozen rankings.

Safe optimization wording:

> GLOBAL-OPT was prediction-identical to V1. PER-DATASET-OPT produced a
> TT-specific AC@1 signal, but did not establish a consistent cross-dataset
> Avg@5 gain; its complete candidate rankings were not frozen.

Safe telemetry wording:

> The frozen pipeline accepts Trace Error input, but its robust-scale path made
> the final TE block candidate-nondiscriminative in both audited datasets and
> lost a documented class of zero-baseline/post-positive RE2-OB signals.

Safe leakage wording:

> The bounded audits detected no explicit root/fault leakage; indirect
> service/telemetry fingerprint risk remains.

Do not claim SOTA, causal discovery, unseen-system or unseen-root
generalization, untouched external confirmation, universal representation
superiority, tree-ranker inferiority, or absolute absence of leakage. Exact
statuses and comparators: `docs/RCA_THESIS_CLAIM_MATRIX.md`.

# Freeze boundary

No further Ada-RCA performance search is included in this scientific freeze.
Future work is not current evidence.
