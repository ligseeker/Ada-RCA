# Ada-RCA V2 Final Decision

Date: 2026-08-29

## Mechanical decision

- `V2_G0 = INTEGRITY_VALID`
- `V2_F0 = DESCRIPTIVE_ONLY`
- `PERFORMANCE_GO = false`
- `MECHANISM_GO = false`
- `V2_F1 = NO_GO`
- `V2_F2 = NOT_AUTHORIZED`
- `V2_F3 = NOT_AUTHORIZED`

The F1 performance gate fails because TT Delta Avg@5 is negative, neither
dataset has a strict positive aligned-minus-Z2 Avg@5 delta, and the
equal-dataset CI lower bound is not positive. The mechanism gate fails because
aligned-minus-misaligned Avg@5 is negative on TT and the equal-dataset CI lower
bound is not positive. Integrity and both AC@1 guards pass.

## Final V2 status

Ada-RCA V2 does not replace or modify the frozen V1 method. F1 is retained as a
negative exploratory result, not as an operational candidate. F2 reliability
weighting and F3 rank-1 interaction were not implemented because the protocol
does not authorize them after F1 NO-GO.

No rescue through alternate XC definitions, modality selection, thresholds,
lag search, hyperparameter tuning, MLP, attention, TCN, Transformer, GNN,
topology propagation, boosting, new data, or changed metrics is authorized.

The next authorized action is human review of the committed evidence only.

**STOPPED FOR HUMAN REVIEW**
