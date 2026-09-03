# Ada-RCA Standalone RCA Research Execution Protocol V0.6-min

> Status: simplified execution protocol
> Date: 2026-08-26
> Scope: Standalone RCA only
> Supersedes: V0.5 for the CURRENT implementation stage
>
> Current goal:
> Implement and falsifiably validate the proposed standalone RCA method.
> Do NOT implement end-to-end Ada-MGAD integration.
> Do NOT reproduce external RCA baselines at this stage.

---

# 0. Current scope

Only work on:

Standalone RCA method
+ data preparation
+ evaluator
+ controlled variants/ablations
+ statistical validation
+ research documentation

Out of scope for the current stage:

- GAIA
- Ada-MGAD integration
- detector-triggered RCA
- external baseline reproduction
- RE2-SS
- RE1
- RE3
- topology/GNN
- Transformer
- production deployment

These may be revisited only after the standalone RCA method is frozen.

---

# 1. Datasets

Use only:

- RE2-OB
- RE2-TT

Reason:

Both are intended to provide the three target telemetry modalities:

- Metrics
- Logs
- Traces

and they represent substantially different system scales.

RE2-OB:
- 90 failure cases
- Online Boutique
- 6 fault types
- 5 root services
- 3 repetitions per root-service × fault pair

RE2-TT:
- 90 failure cases
- Train Ticket
- 6 fault types
- 5 root services
- 3 repetitions per root-service × fault pair

Total current experimental cases:
180.

Do not add/remove datasets after seeing method results without explicit protocol revision.

RE2-SS is intentionally excluded from the current tri-modal method validation because the current RCAEval distribution should be audited for trace availability and the method is currently scoped to complete Metrics+Logs+Traces input.

---

# 2. Task

For one confirmed failure case:

Input:
- event/injection anchor time t0
- Metrics
- Logs
- Traces
- legal candidate services

Output:
- complete unique ranking of candidate root-cause services

Primary task granularity:
- coarse-grained root-cause SERVICE localization

Do not claim fine-grained root-cause indicator localization.

---

# 3. RCAEval-aligned metrics

Headline metrics:

- AC@1
- AC@3
- Avg@5

Also save:
- AC@5

Diagnostic only:
- MRR
- paired bootstrap CI
- Magnitude-Inverted subset results

For each dataset independently, report by fault type:

- CPU
- MEM
- DISK
- SOCKET
- DELAY
- LOSS

Table format:

| Variant | CPU | MEM | DISK | SOCKET | DELAY | LOSS | AVERAGE |
|---|---|---|---|---|---|---|---|

Each fault cell contains:
- AC@1
- AC@3
- Avg@5

AVERAGE:
arithmetic mean over the six fault types.

Primary tables:
- RE2-OB
- RE2-TT

Do not hide dataset/fault heterogeneity behind one pooled 180-case score.

Optional summary:
- mean of RE2-OB and RE2-TT Avg@5

but this cannot replace the two dataset-specific tables.

---

# 4. Published RCAEval results: reference-only policy

At the current stage, DO NOT implement or reproduce external RCA baselines.

The attached RCAEval paper may be used only as a published reference.

Rules:

1. Clearly label such values:
   `Published result from RCAEval; not reproduced in this project`.

2. Never present a published number as if it were produced under the exact same implementation/training protocol as the proposed supervised model.

3. Do not claim statistical superiority over a published baseline without reproducing it.

4. The WWW'25 RCAEval paper provides a detailed RE2-Train Ticket comparison table.
   Those TT values may be cited as contextual reference.

5. If no corresponding published RE2-OB number exists in the cited source:
   do not invent or infer one.

External baseline reproduction is deferred until after the proposed method is frozen and only if needed for the thesis final comparison.

---

# 5. What comparisons ARE still mandatory

Although external baseline algorithms are deferred, controlled internal comparisons are mandatory.

They are NOT optional “baselines”; they are required to test the scientific hypothesis.

The method cannot be validated by reporting only one final model.

Required controlled variants:

Z0:
- anomaly magnitude only

Z1:
- magnitude + onset + simple pre/post evidence

Z2:
- Z1 + handcrafted morphology summaries

Z3:
- Z1 + amplitude-normalized full trajectory

Z3-SHUFFLE:
- same information as Z3 but temporal order destroyed

If P3-G1 passes, later neural variants:

V0:
- base evidence B
- no morphology
- independent scorer

V1:
- B + morphology
- independent scorer

V2:
- B
- comparative scorer

V3:
- B + morphology
- comparative scorer

These variants are necessary to answer:

RQ1:
Does temporal morphology add information beyond magnitude/onset/pre-post?

RQ2:
Does same-event candidate context add additional information?

---

# 6. RCAEval compatibility audit — simplified P3-R0

No external baseline reproduction is required.

P3-R0 only verifies benchmark semantics.

Must pin:

- RCAEval source commit/version
- dataset source/version/checksum

Must verify:

