# P4-G0 Results

Status: COMPLETE; results are from polished deterministic fits. P3-G1 remains
`NO-GO / CLOSED`. This report is limited to RE2-OB and RE2-TT and does not
claim universal or unseen-root generalization.

## Frozen design

Z1 has 32 dimensions; Z1-REL (A1) has 64. Z2 has 68 dimensions; Z2-REL (A3)
has 136. Percentiles are feature-wise within-event ascending average ranks,
scaled by `N-1`, computed before train-fold-only scaling. The scorer is the
event-level conditional logit with L2 lambda 1.0, zero initialization, SciPy
L-BFGS-B and deterministic Newton polishing to gradient infinity norm `<=1e-8`.
The split is the frozen three-fold repetition OOF assignment. Bootstrap uses
10,000 paired fault-stratified case resamples with seed 20260826.

## RE2-OB

| Variant | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| A0 (Z1-ABS) | 0.855556 | 0.988889 | 1.000000 | 0.951111 | 0.913333 |
| A1 (Z1-REL) | 0.866667 | 0.955556 | 0.988889 | 0.946667 | 0.917328 |
| A2 (Z2-ABS) | 0.877778 | 0.988889 | 0.988889 | 0.962222 | 0.931481 |
| A3 (Z2-REL) | 0.844444 | 0.977778 | 0.988889 | 0.948889 | 0.909921 |

Effects: A1-A0 Avg@5 `-0.004444`, AC@1 `+0.011111`; A3-A2 Avg@5
`-0.013333`, AC@1 `-0.033333`; A2-A0 Avg@5 `+0.011111`; A3-A1 Avg@5
`+0.002222`; interaction Avg@5 `-0.008889`.

## RE2-TT

| Variant | AC@1 | AC@3 | AC@5 | Avg@5 | MRR |
|---|---:|---:|---:|---:|---:|
| A0 (Z1-ABS) | 0.577778 | 0.800000 | 0.866667 | 0.764444 | 0.708019 |
| A1 (Z1-REL) | 0.677778 | 0.866667 | 0.922222 | 0.831111 | 0.778886 |
| A2 (Z2-ABS) | 0.711111 | 0.866667 | 0.933333 | 0.851111 | 0.803472 |
| A3 (Z2-REL) | 0.711111 | 0.888889 | 0.922222 | 0.855556 | 0.807694 |

Effects: A1-A0 Avg@5 `+0.066667`, AC@1 `+0.100000`; A3-A2 Avg@5
`+0.004444`, AC@1 `0`; A2-A0 Avg@5 `+0.086667`; A3-A1 Avg@5
`+0.024444`; interaction Avg@5 `-0.062222`.

## Primary bootstrap and integrity

For A1-A0 Avg@5, OB delta is `-0.004444` with 95% CI
`[-0.024444, +0.017778]`; TT delta is `+0.066667` with CI
`[+0.011111, +0.124444]`; the two-dataset mean is `+0.031111` with CI
`[+0.001111, +0.062222]`. AC@1 deltas are `+0.011111` (OB) and `+0.100000`
(TT), both above the `-0.01` guardrail.

All 720 formal case rankings are complete, unique, root-containing, and metric-
recomputable. All eight polished runs have finite inputs, valid checksums,
converged fits, and final gradient infinity norm at or below `1e-8`. Candidate
permutation tests and foreign normal-context replay equality passed.

## Secondary diagnostics

LOSO root-macro A1-A0 Avg@5 is `+0.008889` (OB) and `+0.037778` (TT), but
per-root effects are heterogeneous. Foreign-context normal-minus-foreign
Avg@5 is `+0.004444` (OB) and `+0.017778` (TT), giving
`CONTEXT_DEPENDENCE_OBSERVED` under the pre-specified descriptive rule; this is
not causal proof. Full MI, fault, root, fold, transition, LOSO, and context
outputs are under `artifacts/p4_g0/`.

## Gate status

Condition 1 (OB Avg@5 delta > 0): **FAIL**. Condition 2 (TT > 0): **PASS**.
Condition 3 (mean >= +0.01): **PASS**. Condition 4 (AC@1 guardrails):
**PASS**. Condition 5 (mean bootstrap CI lower > 0): **PASS**. Integrity:
**PASS**. The frozen cross-dataset condition fails, so P4-G0 is NO-GO.
