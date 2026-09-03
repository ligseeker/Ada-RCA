# Historical Compatibility Audit

## Classification

- **Class A:** no historical candidate qualifies as a direct Class A replay in
  this worktree because the old P2 artifacts use different 5-fold assignments,
  feature bundles, and case registries.
- **Class B:** B2, C0-M, C0-L, C0-T, C1-I, and M1-S are concept-reusable but
  protocol-incompatible. Their core ideas may be represented by current
  canonical modality slices, but their reported numbers remain descriptive.
- **Class C:** any candidate using root-conditioned pruning, fault/root input,
  full-data preprocessing, incomplete rankings, or non-OOF selection is invalid
  for formal comparison. No such candidate is admitted to the frozen search.

## Why historical values were high

**FACT:** C1-I and M1-S used a legacy five-fold nested OOF protocol and feature
bundles different from the current 68D Z2 artifacts. C1-I reached RE2-OB
Avg@5 `0.9956`; M1-S reached `0.9933`; C0-M reached `0.9756`.

**FACT:** current V1 uses frozen three-fold assignments, a complete 90-case
registry, and event-relative Z2 features. RE2-OB is near a ceiling, so one case
can move Avg@5 by `1/(90*5)`.

**INFERENCE:** the numerical gap can reflect representation, scorer, fold,
candidate, and post-selection differences; the historical records do not
identify one cause. The evidence is consistent with protocol difference and
ceiling effects, not proof of a universally stronger method.

**UNKNOWN:** exact byte-level canonical replay of P2 C1-I/M1-S under the V1
registry is unavailable without rebuilding their legacy extraction adapters.

All historical rows are tagged `POST-HOC SELECTED FROM HISTORICAL CANDIDATES`.