- RE2-OB 90 cases
- RE2-TT 90 cases
- root annotation parsing
- fault annotation parsing
- injection time parsing
- Metrics/Logs/Traces availability
- service candidate universe
- official time-window semantics
- telemetry cadence
- service-level ranking semantics
- AC@1 / AC@3 / AC@5 / Avg@5 evaluator correctness

Write toy evaluator tests.

If these semantics cannot be matched:
P3-R0 = BLOCKED.

Do NOT require BARO/RCD/etc. reproduction for P3-R0.

Artifacts:

docs/BENCHMARK_COMPATIBILITY.md
docs/EVALUATION_PROTOCOL.md

---

# 7. Candidate-service universe

For OB and TT separately create canonical service registries.

Candidate set must be derived from label-free system/telemetry information.

Never derive candidate services from:
- root labels
- historically injected-root list
- fault labels

For every case:
- rank all legal candidate services
- root must be in candidate registry
- no duplicates
- no label-derived filtering

Artifact:

artifacts/source/service_registry_ob.json
artifacts/source/service_registry_tt.json

---

# 8. Leakage firewall

Physically separate:

RCACaseInput:
- case_id
- t0
- candidate services
- metrics
- logs
- traces
- masks / non-label metadata

RCACaseLabel:
- root_service
- fault_type

Feature extraction and prediction must never access:
- root_service
- fault_type
- path-derived root token
- injection-target token

Folder/case names must not become model features.

No:
- trainable service ID
- service-name embedding
- fault-type embedding
- test root frequency feature

Add automated tests.

---

# 9. Representation freeze

Before looking at morphology performance, create and commit:

docs/REPRESENTATION_FREEZE.md

It must define exactly:

- event window
- time grid
- indicator-to-service mapping
- preprocessing
- robust normalization
- zero-scale fallback
- modality aggregation
- anomaly magnitude
- onset
- pre/post evidence
- morphology normalization
- missingness masks

Do not change these definitions after observing P3-A results unless a factual implementation blocker is found and the protocol is explicitly revised.

---

# 10. Default telemetry representation

Use numeric telemetry representations only.

No:
- raw-log language model
- pretrained text encoder
- trace graph neural network
- topology encoder

For each scalar indicator:

center = median(pre-event values)

scale = 1.4826 * MAD(pre-event values)

If scale < 1e-6:
- fallback to IQR / 1.349

If still degenerate:
- mark the indicator invalid for deviation scoring
- preserve coverage mask

Deviation:

d(t) = (x(t) - center) / (scale + 1e-6)

For service i and modality/channel m:

q_i,m(t) = Q90 over valid indicator |d(t)| values belonging to service i.

If no valid observation:
- mask
- do not treat as real zero

Recommended separate channels:
- metric
- log time-series
- trace-error time-series
- trace-latency time-series

---

# 11. Base evidence B

For each available channel:

Magnitude:
- max post-event q(t)

Mean impact:
- mean post-event q(t)

Pre/post shift:
- mean_post q(t) - mean_pre q(t)

Onset:
- first post-event time bin with q(t) >= 3.0
- condition must hold for two consecutive observed bins

If no onset:
- use end-of-window sentinel
- set onset_missing = 1

Persistence:
- fraction of post-event observed bins where q(t) >= 3.0

Coverage:
- observed fraction
- channel mask

These form base evidence B.

---

# 12. Amplitude-controlled morphology

For each available service/channel:

z(t) = q(t) / (max_observed q(t) + 1e-6)

If maximum is effectively zero:
- mark morphology channel inactive

The scientific claim is NOT:

“magnitude is useless”.

The claim under test is:

> Given magnitude/onset/pre-post evidence B, normalized temporal morphology z(t) provides additional root-ranking information.

---

# 13. Magnitude-Inverted analysis

Do not call all high-anomaly non-root services “propagated symptoms”.

Use neutral terminology:

MI-1:
true root is not rank 1 under frozen anomaly-magnitude score A_i.

MI-3:
true root rank > 3.

A_i must be frozen and label-free.

Recommended:

A_i =
mean across available telemetry channels
of clipped max-post q(t)

clip each channel score at 20.

Report MI-1 / MI-3:
- RE2-OB overall and by fault
- RE2-TT overall and by fault

MI subset is diagnostic.
It does not replace full-benchmark results.

---

# 14. Learned split

Train OB and TT independently.

Do not train one pooled OB+TT model in the primary experiment.

For each dataset:

90 cases =
5 roots × 6 faults × 3 repetitions

Use fixed 3-fold OOF.

For every root×fault stratum:
- one repetition -> fold 0
- one repetition -> fold 1
- one repetition -> fold 2

Each test fold:
30 cases.

Each train fold:
60 cases.

Create split manifest BEFORE model evaluation.

Do not change folds after seeing performance.

---

# 15. Zero-model audit

Primary low-capacity learner:

L2 Logistic Regression

One training row:
one candidate service in one training case.

Label:
1 if root
0 otherwise.

Candidate score:
logistic decision/probability score.

Within each case:
rank all candidates by score.

