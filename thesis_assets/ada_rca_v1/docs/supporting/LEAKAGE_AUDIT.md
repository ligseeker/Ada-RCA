# P3-A0 Leakage Audit

Status: PASS for the current data and manifest boundary.

| Audit axis | Result | Evidence |
|---|---|---|
| Root/fault label leakage into inputs | PASS | `inputs.jsonl` contains zero `root_service`, `fault_type`, and label-token hits. |
| Path leakage | PASS | Opaque `rcaeval://` URIs are used; raw relative directories and source paths are sidecar-only. |
| Candidate filtering by labels | PASS | Registries derive from CPU/MEM schema and fixed auxiliary entity policy; all cases rank the complete registry. |
| Service identity feature | PASS | No trainable service-ID feature exists in the P3-A0 input contract; service names are only registry keys required by task output. |
| Root-in-candidate invariant | PASS | OB 0/90 violations; TT 0/90 violations. |
| Split leakage | PASS | `artifacts/splits/re2ob_3fold.json` and `artifacts/splits/re2tt_3fold.json` are frozen before P3-A2; each fold has 30 test and 60 train cases, and `tests/test_split_integrity.py` verifies disjointness and root x fault balance. |
| Preprocessing leakage | PASS | Event normalization is case-local and pre-event-only; each OOF `StandardScaler` is fit on training-fold candidate rows only. `tests/test_zero_model.py`, `tests/test_run_artifacts.py`, and the committed run manifests verify the fixed boundary. |

The negative firewall tests reject forbidden metadata keys recursively. Any future feature extractor must accept `RCACaseInput` only and must not receive `RCACaseLabel`.
