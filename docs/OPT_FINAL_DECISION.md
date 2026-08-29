# Final Decision

Decision: `NO_CLEAR_OPTIMIZATION_GAIN`

`GLOBAL-OPT` is identical to V1 on the frozen benchmark. `PER-DATASET-OPT`
raises TT AC@1/Avg@5 but lowers OB performance; its equal-dataset Avg@5 is
within the practical-equivalence band but bootstrap intervals do not establish
a consistent gain. Historical high scores remain post-hoc references.

The optimization branch is therefore complete and `STOPPED FOR HUMAN REVIEW`.
No transformer, graph model, new feature family, topology reranking, hard
negative scheme, or larger HPO is authorized by this round.
