# Ada-RCA P4-G0 Minimal Comparative Protocol V0.7

Status: FROZEN BEFORE P3-M POST-MORTEM
Date: 2026-08-27
Scope: standalone service-level RCA on RE2-OB and RE2-TT only.

This protocol tests one question: after frozen event-relative evidence is
computed for each candidate, does deterministic within-event candidate-relative
information improve root-service ranking? P3-G1 remains `NO-GO / CLOSED` and is
not revisited. This protocol does not authorize a learned comparative MLP or
any neural, graph, topology, attention, Transformer, service-identity, fault-
identity, candidate-pruning, third-dataset, GAIA, or external-baseline work.

## 1. Scope and frozen inputs

The only datasets are RE2-OB and RE2-TT, each with 90 cases. The prediction
input is the existing label-free `RCACaseInput`/frozen feature artifact. Labels
are used only by the training loss and evaluation. The canonical candidate
registry is complete and unchanged; every output ranks every legal candidate
exactly once, with the root present.

The P3 representation is inherited verbatim from `docs/REPRESENTATION_FREEZE.md`:

- Z1 is the 32-dimensional absolute base-evidence vector `B`.
- Z2 is the 68-dimensional vector containing Z1 and the frozen 36 morphology
  summaries (nine per channel).
- No Z3 trajectory fields are used in P4.

The frozen P3 split is reused exactly: independent three-fold OOF per dataset,
with repetition 1/2/3 assigned to folds 0/1/2. All candidates of a case stay
in one fold. Train-fold preprocessing only is permitted.

## 2. Controlled variants

| Variant | Representation | Purpose |
|---|---|---|
| A0 = Z1-ABS | frozen Z1 absolute features `h` | primary absolute control |
| A1 = Z1-REL | `[h, p]` | **primary H2 comparison** |
| A2 = Z2-ABS | frozen Z2 absolute features `h` | morphology factorial control |
| A3 = Z2-REL | `[h, p]` | secondary comparative replication |

Within each pair (A0/A1 and A2/A3), the scorer, split, scaling, objective,
regularization, and optimizer are identical. A1-A0 is the only primary H2
comparison. A3-A2 is secondary and is not a necessary condition for H2.

## 3. Candidate-relative percentile transform

For event `e`, candidate `i`, and frozen feature `k`, let `h_eik` be the raw
finite Z1 or Z2 value. For each feature independently, compute ascending ranks
among the N candidates in that same event; ties use average rank. For `N > 1`:

`p_eik = (rank_eik - 1) / (N - 1)`.

Thus `p` is in `[0, 1]`. If all candidates tie for a feature, average ranking
gives `p = 0.5` for every candidate. No jitter, labels, fault/root metadata, or
learned aggregation is allowed. Percentiles are computed before any scaler,
from raw deterministic frozen feature values. Existing frozen finite/missing
handling is reused; no P4-specific imputation is introduced.

Mean-centering is intentionally not a competing transform: in an event-softmax
linear scorer, an event-shared mean term cancels and would not provide a clean
comparative test. Percentile is the sole relative transform in this protocol.

## 4. Scorer and optimization

For each training fold, candidate representation `x_ei` receives one shared
weight vector `w` and no candidate-specific bias. Event probability is:

`P(i | e) = exp(w^T x_ei) / sum_j exp(w^T x_ej)`.

With root candidate `r_e`, optimize the deterministic conditional-logit loss:

`L(w) = sum_e [-log P(r_e | e)] + (1/2) ||w||_2^2`.

The regularization coefficient is fixed at `lambda = 1.0`; no C/lambda search is
allowed. Use zero initialization, float64 arithmetic where supported, SciPy
L-BFGS-B (or an exactly documented deterministic equivalent), fixed gradient
tolerance `1e-8`, and `max_iter = 1000`. The implementation must expose loss and
gradient and pass numerical-gradient, loss-decrease, synthetic recovery, and
deterministic-rerun tests.

