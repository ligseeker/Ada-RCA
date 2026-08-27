# Ada-RCA Final Evidence Summary

Status: **COMPLETE; STOPPED — awaiting human review**  
Integrity status: `INTEGRITY_VALID`  
Scientific claim status: `SCIENTIFIC_CLAIM_RESTRICTED`  
Method status: `FINAL_METHOD_IMPLEMENTATION_FROZEN`

This summary covers the frozen Route-A Z2 method on the same 180-case
RE2-OB/RE2-TT corpus used by P3 and P4. It is descriptive evidence, not a new
confirmatory evaluation.

## Final operational method and replay

Ada-RCA is frozen as **Event-Relative Multimodal Morphology Ranking**: frozen
68D Z2 representation plus event-level conditional logistic scoring, lambda 1,
train-fold-only StandardScaler, deterministic float64 optimization, complete
legal candidate ranking, and separate OB/TT three-fold repetition OOF.

The exact replay persisted every fold's scaler mean/scale and weights. It
reproduced committed P4 A2 rankings with zero maximum score error and exact
metrics:

| Dataset | AC@1 | AC@3 | AC@5 | Avg@5 | MRR | Cases | Ranking identity |
|---|---:|---:|---:|---:|---:|---:|---|
| RE2-OB | 0.8777777778 | 0.9888888889 | 0.9888888889 | 0.9622222222 | 0.9314814815 | 90/90 | identical; max error 0.0 |
| RE2-TT | 0.7111111111 | 0.8666666667 | 0.9333333333 | 0.8511111111 | 0.8034718882 | 90/90 | identical; max error 0.0 |

All folds converged under gradient infinity norm `<=1e-8`. Exact replay is an
identity/integrity verification, not fresh performance evidence.

## Supported or observed evidence

- Magnitude inversion is material: the frozen magnitude score misses rank 1 in
  66/90 OB cases and 90/90 TT cases; MI-3 occurs in 25/90 OB and 85/90 TT.
- Z0 to Z1 shows the expected large gain from base event evidence, but this is
  an internal staged comparison rather than an external baseline claim.
- P3 Z3 versus Z3-SHUFFLE shows that aligned temporal organization contains
  RCA-relevant information relative to deterministic temporal destruction, but
  P3-G1 itself is `NO-GO / CLOSED` because full trajectories did not provide a
  stable cross-dataset gain over Z1.
- Z2 was positive versus Z1 in the observed P3 exploratory summary and in both
  absolute scorer comparisons (P4 A2-A0: +0.011111 OB, +0.086667 TT; P4 A3-A1:
  +0.002222 OB, +0.024444 TT). These are post-observed directional results,
  not untouched confirmation.
- S0, S1, and S2 all separate from the final method under the frozen
  `CONTROL_SEPARATED` rule. The final method therefore exceeds the tested
  benchmark root-universe structural baseline, observability-only representation,
  and exact pre-event-only representation on both datasets at the point and
  equal-dataset bootstrap levels.
- S3 identifies stable service fingerprints: OB top-1 0.598990 and macro-F1
  0.583065; TT top-1 0.132190 and macro-F1 0.113494. S3 is diagnostic only and
  does not imply root-label leakage.

## Control details

All control deltas are `FINAL_Z2 - CONTROL`, based on 10,000 paired
fault-stratified resamples with seed 20260827.

| Control | OB Avg@5 delta [95% CI] | TT Avg@5 delta [95% CI] | Equal-dataset mean [95% CI] | State |
|---|---:|---:|---:|---|
| S0-A deterministic | +0.362222 [+0.293333,+0.431111] | +0.251111 [+0.171111,+0.328889] | +0.306667 [+0.254444,+0.358889] | CONTROL_SEPARATED |
| S0-B tie-neutral analytical | +0.362222 [+0.333333,+0.384444] | +0.251111 [+0.202222,+0.300000] | +0.306667 [+0.278889,+0.334444] | CONTROL_SEPARATED |
| S1 observability-only | +0.471111 [+0.397778,+0.546667] | +0.802222 [+0.740000,+0.862222] | +0.636667 [+0.588889,+0.684444] | CONTROL_SEPARATED |
| S2 pre-event-only | +0.320000 [+0.253333,+0.388889] | +0.640000 [+0.551111,+0.726667] | +0.480000 [+0.425556,+0.536667] | CONTROL_SEPARATED |

S0 is not a root-frequency prior: all folds contain the five legal roots, and
the tie-neutral numbers are analytic expectations from actual tie groups. S1
shows observability structure is informative but does not dominate. S2 is the
primary falsification control: it does not match or exceed Z2, so
`CORE_INTERPRETATION_NOT_SUPPORTED` is not triggered. Nevertheless, S3 and the
OB fingerprint result restrict how specifically the gain may be attributed to
morphology rather than stable service observability/fingerprint structure.

## Closed negative results

P3-G1 remains `NO-GO / CLOSED` with the exact meaning:

> full amplitude-normalized trajectory plus frozen independent scorer did not
> provide stable cross-dataset gain.

P4-G0 remains `NO-GO / CLOSED` with the exact meaning:

> deterministic within-event feature-wise percentile failed the preregistered
> cross-dataset consistency gate.

Neither result is reinterpreted or rescued.

## Anchor robustness

The data-only feasibility audit required support over `[t0-630,t0+630)` for
all offsets and all four official derived sources. It found 77 unsupported
case-source-offset combinations affecting five cases (49 OB, 28 TT). The
status is `ANCHOR_AUDIT_NOT_FEASIBLE_UNDER_FROZEN_PIPELINE`; no shifted
performance, delta=0 extraction identity, or rank-transition analysis was run.
Robustness evidence is unavailable under the current frozen data pipeline. No
padding, interpolation, truncation, source switch, case dropping, or
feasible-subset analysis was used.

## Mandatory uncertainty and selection disclosure

The final operational combination `Z2 + event-level conditional logit` was
synthesized after observing P3 and P4 outcomes. P4 A2 is not an untouched
confirmation. P3 and P4 use the same 180-case corpus. Exact replay is an
identity/integrity verification, not fresh performance evidence. No new
bootstrap, fold summary, replay, or scorer wording turns this into independent
replication.

There is no claim of untouched confirmation, unseen-root generalization,
unseen-fault generalization, cross-system generalization, causality, SOTA,
universal morphology mechanism, universal uselessness of candidate-relative
information, or necessity of topology being absent. No thesis chapter or next
method stage is authorized by this summary.

## Deviations

1. The historical P4 foreign-context model-state reconstruction deviation is
   retained from `docs/P4_PROTOCOL_DEVIATIONS.md`; its diagnostic is further
   qualified by `docs/P4_CONTEXT_DIAGNOSTIC_LIMITATION.md` because normal and
   foreign percentile mappings differ (`(rank-1)/(N-1)` versus
   `(#less+0.5#equal)/N`). P4 primary results are unaffected.
2. The final audit's first uncommitted S0/S1/S2 run exposed a float64 strict
   loss-comparison issue in Newton polishing. The documented ULP-aware
   acceptance deviation in `docs/FINAL_AUDIT_PROTOCOL_DEVIATIONS.md` preserved
   the exact objective and scientific design. The valid rerun corrected
   stationarity; RCA metrics and root ranks remained unchanged. One OB S1 case
   changed only the order of non-root candidates, with the root remaining rank
   4.
3. Anchor feasibility required a pure data-support boundary correction to use
   half-open cadence support (`last_timestamp + cadence`). This corrected audit
   logic before the final feasibility result and did not compute performance or
   alter the frozen pipeline.

