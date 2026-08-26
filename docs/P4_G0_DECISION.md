# P4-G0 Decision

## Scope

This is the preregistered minimal candidate-relative test on RE2-OB and RE2-TT
only. P3-G1 remains `NO-GO / CLOSED`; P4 does not reinterpret or rescue P3.

## Gate checks

1. **OB A1-A0 Avg@5 > 0:** FAIL. Delta `-0.004444`.
2. **TT A1-A0 Avg@5 > 0:** PASS. Delta `+0.066667`.
3. **Two-dataset mean delta >= +0.01:** PASS. Mean `+0.031111`.
4. **AC@1 guardrails:** PASS. OB `+0.011111`; TT `+0.100000`; both are
   greater than or equal to `-0.01`.
5. **Paired fault-stratified bootstrap:** PASS for the mean-effect CI. Mean
   95% CI is `[+0.001111, +0.062222]`, lower bound > 0. OB and TT CIs are
   reported descriptively; OB includes zero and TT excludes zero.
6. **Integrity:** PASS. All formal rankings are complete, unique, and root-
   containing; metrics recompute exactly; split and label-firewall tests pass;
   candidate permutation invariance passes; all polished fits satisfy the
   gradient tolerance; exact replay has zero score error and identical ranking;
   the full test suite passes 40/40.

## Decision

**P4-G0 = NO-GO.**

The frozen minimal comparative test does not support H2 because the required
dataset-consistency condition fails on RE2-OB. Candidate-relative percentile
information improved TT ranking under this protocol, but the effect was not
positive on both datasets. The positive pooled descriptive mean and bootstrap
CI cannot override the preregistered OB positivity requirement.

## Morphology consistency

This is a descriptive post-observed analysis, not new untouched confirmation.
Z2-ABS minus Z1-ABS Avg@5 is `+0.011111` on OB and `+0.086667` on TT;
Z2-REL minus Z1-REL is `+0.002222` on OB and `+0.024444` on TT. Together with
P3 Z2-Z1, the morphology status is **MIXED** as a cross-dataset scientific
claim, while Z2 absolute evidence is descriptively positive in these runs.

## Limitations and stop rule

LOSO effects are positive in root-macro average but heterogeneous per held-out
root, so no unseen-root generalization claim is made. Foreign intervention
meets the descriptive status `CONTEXT_DEPENDENCE_OBSERVED`, not causal proof.
The two documented deviations concern deterministic model-state reconstruction
and Newton polishing; both preserve the frozen scientific design and are fully
audited.

This round stops here. No learned comparative MLP, alternate relative
transform, lambda search, topology, graph model, attention, Transformer,
candidate pruning, third dataset, external baseline, or Z3 rescue is authorized.
