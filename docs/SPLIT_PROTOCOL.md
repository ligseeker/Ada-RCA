# P3-A0 Split Protocol

RE2-OB and RE2-TT are trained and evaluated independently. Each dataset has 90 cases arranged as 5 root services × 6 fault types × 3 repetitions.

The frozen three-fold OOF assignment is deterministic:

- repetition `1` → fold `0`;
- repetition `2` → fold `1`;
- repetition `3` → fold `2`.

This yields 30 test cases and 60 training cases per fold. Every fold covers every root × fault stratum exactly once. The assignment uses seed `20260826` as a provenance field; the mapping itself is deterministic from the official repetition directory and is not tuned against results.

Machine-readable assignments and fold train/test lists are stored under `artifacts/splits/re2ob/` and `artifacts/splits/re2tt/`. They are bound to the P3-A0 source-manifest SHA-256 and must not be changed after model results are observed.
