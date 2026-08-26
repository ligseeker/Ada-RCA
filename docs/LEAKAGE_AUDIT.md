# P3-A0 Leakage Audit

Status: PASS for the current data and manifest boundary.

| Audit axis | Result | Evidence |
|---|---|---|
| Root/fault label leakage into inputs | PASS | `inputs.jsonl` contains zero `root_service`, `fault_type`, and label-token hits. |
| Path leakage | PASS | Opaque `rcaeval://` URIs are used; raw relative directories and source paths are sidecar-only. |
| Candidate filtering by labels | PASS | Registries derive from CPU/MEM schema and fixed auxiliary entity policy; all cases rank the complete registry. |
| Service identity feature | PASS | No trainable service-ID feature exists in the P3-A0 input contract; service names are only registry keys required by task output. |
| Root-in-candidate invariant | PASS | OB 0/90 violations; TT 0/90 violations. |
| Split leakage | PENDING P3-A0 split freeze | The 3-fold assignment is generated and validated in the next independent step. |
| Preprocessing leakage | PENDING P3-A2 | No learned preprocessing has run; representation fit scope will be train-fold-only. |

The negative firewall tests reject forbidden metadata keys recursively. Any future feature extractor must accept `RCACaseInput` only and must not receive `RCACaseLabel`.
