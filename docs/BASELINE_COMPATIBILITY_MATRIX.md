# Performance-Blind RCAEval Baseline Compatibility Matrix

Status: **STATIC AUDIT COMPLETE; NO BASELINE EXECUTED**  
Date: 2026-08-27  
RCAEval checkout: `5e96b700445bfb5c599e505ecf37d53bf847bbeb`  
RCAEval remote: `https://github.com/phamquiluan/RCAEval.git`

This audit applies `docs/RCA_FINAL_EVALUATION_PROTOCOL_V1.0.md`. It was
completed without inspecting the human-verified RCAEval Table 6 reference or
using remembered/published performance. Classifications use only task fit,
actual code paths, information conditions, provenance, output semantics,
environment feasibility, effort, and scientific diversity.

## 1. Audit context and cross-cutting findings

The pinned RCAEval checkout is dirty before this audit. Its recorded upstream
HEAD is fixed above. Local modifications are limited to adding Python 3.10 to
the method import branch in `main.py` and selecting CUDA in
`RCAEval/e2e/run.py`; they are pre-existing and are not treated as official
upstream code. The Ada-RCA provenance audit binds their diff digest as
`24fd630537aee9daec7ca907e68360b6616046989b79d6c25d32e83021291320`.

The local `rcaeval` conda environment uses Python 3.10.20 and contains torch,
causal-learn, tigramite, and pingouin. The active Ada-RCA `DAG` environment uses
Python 3.8.20 and does not contain causal-learn, tigramite, or pingouin. The
RCAEval repository also has a separate Python-3.8-oriented
`requirements_rcd.lock`. These facts support environment classification only;
no import of an RCA method and no baseline call was made.

The common RCAEval `main.py` path:

- discovers `simple_metrics.csv` when `data.csv` is absent;
- forward-fills and then zero-fills metric missingness;
- selects 10 minutes before and 10 minutes after `inject_time` at default
  `--length 20`;
- passes this metric DataFrame to the selected method;
- converts indicator/operation names to services with underscore splitting and
  first-occurrence deduplication;
- does not enforce a complete legal service candidate permutation; and
- contains a successful-subset evaluation path, while its `e2e.rca` decorator
  may turn exceptions into a dummy column order.

Future reproduction must bypass or instrument silent fallback, preserve raw
failure status, and validate outputs against Ada-RCA's complete registry and
F-A--F-E taxonomy. An adapter may map native indicator/operation outputs to
services and append otherwise unscored legal candidates only under a
predeclared deterministic rule; native top-k and adapted complete ranking must
remain distinguishable.

Trace functions expect raw `traces.csv`, but the common runner supplies the
derived metric DataFrame. Their code compares `startTime + duration` directly
with `inject_time` while a commented conversion notes the seconds-to-
microseconds issue. RE2 applicability therefore remains
`UNKNOWN - REQUIRES EXECUTION AUDIT` until a non-performance adapter/unit audit
confirms timestamp units and service mapping.

## 2. Summary matrix

| Method | Family | Actual consumed telemetry in audited path | Supervision | Native output | Pairing | Protocol | Effort | Static RE2 applicability |
|---|---|---|---|---|---|---|---|---|
| BARO | metric | derived metric series | case-wise unsupervised | complete retained indicator ranking | PAIRABLE | P2 | LOW | OB yes; TT yes |
| CausalRCA | metric | derived metric series; optional metric+log branch exists | case-wise self-trained, no root labels | retained indicator ranking | PAIRABLE | P2 | LOW | OB yes; TT yes |
| CIRCA | metric | derived metric series | case-wise unsupervised | retained indicator ranking | PAIRABLE | P2 | LOW | OB yes; TT yes |
| MicroCause | metric | derived metric series + chosen SLI | case-wise unsupervised | retained indicator ranking | PAIRABLE | P2 | LOW | OB yes; TT yes |
| RCD | metric | derived metric series | case-wise unsupervised | selected indicator ordering | PAIRABLE | P2 | MEDIUM | OB yes; TT yes |
| MicroRank | trace | raw spans/derived operations | case-wise unsupervised | operation top-5 | UNKNOWN - REQUIRES EXECUTION AUDIT | P2 | LOW | OB/TT unknown pending timestamp audit |
| TraceRCA | trace | raw spans/derived operations | case-wise unsupervised | ranked observed operations | UNKNOWN - REQUIRES EXECUTION AUDIT | P2 | LOW | OB/TT unknown pending timestamp audit |
| multi-source BARO (`mmbaro`) | multi-source | derived metric + log series; trace branches dataset-key gated | case-wise unsupervised | cross-modality indicator ranking | PAIRABLE | P2 | LOW | OB/TT unknown pending adapter/key audit |
| multi-source CIRCA | multi-source | unknown; no audited callable implementation | unknown | unknown | NOT_PAIRABLE | P3 | HIGH | OB no audited path; TT no audited path |
| PDiagnose | multi-source | derived metrics + raw logs + raw traces | case-wise unsupervised | printed service ranking | NOT_PAIRABLE | P2 | HIGH | OB hard-coded demo only; TT unknown |
| multi-source RCD (`mmrcd`) | nominal multi-source | **metric only in computation** | case-wise unsupervised | selected indicator ordering | PAIRABLE | P2 | MEDIUM | OB/TT unknown pending adapter audit |

