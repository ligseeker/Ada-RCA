# Legacy Ada-MGAD RCA Asset Map

The sibling repositories were inspected read-only. No files were copied or modified. The V0.6-min protocol remains the authority.

| Legacy asset | Classification | Ada-RCA handling | Reason |
|---|---|---|---|
| `Ada-MGAD-rca-standalone/src/data/schema.py` | REIMPLEMENT | Recreate isolated `RCACaseInput` / `RCACaseLabel` contracts | Useful schema ideas, but current protocol requires a fresh leakage firewall and only RE2-OB/TT scope. |
| `Ada-MGAD-rca-standalone/src/data/rcaeval.py` | REIMPLEMENT | Rebuild adapters against the current local layouts | Historical adapter is evidence about parsing, not a frozen implementation. |
| `Ada-MGAD-rca-standalone/src/evaluation/metrics.py` | REIMPLEMENT | Rebuild and toy-test AC@1/3/5, Avg@5, and diagnostic MRR | Metric semantics are frozen by V0.6-min and must be independently verified. |
| `Ada-MGAD-rca-standalone/src/evaluation/bootstrap.py` | REIMPLEMENT | Rebuild paired case-level bootstrap with the current fixed seed | Statistical procedure is protocol-bound and must be traceable to this repository's commit. |
| `Ada-MGAD-rca-standalone/tests/` | REFERENCE_ONLY | Use as audit-pattern reference only | Tests may encode the superseded P1/P2 protocol. |
| `Ada-MGAD-rca-standalone/docs/` | REFERENCE_ONLY | Consult historical provenance and diagnostics only | Historical documents are not current rules. |
| `Ada-MGAD/src/rca/` and neural RCA localizers | DO_NOT_PORT | Do not use | They belong to the old Ada-MGAD / event-stage method and violate current scope. |
| `Ada-MGAD/util/GAIA/` and GAIA assets | DO_NOT_PORT | Do not use | GAIA is explicitly out of scope. |
| Legacy result checkpoints and published baseline outputs | DO_NOT_PORT | Do not use for selection or gates | External/past results cannot influence the current frozen experiment. |
