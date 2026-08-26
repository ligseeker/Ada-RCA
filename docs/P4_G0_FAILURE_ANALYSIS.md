# P4-G0 Failure Analysis

P4-G0 is a minimal falsification experiment, not a tuning exercise. The
primary failure is the frozen dataset-consistency condition: candidate-relative
percentiles improve TT Avg@5 by `+0.066667` but reduce OB Avg@5 by `-0.004444`.
The positive two-dataset mean and its CI cannot rescue the required OB > 0
condition.

## Successful and degraded cases

For root-rank transitions A1 versus A0, OB has 4 improved, 7 degraded, and 79
unchanged cases; TT has 28 improved, 11 degraded, and 51 unchanged. The largest
TT gains concentrate in CPU, MEM, and route/train roots, while large losses
occur in several AUTH/TRAVEL delay/loss cases. OB changes are sparse and mixed;
the largest gains are concentrated in currencyservice cases, with losses also
present for currencyservice and checkoutservice.

## MI-1 / MI-3

On OB, A1-A0 Avg@5 is `-0.006061` for MI-1 and approximately zero for MI-3;
AC@1 is `+0.030303` and `+0.120000`, respectively. On TT every case is MI-1;
the MI-1 Avg@5 delta is `+0.066667`. TT MI-3 (85 cases) is `+0.056471`.
The five TT non-MI-3 cases show `+0.240000`, too small for a stable claim.

## Fault, root, and fold

OB fault deltas range from `-0.053333` (CPU) to `+0.053333` (MEM); fold 1 is
negative (`-0.013333`) and fold 2 is more negative (`-0.026667`). TT is
heterogeneous: CPU `+0.173333`, MEM `+0.146667`, SOCKET `+0.053333`, DELAY
`+0.080000`, DISK `0`, and LOSS `-0.053333`. TT root effects range from
`-0.055556` (AUTH/TRAVEL) to `+0.288889` (TRAIN), and all folds are positive.
These patterns reject a single universal “all faults/all roots” mechanism.

## A3-A2, morphology, and interaction

A3-A2 is `-0.013333` Avg@5 on OB and `+0.004444` on TT. Z2 absolute versus Z1
is positive on both datasets, but this is a post-observed morphology consistency
analysis, not new untouched confirmation. The factorial interaction is
`-0.008889` (OB) and `-0.062222` (TT) for Avg@5, indicating that the relative
effect is smaller when morphology summaries are already present.

## LOSO and context intervention

LOSO A1-A0 root-macro Avg@5 is `+0.008889` (OB) and `+0.037778` (TT), with
zero or negative held-out-root deltas for several roots. Therefore no broad
unseen-root generalization claim is authorized. Foreign-context normal-minus-
foreign Avg@5 is positive on both datasets (`+0.004444`, `+0.017778`), but this
only supports `CONTEXT_DEPENDENCE_OBSERVED`; it is not causal mechanism proof.

## Coverage and numerical integrity

Frozen mean q coverage is `0.544113` (OB) and `0.354154` (TT). Coverage/rank-
gain correlations are small and descriptive. The initial L-BFGS-B persistence
and stopping issues were repaired by the documented deterministic state
reconstruction and Newton-polishing deviations. Polished runs satisfy the
gradient tolerance, replay exactly, and preserve all rankings; the initial
unpolished outputs are superseded evidence.

## Scientific conclusion

The minimal candidate-relative route fails its preregistered cross-dataset
consistency gate. The observed TT gain is real under this implementation but is
not stable across OB and TT. No learned MLP, alternate relative transform,
lambda search, topology, graph model, attention, Transformer, or third dataset
is authorized as a rescue in this round.