`PAIRABLE` above means the method's native output can in principle yield a
case-level primary utility on the same cases; it does not assert that a valid
run already exists. `UNKNOWN` is used where the static timestamp/input blocker
prevents that conclusion. All implementable methods remain P2 rather than P1:
Ada-RCA is root-label supervised and cross-case trained with a complete
candidate universe, whereas these audited paths are case-wise, label-free, and
usually produce indicator/operation rankings over observed retained nodes.

## 3. Metric-based methods

### 3.1 BARO

- **Paper category / scientific role:** metric-based robust anomaly-ranking
  representative; supplies a simple case-wise statistical contrast to
  Ada-RCA's supervised cross-case scorer.
- **Telemetry and preprocessing:** `simple_metrics.csv` through the common
  runner; raw versus derived = derived. The runner owns forward/zero fill and
  the default anchor window. `baro.py` splits pre/post per case, runs RCAEval
  `preprocess`, intersects retained columns, fits a per-indicator pre-event
  `RobustScaler`, and ranks by maximum post-event standardized value.
- **Window / anchor:** explicit pre/post split at `inject_time`; default common
  runner supplies 600 seconds on each side. Anchor dependent: yes.
- **Normalization:** per-case, per-indicator pre-event; no cross-case state.
- **Implementation / provenance:** official RCAEval function
  `RCAEval/e2e/baro.py::baro`; pinned RCAEval provenance is known. An original
  external implementation pointer is not encoded in the file: unknown.
- **Task and supervision:** native indicator RCA; service-level compatible only
  after the official name-to-service dedup adapter. Root-label training: no.
  Cross-case training: no. Pretraining/external knowledge: none observed.
- **Candidates / output:** all retained metric columns, sorted; complete at the
  retained-indicator level, not guaranteed complete at Ada-RCA's legal-service
  level. Scores are not returned. Primary top-k service utility is pairable;
  full-ranking MRR needs audited candidate completion.
- **Dependencies / blockers:** numpy, pandas, sklearn; no external runtime.
  Static blocker is output/candidate reconciliation, not algorithm execution.
- **Applicability / classification:** RE2-OB yes; RE2-TT yes; `PAIRABLE`;
  `P2_BENCHMARK_COMPARABLE_WITH_MATERIAL_DIFFERENCES`; `LOW` because the local
  Python 3.10 RCAEval environment contains the stack and only an audited adapter
  is required.
- **Evidence:** RCAEval `main.py`, `RCAEval/e2e/baro.py`,
  `requirements.txt`, Ada-RCA `docs/BENCHMARK_COMPATIBILITY.md`.

### 3.2 CausalRCA

- **Paper category / scientific role:** metric-based learned graph/PageRank;
  adds a neural within-case graph-construction assumption.
- **Telemetry and preprocessing:** the standard audited path consumes derived
  metrics after common runner fill/windowing and RCAEval preprocessing. A dict
  branch concatenates downsampled metric and `logts`, but trace inputs are
  commented out and the common RE2 runner does not construct this dict.
- **Window / anchor / normalization:** common 600-second pre/post anchor window;
  anchor dependent. The full within-case window is divided by column maxima;
  no cross-case normalization.
