# Bootstrap Forensic Audit

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Verification Status: VERIFIED
- Version Label: bootstrap_forensic_audit_v1_1
- Scientific input: immutable `case_id`, `fault_type`, and `root_rank`
- Machine-readable result:
  `artifacts/evidence_closure/bootstrap_corrected_v1_1.json`

## Gate result

`GATE_2_PASS — GATE_3_AUTHORIZED`

The corrected audit uses `Delta = Candidate - V1`, failure cases as the
sampling unit, 10,000 paired resamples, seed `20260829`, and replacement within
each of the six 15-case fault strata. Candidate and V1 use exactly the same
sampled case IDs in every iteration. No complete candidate ranking, score,
feature, model fit, or optimization result is generated.

## Legacy discrepancy classification

Classification: `MULTIPLE_CAUSES`

Two observable causes are independently confirmed:

1. `DOCUMENTATION_DIRECTION_ERROR`. The legacy prose says “V1 minus
   PER-DATASET-OPT,” while all six stored PER-DATASET point values equal
   `PER-DATASET-OPT - V1` reconstructed directly from the frozen metrics.
2. `ESTIMATOR_MISMATCH`. The six legacy PER-DATASET intervals match neither the
   corrected `Candidate - V1` percentile intervals nor their exact
   antisymmetric `V1 - Candidate` intervals under the specified paired
   case-ID estimator.

`EXPECTED_BOOTSTRAP_BEHAVIOR` is rejected: deterministic reconstruction under
the frozen estimator does not reproduce the legacy intervals. A low-level
`IMPLEMENTATION_ERROR` is not asserted because the generator source for
`artifacts/opt/final/bootstrap.json` was not committed with the artifact. The
available evidence therefore localizes the discrepancy to direction
documentation plus estimator/input-path mismatch, but cannot distinguish an
uncommitted implementation defect from use of a different unrecorded estimator
or input path.

The highlighted TT Avg@5 record illustrates both causes:

- legacy point: `+0.0066666667`, which is PER-DATASET minus V1;
- legacy CI: `[-0.1400000000, -0.0244444444]`;
- corrected Candidate-minus-V1 CI: `[-0.0333333333, +0.0466666667]`;
- corrected V1-minus-Candidate CI: `[-0.0466666667, +0.0333333333]`.

The legacy CI matches neither direction of the required estimator.

## Corrected paired bootstrap

### GLOBAL-OPT minus V1-SCIENTIFIC

GLOBAL-OPT and V1 have byte-identical frozen predictions on both datasets.

| Dataset | Metric | Point | Corrected 95% percentile CI |
|---|---|---:|---:|
| RE2-OB | Avg@5 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| RE2-OB | AC@1 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| RE2-OB | MRR | 0.0000000000 | [0.0000000000, 0.0000000000] |
| RE2-TT | Avg@5 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| RE2-TT | AC@1 | 0.0000000000 | [0.0000000000, 0.0000000000] |
| RE2-TT | MRR | 0.0000000000 | [0.0000000000, 0.0000000000] |

### PER-DATASET-OPT minus V1-SCIENTIFIC

| Dataset | Metric | Point | Corrected 95% percentile CI |
|---|---|---:|---:|
| RE2-OB | Avg@5 | -0.0111111111 | [-0.0266666667, 0.0000000000] |
| RE2-OB | AC@1 | -0.0222222222 | [-0.0555555556, 0.0000000000] |
| RE2-OB | MRR | -0.0157407407 | [-0.0379629630, 0.0000000000] |
| RE2-TT | Avg@5 | +0.0066666667 | [-0.0333333333, +0.0466666667] |
| RE2-TT | AC@1 | +0.0777777778 | [0.0000000000, +0.1555555556] |
| RE2-TT | MRR | +0.0357775552 | [-0.0132650477, +0.0870892761] |

The corrected results preserve the prior descriptive pattern: PER-DATASET is
lower on RE2-OB and mixed-to-higher on RE2-TT. They do not establish a
consistent Avg@5 improvement across datasets. The corrected evidence therefore
does not materially overturn the previous `NO_CLEAR_OPTIMIZATION_GAIN`
method-selection interpretation, although the legacy interval claims must not
be reused.

## Required invariants

Each invariant passes independently for GLOBAL-OPT and PER-DATASET-OPT on both
RE2-OB and RE2-TT.

| Invariant | Result | Executable meaning |
|---|---|---|
| Identity | PASS | V1 minus itself has point 0 and CI `[0, 0]` for every metric. |
| Antisymmetry | PASS | Reversing methods negates the point and swaps/negates CI endpoints. |
| Direct-point consistency | PASS | Bootstrap point equals direct Candidate aggregate minus V1 aggregate within `1e-12`. |
| Pair alignment | PASS | 90 identical case IDs and identical fault assignments; sampled IDs shared by construction. |
| Fault-stratum accounting | PASS | Six original strata of 15; each iteration draws 15 per stratum and 90 total. |
| Deterministic seed | PASS | Repeated seed `20260829` produces identical index plans and SHA-256 digests. |

## Provenance and limitation

The legacy artifact remains unchanged and matches its frozen-commit blob:
SHA-256
`23cd9e27592746191f116a163341f5b8d241ad290a7572aef2ea882f711d927e`.
The corrected artifact records the Gate 1 input SHA, sample-plan SHA for each
dataset, fault-level deltas, and every invariant detail.

Intervals are conditional on the fixed frozen root ranks. They do not include
uncertainty from benchmark reuse, model/search selection, system sampling, or
the absence of PER-DATASET candidate-level score/ranking evidence.
