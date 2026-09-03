# O0 V1 Baseline Integrity

Status: `PASS / INTEGRITY_VALID`

The optimization baseline is the frozen V1-SCIENTIFIC method: 68D Z2
event-relative multimodal representation, event-level conditional-logit ranking,
lambda 1.0, train-fold-only StandardScaler, frozen three-fold OOF, and complete
legal candidate rankings.

| Dataset | Cases | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| RE2-OB | 90/90 | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 |
| RE2-TT | 90/90 | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 |

The copied canonical replay artifacts under `artifacts/opt/o0_integrity/` are
checksum-bound and reproduce the committed V1 rankings exactly. All six folds
converge, rankings are complete and root-containing, and metric recomputation
matches the frozen values. The TT MRR artifact retains the full recomputed value
`0.8034718881941106`, displayed above at the protocol precision.

An independent refit from the V1 tree produced identical rankings and metrics,
but a sub-ULP score tail difference against the older committed P4-A2 arrays
(maximum `1.2008172234345693e-12` on TT) because the V1 tree contains a later
floating-point polishing correction. This does not alter ranking, case metrics,
or persisted-state replay; no V1 logic was changed to obtain this record.

Checks covered: 90 cases per dataset, 60/30 fold membership, legal candidate
counts, root mapping, label-free feature names, deterministic tie ordering,
complete rankings, exact metric recomputation, persisted model-state checksums,
and replay identity. Result classification is `V1-SCIENTIFIC`, not a new test
estimate.