Before fitting, fit `StandardScaler` on training-fold candidate rows only, then
transform both train and test rows. Percentile construction always precedes
scaling. No random seed model selection is performed.

## 5. Primary evaluation and gate

Report separately for each dataset: AC@1, AC@3, AC@5, Avg@5, and diagnostic
MRR, overall and by fault, root, and fold/repetition. The statistical unit is a
failure case, never a candidate row or optimizer rerun.

Primary metric is Avg@5 for A1-A0. Define:

- `Delta_OB = Avg@5(A1) - Avg@5(A0)`;
- `Delta_TT = Avg@5(A1) - Avg@5(A0)`;
- `Delta_mean = (Delta_OB + Delta_TT) / 2`.

P4-G0 passes only if all of the following are true:

1. `Delta_OB > 0`.
2. `Delta_TT > 0`.
3. `Delta_mean >= +0.01`.
4. In both datasets, `Delta AC@1(A1-A0) >= -0.01`.
5. A paired, case-level, fault-stratified 10,000-resample bootstrap (seed
   `20260826`) has a 95% CI lower bound greater than zero for the two-dataset
   mean Avg@5 delta. Report OB and TT CIs separately; they are descriptive and
   not additional hard gates.
6. All integrity tests pass, including label firewall, event batching, split
   integrity, complete rankings, metric recomputation, permutation equivariance,
   and deterministic rerun equality.

If any core condition fails, the decision is `P4-G0 = NO-GO`; no rescue by
changing representation, percentile, lambda, optimizer, split, threshold, or
model capacity is permitted. In either outcome, execution stops after the
decision.

## 6. Secondary diagnostics (pre-specified, non-gating)

Report A3-A2, A2-A0, A3-A1, and factorial interaction
`I = (A3-A2) - (A1-A0)` for Avg@5 and AC@1. Describe morphology as
`CONSISTENT`, `MIXED`, or `NOT_ROBUST`; do not call Z2 a new confirmation.

Also report MI-1/MI-3, fault/root/fold distributions, improved/degraded/unchanged
case rank transitions, and a leave-one-root-out stress test using the same
scorer and settings. LOSO is secondary and does not alter the primary gate.

For the mechanism diagnostic, derive an opaque case-id SHA-256 ordering and a
fixed cyclic derangement. Keep current-event `h` unchanged, compute percentiles
against the foreign event's candidate distribution, and apply the already
trained A1/A3 scorer without retraining. Report normal-versus-foreign Avg@5 and
AC@1. Interpret only as `NO_CONTEXT_DEPENDENCE_EVIDENCE`,
`MIXED_CONTEXT_DEPENDENCE`, or `CONTEXT_DEPENDENCE_OBSERVED`; never as causal
proof. Candidate-count effects are out of scope.

## 7. Artifacts, provenance, and deviations

P4 artifacts must persist configs, manifests, finite model inputs without labels,
evaluation predictions with labels only in evaluation sidecars, metrics,
bootstrap, LOSO, foreign-context, runtime, environment, and checksum records.
Every formal artifact records its generating Git commit, dataset tree digest,
split/representation provenance, seed, and command. Each logical stage receives
its own commit; P4 protocol, implementation/tests, and config freeze commits
must precede P3-M.

If a factual blocker prevents execution, record a protocol deviation containing
the frozen rule, factual blocker, proposed deviation, whether results were
already seen, and scientific consequence. A deviation changing representation,
split, primary model, percentile definition, lambda, metric, or gate requires
stopping for human authorization.

## 8. Interpretation boundary

If all gates pass, the only authorized claim is that deterministic
candidate-relative evidence provides incremental ranking value under this frozen
RE2 repetition-generalization protocol. If any gate fails, state that H2 is not
supported by this minimal comparative test. Neither outcome establishes
universality, unseen-root generalization (unless LOSO supports a separately
limited claim), causal propagation recovery, or state-of-the-art performance.

P3-M is exploratory post-result analysis and must not modify this protocol or
its implementation.
