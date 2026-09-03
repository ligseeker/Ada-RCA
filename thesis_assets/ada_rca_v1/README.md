# Ada-RCA V1 Thesis Asset Package

This directory is the single thesis-writing entry point for the frozen Ada-RCA
V1 evidence package. It contains Ada-RCA evidence only; external baseline
execution and baseline comparison are outside this package and are not included.

## Freeze identity

- source branch: `research/evidence-closure`
- source commit: `9342e06db91945be2e44703437229ba45b18bda8`
- V1 scientific reference: `bed295326e567395e725caa82840a534dcc0b1de`
- frozen optimization record: `53c9face2c96761c9114edb558eb6d8666a38dc6`
- Evidence Closure decision record: `5957b465fac7351a6c55ab799a058ef66a60f9bc`
- exporter commit: `ca5e092e021359fe10c3db543d507e8b6f49fbb9`
- terminal scientific decision: `RCA_FREEZE_READY_WITH_LIMITATION`

Ada-RCA V1 is a supervised service-level root-cause ranking pipeline for a
confirmed failure event. Its frozen method is the candidate-wise event-relative
four-channel 68D Z2 representation followed by event-level Conditional Logit
and a complete deterministic service ranking. The package does not redefine
choice-set semantics, claim variable candidate universes, or promote the
pipeline to causal discovery.

## Where to find evidence

- `raw/final_method/`: byte-identical final metrics, predictions, configs,
  provenance, checksums, replay audits, and persisted-state manifests.
- `raw/source/` and `raw/splits/`: labels, legal candidate registries, input
  metadata, and frozen fold assignments needed for independent reconstruction.
- `raw/evidence_closure/`: canonical machine-readable semantic, metric,
  bootstrap, telemetry, Trace Error, provenance, and final-decision evidence.
- `data/final/`: independently reconstructed case/root/fault/fold/overall
  metrics, rank distributions, and candidate-universe summaries.
- `data/reproducibility/`: code-derived 68D feature schema, frozen
  configuration, persisted fit diagnostics, and replay integrity.
- `data/ablation/`: P3 and P4 development evidence. P3-G1 and P4-G0 remain
  `NO-GO / CLOSED`; their bounded comparisons are not external confirmation.
- `data/controls/`: final falsification controls and the separate S3 service
  identity diagnostic. S3 is not an RCA baseline.
- `data/optimization/`: configuration robustness / frozen optimization
  post-study evidence. Corrected bootstrap uses `Candidate - V1`; the legacy
  interval artifact is not used.
- `data/telemetry/`: candidate-case modality funnel, Trace Error information
  loss, and the exact frozen 17D Trace Error invariant. The official method
  remains four-channel 68D Z2 even where the TE block is nondiscriminative.
- `data/diagnostics/`: descriptive magnitude, anchor-feasibility,
  fingerprint, failure-case, coverage, and postmortem diagnostics. Every row
  is marked `evidence_class=DIAGNOSTIC` and `confirmatory=false`.
- `tables/`: deterministic thesis candidate tables; `tables/TABLE_CATALOG.md`
  records placement and claim boundaries.
- `refs/`: complete document, source-code, source-artifact, supersession, and
  excluded-scope indexes.
- `scripts/`: deterministic exporter and fail-closed validator.

## Evidence classes and wording boundary

`CANONICAL` is the current frozen evidence layer. `SUPPORTING` records method,
protocol, control, or provenance context. `DEVELOPMENT` covers internal P3,
P4, and post-study selection evidence. `DIAGNOSTIC` records limitations and
post-hoc mechanisms without confirmatory status. `HISTORICAL_SUPERSEDED` is
retained for traceability but cannot supply canonical metrics or bootstrap
intervals. `OUT_OF_SCOPE` material is indexed as excluded and is not copied.

The supported claim boundary is the exact matrix in
`docs/canonical/RCA_THESIS_CLAIM_MATRIX.md`. Safe claims remain bounded to
RE2-OB and RE2-TT, their fixed candidate registries, frozen folds, and the
committed protocol. The package does not support SOTA, causal discovery,
unseen-system or unseen-root generalization, untouched external confirmation,
universal representation superiority, absolute no-leakage, or tree-ranker
inferiority. XGBoost and LightGBM are explicitly `NOT EXECUTED — DEPENDENCY
UNAVAILABLE`, not negative results.

`MANIFEST.csv` records byte hashes and source provenance for every package file
except the manifest index itself, which is necessarily self-referential.
`PROVENANCE.json` records the source and exporter identities without an ambient
timestamp. Re-running the exporter after the exporter commit should produce
byte-equivalent generated outputs.