Fixed config:

C = 1.0
max_iter = 5000

Feature standardization:
train fold only.

Variants:

Z0:
magnitude only

Z1:
base evidence B

Z2:
Z1 + handcrafted normalized morphology summaries

Z3:
Z1 + flattened normalized trajectory and masks

Z3-SHUFFLE:
same Z3 representation, but morphology temporal order is deterministically destroyed

No hyperparameter search in zero-model audit.

---

# 16. P3-G1

Purpose:
decide whether neural morphology modeling is worth implementing.

Evaluate OB and TT separately.

P3-G1 PASS only if:

1. Average of OB and TT Avg@5:
   Z3 > Z1

2. Both datasets do not contradict strongly:
   neither dataset may have
   Delta Avg@5(Z3-Z1) < -0.02

3. At least one dataset has:
   Delta Avg@5(Z3-Z1) > 0

4. Temporal-order check:
   average Avg@5:
   Z3 > Z3-SHUFFLE

5. label/path/service-identity audit passes

Report paired bootstrap uncertainty for:
- Z3 - Z1
- Z3 - Z3-SHUFFLE

CI exclusion of zero is NOT required at G1.
G1 only authorizes neural MVP development.

If G1 fails:
STOP.

Do not add:
- GNN
- Transformer
- topology
- attention
- new datasets
- new external baseline

to rescue the hypothesis.

---

# 17. What happens after P3-G1

If PASS:

stop autonomous execution.

Next stage requires explicit approval.

Then implement V0/V1/V2/V3 neural controlled MVP.

If NO-GO:

preserve negative result and stop this method route.

---

# 18. Statistics

Main outputs:
- AC@1
- AC@3
- Avg@5

Per:
- dataset
- fault type

Key controlled differences:
- Z3 - Z1
- Z3 - Z3-SHUFFLE
- later V1 - V0
- later V3 - V2

Use paired case-level bootstrap:
- 10,000 resamples
- fixed seed
- within each dataset
- preserve fault-type balance when practical

Report:
- point delta
- 95% CI

Do not use statistical significance as a substitute for practical consistency across OB and TT.

---

# 19. Current first execution order

Repository inspection
    ↓
P3-R0 benchmark semantic compatibility
    ↓
P3-A0 OB/TT data + leakage audit
    ↓
P3-A0.5 representation freeze
    ↓
P3-A1 MI audit
    ↓
P3-A2 zero-model morphology audit
    ↓
P3-G1
    ↓
STOP

External baseline reproduction:
DEFERRED.

GAIA integration:
DEFERRED.

Neural model:
ONLY AFTER G1 PASS.

---

# 20. Mandatory current artifacts

docs/
- README.md
- RESEARCH_STATUS.md
- BENCHMARK_COMPATIBILITY.md
- EVALUATION_PROTOCOL.md
- DATASET_AUDIT_RE2.md
- LEAKAGE_AUDIT.md
- REPRESENTATION_FREEZE.md
- MAGNITUDE_INVERSION_AUDIT.md
- ZERO_MODEL_AUDIT.md
- P3_G1_DECISION.md

artifacts/source/
- RCAEval source manifest
- dataset manifests/checksums
- OB service registry
- TT service registry

artifacts/splits/
- OB 3-fold manifest
- TT 3-fold manifest

artifacts/runs/
- predictions
- configs
- metrics
- runtime
- environment
- git commit
- seed

tests/
- evaluator
- schema
- candidate completeness
- label firewall
- split integrity
- metric recomputation
- reproducibility

---

# 21. External reference table policy

It is acceptable to create:

docs/PUBLISHED_BASELINE_REFERENCE.md

It may include RCAEval paper values.

Every row/cell must identify:
- publication
- system
- dataset
- fault type
- method
- AC@1 / AC@3 / Avg@5
- reproduced? NO

This document is background/reference only.

Do not use these values in:
- Go/No-Go gates
- hyperparameter selection
- feature selection

and do not claim direct experimental superiority unless later reproduced under a comparable protocol.

---

# 22. Hard prohibitions for current stage

Do NOT:
- use GAIA
- modify Ada-MGAD
- implement detector-to-RCA integration
- reproduce external baselines
- use RE2-SS
- use RE1/RE3
- add topology/GNN/Transformer
- change headline RCAEval metrics
- hide fault-specific results
- tune on OOF test results
- use service/fault labels as model features
- change representation after inspecting performance
- switch datasets after seeing unfavorable results
- relax G1 after results

---

# 23. Current thesis interpretation

If Kernel A later succeeds, the defensible claim is narrow:

> On two complete tri-modal RCAEval RE2 systems, amplitude-normalized event-relative telemetry morphology provides root-service ranking information beyond frozen magnitude/onset/pre-post evidence under controlled event-level evaluation.

This does NOT yet establish:
- superiority over all published RCA baselines
- code-level RCA
- causal propagation recovery
- fine-grained indicator localization
- end-to-end anomaly detection + RCA
- universal cross-system generalization

Those require separate later evidence.
