# P4-G0 Protocol Deviations

## Deviation 1: deterministic model-state reconstruction for foreign context

1. **Frozen rule:** Foreign-context diagnostics must apply the already trained
   A1/A3 fold model without retraining.
2. **Factual blocker:** `scripts/run_p4_g0.py` persisted predictions, configs,
   convergence summaries, runtime, environment, and checksums, but did not
   persist fold scaler means/scales and conditional-logit weights. The formal
   process had exited before this omission was detected, so the in-memory model
   objects were unavailable.
3. **Proposed deviation:** Reconstruct each A1/A3 fold model once using the exact
   committed frozen feature artifacts, split, percentile transform, scaler,
   lambda, optimizer, tolerance, and max-iteration settings. Before any foreign
   context is evaluated, require reconstructed normal-context scores and
   rankings to match the committed formal prediction artifact within strict
   floating tolerance (`max absolute score error <= 1e-12`, identical ranking).
   The reconstructed model is then used without further fitting for the foreign
   context intervention.
4. **Results already seen:** YES. Overall A0/A1/A2/A3 metrics for both RE2-OB
   and RE2-TT had been generated and committed when the persistence omission was
   detected.
5. **Scientific consequence:** This is a reproducibility/persistence deviation,
   not a scientific-design change. It does not change representation, split,
   primary model, percentile definition, lambda, primary metric, or Gate. Exact
   replay equality is required; failure of replay invalidates the context
   diagnostic and stops decision execution. The primary P4-G0 results and Gate
   do not depend on this diagnostic.

## Deviation 2: deterministic Newton polishing for optimizer tolerance

1. **Frozen rule:** The L-BFGS-B conditional-logit fit must satisfy final
   gradient infinity norm `<= 1e-8` with deterministic zero initialization,
   lambda 1.0, and max_iter 1000.
2. **Factual blocker:** On the first formal runs, L-BFGS-B reported successful
   relative-function convergence while some TT folds had final gradient norms
   up to `1.72e-6`. Analytic and finite-difference gradients agreed; this was a
   stopping-criterion issue, not an objective or leakage error.
3. **Proposed deviation:** After L-BFGS-B, run at most 32 deterministic damped
   Newton steps using the exact analytic Hessian of the same conditional-logit
   objective and L2 penalty. Accept only strictly loss-decreasing steps and
   require the frozen `1e-8` gradient tolerance. This does not change the
   representation, split, scorer, lambda, metrics, or gate.
4. **Results already seen:** YES. Initial formal A0/A1/A2/A3 results were
   observed and committed before this numerical issue was identified.
5. **Scientific consequence:** The first formal runs are superseded numerical
   evidence. All primary P4 metrics, bootstrap, and diagnostics must be rerun
   from a clean commit with polished fits. If polishing fails for any fold, the
   integrity condition fails and the P4 decision cannot be a PASS.
