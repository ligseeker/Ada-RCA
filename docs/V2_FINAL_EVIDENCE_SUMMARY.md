# Ada-RCA V2 Final Evidence Summary

Status: **F1 NO-GO - STOPPED FOR HUMAN REVIEW**
Date: 2026-08-29

## Selection disclosure

V2 uses a previously inspected 180-case corpus and therefore cannot provide
untouched or independent confirmation. It is a separate exploratory line and
does not modify V1, reopen P3/P4, or provide unseen-root, unseen-fault,
cross-system, causal, universal, or state-of-the-art evidence.

## Stage outcomes

| Stage | Outcome | Consequence |
|---|---|---|
| Protocol | Frozen before V2 performance | Hypotheses, features, folds, bootstrap, gates, and stops fixed |
| G0 V1 replay | INTEGRITY_VALID | V2 allowed to proceed |
| F0 modality audit | DESCRIPTIVE_ONLY | No modality/pair selection authorized |
| F1 concordance | NO_GO | F2 and F3 not authorized |
| F2 reliability gate | NOT RUN | Blocked by F1 NO-GO |
| F3 interaction | NOT RUN | Blocked by F1 NO-GO |

## V1 integrity

V1 replay has exact ranking identity and zero score error against committed
P4-A2 persisted predictions, complete candidate/root coverage, exact folds,
valid checksums, and frozen metrics:

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| RE2-OB | 0.877778 | 0.988889 | 0.988889 | 0.962222 | 0.931481 |
| RE2-TT | 0.711111 | 0.866667 | 0.933333 | 0.851111 | 0.803472 |

## F0 evidence

The complete 30-row metric table and case-level audit are in
`docs/V2_F0_MODALITY_AUDIT.md` and `artifacts/v2/f0_modality_audit/`.

- Metric is fully available and carries most standalone ranking performance.
- Trace-error availability/coverage is zero on both datasets; removing it
  changes no root rank.
- Log and trace-latency are sparse and weak alone, but produce heterogeneous
  corrections and degradations on individual cases.
- Single-modality rank disagreement is substantial, especially on TT, but is
  confounded by availability, canonical ties, and candidate-universe size.
- F0 does not establish useful complementarity and did not select F1 pairs.

## F1 evidence

| Dataset | Method | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---|---:|---:|---:|---:|---:|
| RE2-OB | Z2 | 0.877778 | 0.988889 | 0.988889 | 0.962222 | 0.931481 |
| RE2-OB | F1-ALIGNED | 0.877778 | 0.988889 | 0.988889 | 0.962222 | 0.931481 |
| RE2-OB | F1-MISALIGNED | 0.855556 | 0.966667 | 0.988889 | 0.946667 | 0.912698 |
| RE2-TT | Z2 | 0.711111 | 0.866667 | 0.933333 | 0.851111 | 0.803472 |
| RE2-TT | F1-ALIGNED | 0.700000 | 0.855556 | 0.933333 | 0.837778 | 0.791105 |
| RE2-TT | F1-MISALIGNED | 0.722222 | 0.877778 | 0.933333 | 0.851111 | 0.807927 |

For aligned minus Z2, equal-dataset Delta Avg@5 is `-0.006667` with 95% CI
`[-0.014444, 0.000000]`. For aligned minus misaligned it is `+0.001111` with
95% CI `[-0.017778, 0.021111]`. TT point direction is negative in both
comparisons. Both AC@1 guards pass, including the exact TT `-1/90` boundary.

`PERFORMANCE_GO = false`, `MECHANISM_GO = false`, and `V2_F1 = NO_GO`.

## Positive, negative, null, and heterogeneous evidence

- **Positive:** aligned exceeds misaligned on OB Avg@5 by `+0.015556`.
- **Negative:** aligned degrades TT Avg@5 by `-0.013333` relative to both Z2
  and misaligned.
- **Null:** aligned and Z2 have identical rankings and metrics on all OB cases;
  AC@5 deltas are zero in the primary comparison on both datasets.
- **Heterogeneous:** misalignment direction reverses across OB and TT; TT fault
  directions are mixed; equal-dataset CIs include zero.

The positive OB control difference cannot be promoted into a concordance
mechanism claim because the preregistered TT and equal-dataset mechanism checks
fail.

## Deviations

Two audit-only numerical corrections are fully disclosed in
`docs/V2_PROTOCOL_DEVIATIONS.md`: the F0 fresh-fit score guard correction and
the F1 AC@1 exact rational-boundary correction. Neither changed a feature,
model, prediction, metric, bootstrap sample, or stage decision; no affected fit
or bootstrap was rerun.

## Scientific conclusion

**FACT:** the low-capacity aligned XC30 representation did not improve Z2
consistently and failed deliberate misalignment falsification across datasets.

**INFERENCE:** under the frozen representation and previously inspected
RE2-OB/TT corpus, there is no evidence that this definition of same-service
cross-modal temporal concordance supplies stable incremental RCA information.

**NOT SUPPORTED:** cross-modal concordance attribution, reliability-aware
gating, nonlinear expert interaction, Transformer/GNN escalation, causal RCA,
independent confirmation, or generalization beyond the evaluated known-root x
known-fault new-repetition setting.

**STOPPED FOR HUMAN REVIEW**
