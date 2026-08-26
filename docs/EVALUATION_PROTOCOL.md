# Evaluation Protocol

## Scope

This protocol evaluates standalone, coarse-grained root-cause service localization on RCAEval RE2-OB and RE2-TT. Each case supplies an event anchor `t0`, metrics, logs, traces, and the complete legal candidate-service registry. Models must output a duplicate-free ranking containing every candidate exactly once.

## Metrics

For a case with root service `r` and ranking `R`:

- `AC@k = 1[r is in R[:k]]`.
- `Avg@5 = (AC@1 + AC@2 + AC@3 + AC@4 + AC@5) / 5`.
- `MRR = 1 / rank(r)` is diagnostic only.

Aggregate metrics are arithmetic means over cases. Primary reports are separate for RE2-OB and RE2-TT and are further separated by CPU, MEM, DISK, SOCKET, DELAY, and LOSS. The six-fault AVERAGE is the unweighted arithmetic mean of the six fault-type results; a pooled 180-case score is not a replacement.

## RCAEval compatibility

The evaluator is independently implemented in `src/rca/evaluator.py` and toy-tested for AC@1, AC@3, AC@5, and Avg@5. It requires complete, unique rankings over the legal candidate registry and rejects duplicates or omitted candidates.

## Provenance

P3-R0 pins the RCAEval checkout commit, the dirty-checkout diff digest, the Zenodo RE2 release record, and per-file dataset SHA-256 manifests. All formal experiment artifacts must record the generating Ada-RCA Git commit as well.