- **Implementation / provenance:** official RCAEval function
  `RCAEval/e2e/causalrca.py::causalrca`; file history identifies RCAEval commit
  `a41b1f4` as its addition. Original external source is not encoded: unknown.
- **Task and supervision:** native indicator ranking from a learned adjacency
  and PageRank. No root-label training or cross-case training; it self-trains
  on each case. No pretraining observed.
- **Candidates / output:** ranks retained indicator columns; an empty graph
  falls back to input column order. Service mapping is required and complete
  legal service ranking is not guaranteed.
- **Dependencies / blockers:** torch and scikit-network plus the RCAEval stack
  are present in the Python 3.10 environment. It is stochastic unless execution
  controls establish seeding; this requires an execution audit, not a semantic
  patch.
- **Applicability / classification:** metric branch OB yes and TT yes;
  `PAIRABLE`; P2; `LOW` by the objective dependency/adapter definition. The
  optional multi-source branch is not qualified by this row.
- **Evidence:** `RCAEval/e2e/causalrca.py`, `RCAEval/e2e/__init__.py`,
  `main.py`, local environment inspection.

### 3.3 CIRCA

- **Paper category / scientific role:** metric-based causal-graph construction
  plus regression-based hypothesis-test ranking; adds a non-neural graph family.
- **Telemetry and preprocessing:** derived metrics; RCAEval `preprocess` on the
  full case window, PC graph construction, then RHT ranking. The function passes
  the literal graph-construction dataset value `"ob"`, including on TT.
- **Window / anchor / normalization:** common anchored 600-second pre/post
  window; RHT receives `inject_time`. Preprocessing owner is RCAEval common
  runner plus `circa.py`; normalization granularity is unknown from this static
  entry-point audit.
- **Implementation / provenance:** official RCAEval function
  `RCAEval/e2e/circa.py::circa`, added in file history at `619fc2b`. Original
  implementation provenance is not encoded: unknown.
- **Task and supervision:** indicator-level case-wise unsupervised inference;
  no root-label or cross-case training and no pretraining observed.
- **Candidates / output:** sorted retained indicator names, requiring service
  dedup and legal-candidate completion audit. The `@rca` decorator catches all
  exceptions and returns preprocessed column order, so future reproduction must
  disable or detect this fallback.
- **Dependencies / blockers:** causal-learn/RCAEval graph stack is available in
  the Python 3.10 environment. Literal `dataset="ob"` on TT and silent fallback
  require static/integration validation, not performance interpretation.
- **Applicability / classification:** OB yes; TT yes at the runner level but
  with the recorded dataset-literal qualification; `PAIRABLE`; P2; `LOW`.
- **Evidence:** `RCAEval/e2e/circa.py`, `RCAEval/e2e/__init__.py`,
  `RCAEval/graph_construction/pc.py`, `RCAEval/graph_heads/rht.py`.

### 3.4 MicroCause

- **Paper category / scientific role:** metric-based temporal causal discovery
  and random walk; adds lagged PCMCI/partial-correlation inference.
- **Telemetry and preprocessing:** derived metrics through RCAEval preprocessing
  over the common anchored window. It uses a dataset-selected SLI supplied by
  `main.py`, PCMCI with lag up to 10, partial correlations, and a stochastic
  random walk. The file identifies source lineage from
  `https://github.com/PanYicheng/dycause_rca/tree/main` "with update."
- **Window / anchor / normalization:** common 600-second pre/post selection;
  anchor dependency arises from runner selection and SLI choice. Per-case only;
  no cross-case normalization.
- **Implementation / provenance:** official RCAEval function
  `RCAEval/e2e/microcause.py::microcause`; original lineage is traceable through
  the encoded URL, while the extent of RCAEval modifications is not enumerated.
- **Task and supervision:** indicator ranking; no root-label or cross-case
  training, no pretrained state observed. Service mapping required.
- **Candidates / output:** full score ordering of retained indicators, without
  scores in the returned artifact; complete legal services not guaranteed.
- **Dependencies / blockers:** tigramite, pingouin, causal-learn, networkx and
  scipy are present in the Python 3.10 environment. Random-walk seeding and
  SLI/name validity require execution audit.
- **Applicability / classification:** OB yes; TT yes; `PAIRABLE`; P2; `LOW` by
  dependency criteria, while computational burden must be measured only later.
