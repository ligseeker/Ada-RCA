# Ada-RCA Research Documentation

This directory is the entry point for the standalone RCA research execution.

The governing protocol is [`RCA_P3_Research_Execution_Protocol_V0.6_min.md`](RCA_P3_Research_Execution_Protocol_V0.6_min.md), the repository's exact filename for the user-specified V0.6-min protocol. The protocol is frozen and has priority over historical assets and implementation preferences.

Current execution order:

1. Repository governance and provenance
2. P3-R0 benchmark compatibility
3. P3-A0 data, candidate-universe, and leakage audit
4. P3-A0.5 representation freeze
5. P3-A1 magnitude-inversion audit
6. P3-A2 zero-model morphology audit
7. P3-G1 morphology signal gate

External RCA baselines, neural models, detector integration, GAIA, Ada-MGAD, RE2-SS, RE1, and RE3 are out of scope until the frozen gate authorizes a later stage.

The append-only execution state is maintained in [`RESEARCH_STATUS.md`](RESEARCH_STATUS.md).
