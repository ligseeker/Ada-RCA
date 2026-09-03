# RCA Evidence Errata

Status: **ACTIVE PROVENANCE AND CLAIM NORMALIZATION**

This errata preserves every legacy artifact and historical document. It does
not rewrite the past record. It defines the terminology that must be used by
active Evidence Closure and thesis-facing documents after Gate 4.

## Historical reference terminology

Legacy term: `HIST-BEST-REPLAYED-REFERENCE`

Normalized active term: `HIST-BEST-RECOVERED-REFERENCE`

Required qualifier:

> Recovered legacy result; not canonically replayed; not an unbiased comparator.

The normalization is required because the historical compatibility audit says
that no historical candidate qualifies as a direct Class A replay, and exact
byte-level canonical replay under the current V1 registry is unavailable. The
historical replay document further says the summaries were copied read-only.
The historical artifact directory contains aggregate summaries/bootstrap
records but no current-registry case-level predictions, root-rank artifact,
model-state manifest, or replay-audit bundle.

Consequently, historical C1-I/M1-S values may be reported only as post-hoc
descriptive context. They cannot be used for independent metric reconstruction,
paired bootstrap against V1, a same-protocol comparison, or method selection.

## Ranker execution semantics

| Ranker family | Canonical execution status |
|---|---|
| Conditional Logit | `EXECUTED` |
| XGBoost | `NOT EXECUTED — DEPENDENCY UNAVAILABLE` |
| LightGBM | `NOT EXECUTED — DEPENDENCY UNAVAILABLE` |

Both dataset configs mark Conditional Logit available and both tree families
unavailable. Every ranker entry in the nested selection traces is
`R0-ConditionalLogit`. No fallback tree implementation or ensemble was
substituted.

The unavailable families are not empirical negative results. Optimization
claims are limited to the actually executed Conditional-Logit representation
and lambda search; they do not compare algorithm families.

## Telemetry active-count clarification

The legacy telemetry document is retained unchanged. Its service-row table is
not a candidate-case feature-active funnel. The Gate 3 V1.1 audit establishes
that frozen Trace Error `feature_active` count is zero for both datasets; see
`docs/TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md`. No legacy count may be used to
claim that Trace Error survived the frozen robust-scale path.

## Leakage and shortcut wording

Passing the label firewall and nested split checks authorizes only:

`NO_EXPLICIT_LABEL_LEAKAGE_DETECTED`

It does not authorize a claim that all service identity, telemetry
availability, or observability fingerprints are absent. The existing shortcut
audit's service-fingerprint finding remains `ADVISORY`.