- **Evidence:** `RCAEval/e2e/microcause.py`, `main.py`, local environment
  inspection.

### 3.5 RCD

- **Paper category / scientific role:** metric-based distribution-change RCA
  using an F-node and localized PC; adds a change-distribution causal-discovery
  assumption.
- **Telemetry and preprocessing:** derived metrics split pre/post at the anchor;
  constant/time removal, memory conversion, matched columns, per-case F-node
  labeling, discretization, and multi-phase localized PC. The F-node is a
  normal/anomalous segment label, not a root label.
- **Window / anchor / normalization:** common 600-second pre/post runner window;
  explicitly anchor dependent. Per-case preprocessing; no cross-case state.
- **Implementation / provenance:** official RCAEval function
  `RCAEval/e2e/rcd.py::rcd`, added in RCAEval history at `72112cb`. Original
  external implementation URL is not encoded: unknown.
- **Task and supervision:** selected indicator ordering, service mapping
  required. Root-label training: no. Cross-case training: no. Pretraining: no.
- **Candidates / output:** RCD-selected indicator order may be partial; complete
  service ranking and score output are absent.
- **Dependencies / blockers:** RCAEval imports RCD only in its Python 3.8 branch
  and provides `requirements_rcd.lock`; the active Python 3.8 Ada-RCA env lacks
  causal-learn. A separate compatible environment is therefore required.
- **Applicability / classification:** OB yes; TT yes; `PAIRABLE` for primary
  top-k utility after adapter validation; P2; `MEDIUM` based on the separate
  Python/dependency environment, not performance or vague complexity.
- **Evidence:** `RCAEval/e2e/rcd.py`, `RCAEval/e2e/__init__.py`, `main.py`,
  `requirements_rcd.lock`.

## 4. Trace-based methods

### 4.1 MicroRank

- **Paper category / scientific role:** trace-based anomaly partition,
  operation/trace PageRank, and spectrum ranking; supplies a trace graph family.
- **Telemetry and preprocessing:** raw `traces.csv`; derives operation as
  `serviceName + "_" + methodName`, pre-event operation latency SLO, normal and
  anomalous post-event trace groups, coverage graphs, and DStar2 scores.
  RCAEval owns preprocessing inside the function.
- **Window / anchor:** direct comparison of raw span end time to `inject_time`;
  anchor dependent. The function does not itself enforce the common symmetric
  window. The seconds/microseconds conversion is commented out and requires a
  non-performance unit audit.
- **Normalization:** per-case operation SLO; no cross-case normalization.
- **Implementation / provenance:** official RCAEval function
  `RCAEval/e2e/microrank.py::microrank`, with a header pointing to
  `https://github.com/IntelligentDDS/MicroRank`; added at RCAEval commit
  `17c5b68`.
- **Task and supervision:** operation-level case-wise unsupervised inference;
  no root labels, cross-case training, or pretraining observed. Operation names
  require service projection.
- **Candidates / output:** native output is top 5 operations only; neither full
  operation nor complete service ranking is available. AC@1/3 and Avg@5 may be
  derivable after a valid adapter, but MRR is not legitimate from native output.
- **Dependencies / blockers:** numpy/pandas only beyond repository code, but the
  common runner passes metric data and timestamp units are unresolved.
- **Applicability / classification:** OB and TT `UNKNOWN - REQUIRES EXECUTION
  AUDIT`; pairing also unknown until the trace adapter establishes a valid
  case-level output; P2; `LOW` because blockers are adapter/unit-audit work and
  no external runtime or algorithm patch is statically required.
- **Evidence:** `RCAEval/e2e/microrank.py`, `main.py`, file header/history.

### 4.2 TraceRCA

- **Paper category / scientific role:** trace-based latency anomaly detection
  with operation support/confidence ranking; a simpler trace-statistical family.
- **Telemetry and preprocessing:** raw spans; derives operation identity,
  pre-event mean/std latency, post-event abnormal flags, then ranks observed
  operations by the harmonic combination of support and confidence.
- **Window / anchor / normalization:** anchor-dependent raw-span split; no
  symmetric window enforcement in the function; per-case SLO. The same
  unresolved timestamp-unit issue as MicroRank applies.
