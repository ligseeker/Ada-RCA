# Final Ada-RCA Audit Protocol Deviations

## Deviation 1: float64 ULP-aware Newton polishing acceptance

1. **Frozen rule:** S1 and S2 use the same deterministic conditional-logit
   objective, lambda 1.0, train-fold-only scaler, L-BFGS-B initialization, and
   final gradient infinity-norm tolerance `<= 1e-8` as the final method.
2. **Factual blocker:** The first uncommitted S0/S1/S2 run exposed four S1/S2
   folds whose gradients remained between `7.05e-8` and `4.30e-7`. Direct
   diagnostic evaluation showed that the analytic full Newton step reduced
   those gradients to approximately `1e-14`, but the float64 summed objective
   increased by only 1-8 units in the last place. The existing strict
   `candidate_loss < current_loss` guard rejected those stationarity-improving
   steps. Analytic and finite-difference derivative tests continued to pass.
3. **Deviation:** Preserve the exact objective, Hessian, Newton direction,
   representation, split, scaler, lambda, and zero initialization. A Newton
   candidate may additionally be accepted when its loss is no more than eight
   float64 ULPs above the current summed loss and its gradient infinity norm is
   strictly smaller. The eight-ULP bound is an arithmetic-resolution rule, not
   a performance or scientific threshold.
4. **Results already seen:** **YES.** Preliminary S0/S1/S2 point metrics and
   comparison states were printed before the convergence failure was audited.
   Those artifacts were not committed and are invalid/superseded. No feature,
   split, lambda, scorer, candidate universe, window, bootstrap, or decision
   rule was changed in response to performance.
5. **Scientific consequence:** Numerical integrity only. All controls must be
   regenerated from a clean commit and all folds must satisfy `<= 1e-8` before
   any result is interpreted. The rerun must report whether rankings or metrics
   differ from the invalid preliminary run; any such difference is descriptive
   and cannot trigger further changes.

