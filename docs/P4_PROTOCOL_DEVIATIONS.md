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