- **Implementation / provenance:** official RCAEval function
  `RCAEval/e2e/tracerca.py::tracerca`, added at `31339ba`. Its header also says
  it was refactored from the IntelligentDDS MicroRank repository, so direct
  TraceRCA original-source provenance is ambiguous.
- **Task and supervision:** operation-level case-wise unsupervised; no root
  labels, cross-case training, or pretraining observed. Service mapping needed.
- **Candidates / output:** ranks all observed post-event operations with finite
  score; complete legal service coverage and returned scores are absent.
- **Dependencies / blockers:** local dataframe stack only; common runner input
  mismatch, timestamp units, zero-abnormal denominators, and unseen post-event
  operations require execution audit.
- **Applicability / classification:** OB/TT and pairing `UNKNOWN - REQUIRES
  EXECUTION AUDIT`; P2; `LOW` based on objective adapter-only effort.
- **Evidence:** `RCAEval/e2e/tracerca.py`, `main.py`, file header/history.

## 5. Multi-source methods

### 5.1 Multi-source BARO (`mmbaro`)

- **Paper category / scientific role:** multi-source independent robust anomaly
  scoring; provides the simplest feasible modality-fusion contrast.
- **Telemetry and preprocessing:** the function indexes raw metric/log/trace
  objects plus derived `logts`, `tracets_err`, and `tracets_lat`, although raw
  logs/traces and `cluster_info` are not used after access. Metrics are
  downsampled by row stride 15. Derived logs are always scored. Trace-error and
  trace-latency are scored only when `dataset` equals literal `mm-ob` or `mm-tt`;
  current RE2 keys do not meet this branch condition.
- **Window / anchor:** each consumed series is split at `inject_time`; a future
  adapter must impose the same explicit source window and document stride/time
  alignment. Anchor dependent.
- **Normalization:** per-case, per-indicator pre-event `RobustScaler`; modality
  ranks are merged by score with no learned cross-case fusion.
- **Implementation / provenance:** official exported RCAEval function
  `RCAEval/e2e/baro.py::mmbaro`, introduced as "Multi-source BARO" in RCAEval
  history at `834cd02`; original external provenance is not encoded.
- **Task and supervision:** indicator-level case-wise unsupervised; no root
  labels or cross-case training. Service adapter required.
- **Candidates / output:** merged cross-modality indicator ranking, potentially
  repeated service names and incomplete legal services; no scores returned.
- **Dependencies / blockers:** Python 3.10 RCAEval stack is sufficient, but the
  common RE2 runner does not construct its data dictionary, required unused keys
  must exist, and trace activation depends on non-RE2 dataset literals.
- **Applicability / classification:** OB/TT applicability unknown pending a
  source/key adapter audit; `PAIRABLE` once a valid dict path is established
  because per-case ranked output exists; P2; `LOW` as the needed work is an
  adapter and explicit branch audit, not an algorithm-semantic patch.
- **Evidence:** `RCAEval/e2e/baro.py`, `RCAEval/e2e/__init__.py`, `main.py`, git
  file history.

### 5.2 Multi-source CIRCA

- **Paper category / scientific role:** requested multi-source graph family.
- **Telemetry, window, anchor, preprocessing, normalization, candidates,
  output, supervision, and dependencies:** `UNKNOWN - REQUIRES EXECUTION AUDIT`.
  No `mmcirca` or equivalent callable implementation was found in the pinned
  RCAEval Python code or all-branch string history. The audited `circa()` accepts
  only a DataFrame and is metric-based.
- **Implementation / provenance:** official RCAEval implementation: no audited
  path. Implementation path: unavailable. Source provenance: unknown.
- **Applicability / classification:** RE2-OB no audited path; RE2-TT no audited
  path; `NOT_PAIRABLE`; `P3_CONTEXT_ONLY`; `HIGH` because source provenance and
  executable implementation are unavailable, not because of performance.
- **Scientific contribution:** would add a multi-source causal graph family if
  an official, semantics-preserving implementation were later supplied.
- **Evidence:** pinned RCAEval file inventory, `RCAEval/e2e/__init__.py`,
  `RCAEval/e2e/circa.py`, all-branch `mmcirca` search.

### 5.3 PDiagnose

- **Paper category / scientific role:** multi-source rule-based service scoring
  from metric, log, and trace anomaly counts.
