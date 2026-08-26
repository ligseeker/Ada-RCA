# Ada-RCA Research Documentation

This directory is the entry point for the standalone RCA research execution.

The completed P3 stage remains governed by [`RCA_P3_Research_Execution_Protocol_V0.6_min.md`](RCA_P3_Research_Execution_Protocol_V0.6_min.md). P3-G1 is permanently `NO-GO / CLOSED`.

The current P4-G0 minimal candidate-relative falsification experiment is governed by [`RCA_P4_G0_MINIMAL_COMPARATIVE_PROTOCOL_V0.7.md`](RCA_P4_G0_MINIMAL_COMPARATIVE_PROTOCOL_V0.7.md). It was frozen before P3-M exploratory post-mortem analysis and has priority for the current stage.

Current P4 execution order:

1. P4-G0 protocol freeze
2. P4-G0 implementation, tests, and config freeze
3. P3-M exploratory post-mortem
4. P4-G0 RE2-OB and RE2-TT runs
5. Frozen bootstrap and secondary diagnostics
6. P4-G0 decision and stop

External RCA baselines, neural models, learned comparative models, detector integration, GAIA, Ada-MGAD, topology, RE2-SS, RE1, RE3, and all third datasets are out of scope.

The append-only execution state is maintained in [`RESEARCH_STATUS.md`](RESEARCH_STATUS.md).