- **Telemetry and preprocessing:** hard-coded demo reads
  `simple_metrics.csv`, raw `logs.csv`, `logts.csv`, and raw `traces.csv`; logts
  is unused. Metrics use pre-event mean/std and post-event 3-sigma counts. Logs
  count messages containing `error|fail` over the full file rather than an
  explicit event window. Traces use pre-event operation SLO and post-event
  abnormal spans. RCAEval's standalone script owns preprocessing.
- **Window / anchor / normalization:** metric and trace branches are anchor
  dependent and per-case; log branch has no explicit anchor window. No
  cross-case normalization.
- **Implementation / provenance:** file exists at
  `RCAEval/e2e/pdiagnose.py`, added at RCAEval commit `fbf6552`, but only exposes
  a hard-coded `main()`. It is not exported by `e2e/__init__.py`, does not accept
  a case argument, and prints rather than returns a ranking. Original source
  provenance is not encoded.
- **Task and supervision:** service-level case-wise unsupervised; no root-label
  or cross-case training, no pretraining observed.
- **Candidates / output:** service dictionary originates from metric columns;
  raw log/trace service keys are accumulated into it. Output is a printed full
  dictionary ordering, not a structured prediction artifact.
- **Dependencies / blockers:** ordinary local dataframe stack, but converting
  the demo into a general callable path and resolving window/name/key behavior
  is substantial algorithm integration rather than an adapter-only invocation.
- **Applicability / classification:** hard-coded OB demo path only; TT unknown;
  `NOT_PAIRABLE` in current form; P2 conceptually, because the task is benchmark
  comparable if implemented; `HIGH` on factual missing callable/general path.
- **Evidence:** `RCAEval/e2e/pdiagnose.py`, `RCAEval/e2e/__init__.py`, git file
  history.

### 5.4 Multi-source RCD (`mmrcd`)

- **Paper category / scientific role:** nominal multi-source RCD candidate.
- **Telemetry and preprocessing:** the function indexes `metric`, `logts`,
  `tracets_err`, and `tracets_lat`, but the computation only preprocesses and
  passes metric data to RCD. Log and trace values are never consumed by the
  ranking algorithm. Raw versus derived = derived metrics in actual use.
- **Window / anchor / normalization:** metric split pre/post at `inject_time`,
  with per-case constant/time removal, F-node construction, discretization, and
  localized PC. No cross-case normalization.
- **Implementation / provenance:** official exported RCAEval function
  `RCAEval/e2e/mmrcd.py::mmrcd`, introduced at `6df65ee`; original external
  provenance is unknown.
- **Task and supervision:** indicator-level case-wise unsupervised; no root
  labels/cross-case training/pretraining. Service adapter required.
- **Candidates / output:** selected indicator ordering, possibly partial; no
  scores or complete service ranking.
- **Dependencies / blockers:** Python-3.8 RCD branch/separate dependency stack;
  common runner does not construct the dict. More importantly, the audited
  implementation contributes no actual multimodal information despite its
  paper-family label.
- **Applicability / classification:** OB/TT unknown pending adapter audit;
  `PAIRABLE` if invoked legally; P2; `MEDIUM` due separate environment plus
  adapter. Its scientific family contribution is metric RCD redundancy, not
  demonstrated multi-source coverage.
- **Evidence:** `RCAEval/e2e/mmrcd.py`, `RCAEval/e2e/__init__.py`, `main.py`,
  `requirements_rcd.lock`.

## 6. Audit conclusion and unresolved execution prerequisites

No performance evidence was used. Static compatibility does not authorize a
run. Before any future reproduction, a separate execution protocol must resolve:

1. trace timestamp units and symmetric window construction;
2. native indicator/operation-to-service mapping and complete candidate policy;
3. silent exception fallback and successful-subset suppression;
4. deterministic controls for stochastic methods without selecting seeds by
   outcome;
5. the `mmbaro` dataset-key trace branch and exact consumed modalities;
6. the separate RCD environment; and
7. output/failure persistence at case level.

Multi-source CIRCA and PDiagnose cannot enter a minimum executable matrix from
the audited checkout without new provenance or substantial implementation
work. Multi-source RCD does not establish multi-source scientific coverage in
its current code because its ranking consumes metrics only.
