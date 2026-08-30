# RCAEval Baseline Adapter Specification V1

Status: **FROZEN, PERFORMANCE-BLIND**  
Date: 2026-08-30  
RCAEval commit: `5e96b700445bfb5c599e505ecf37d53bf847bbeb`

This specification defines label-free input construction, native invocation,
output validation, and service projection. It contains no evaluation result.

## 1. Common metric adapter

For BARO, CIRCA, MicroCause, CausalRCA, and RCD, load the canonical
`simple_metrics.csv` associated with the opaque case ID. Apply the audited
RCAEval runner transformations in this order:

1. remove columns ending `_latency-50`;
2. on RE2-TT retain `ts-` indicator columns and `time`;
3. replace positive/negative infinity with missing;
4. forward-fill, then fill remaining missing values with zero;
5. retain rows whose integer-second `time` is in `[t0-600,t0+600)`; and
6. rename `_latency-90` suffixes to `_latency`.

Pass `dk_select_useful=False`. The adapter does not apply Ada-RCA binning,
normalization, candidate completion, or feature extraction.

The common RCAEval runner parses the injected service from the source directory
and may override the SLI with `<injected-service>_latency`. That leaks the root
identity into MicroCause's predictive call and is prohibited. The frozen,
label-independent SLI is `frontend_latency` for RE2-OB and
`ts-ui-dashboard_latency` for RE2-TT. `frontend_1` is allowed only as the
native OB schema fallback when `frontend_latency` is absent; it is not selected
from a label or outcome.

## 2. Common raw-trace adapter

For MicroRank and TraceRCA:

1. load raw `traces.csv` for the opaque case ID;
2. require `serviceName`, `methodName`, `operationName`, `startTime`,
   `startTimeMillis`, and `duration`;
3. verify `startTime // 1000 == startTimeMillis` on deterministic unit samples;
4. compute native span end as `startTime + duration`, in microseconds;
5. retain span ends in `[(t0-600)*1e6,(t0+600)*1e6)`;
6. pass `inject_time=t0*1e6`; and
7. allow the native method to fill `methodName`, construct
   `serviceName_methodName`, split on span end, and calculate its own SLO.

The adapter does not pre-bin spans or convert duration to another unit. The
commented `inject_time * 1_000_000` lines in both methods represent a real
seconds/microseconds mismatch in RE2. Passing unconverted `t0` would place every
sampled span on the post-event side and is illegal.

## 3. Common service projection

All ordered indicator/operation outputs use one rule:

- normalize only the frozen official trace alias
  `frontendservice[_...] -> frontend[_...]`;
- match the longest frozen candidate that is exact or followed by `_`;
- retain the first/best native occurrence of each service;
- persist later same-service items as duplicates;
- persist unknown/non-registry items as unmapped and omit them; and
- emit `ADAPTER_FAILURE` if no legal service remains.

The root label is not an adapter argument. No missing service is appended.

## 4. Method contracts

### 4.1 BARO

- **Family:** simple statistical / robust anomaly ranking.
- **Provenance:** official RCAEval
  `RCAEval/e2e/baro.py::baro`, source SHA-256
  `ddaae58b4b03453a812c4af33eb0053d803bcb6132453dd37bfa1f5e675b72c4`.
- **Native input:** common metric adapter output and second-based `t0`.
- **Native processing:** pre/post split at `t0`; separate constant removal;
  intersection of retained pre/post indicators; pre-event `RobustScaler`; rank
  by maximum post-event standardized value.
- **Window:** `WINDOW-ALIGNED`.
- **Native output:** ordered retained indicator list; complete over retained
  indicators, not over legal services; internal scores are not returned.
- **Mapping/candidates:** common projection; completion `NONE`.
- **Metric legality:** AC@1/3/5 and Avg@5 `ADAPTED-BUT-VALID`; MRR
  `NOT-IDENTIFIABLE`.
- **Failures:** exception/empty/invalid output `METHOD_FAILURE`; no decorator
  fallback exists in this path.
- **Randomness:** no explicit RNG in the audited path.

### 4.2 CIRCA

- **Family:** PC causal graph plus regression hypothesis testing.
- **Provenance:** official RCAEval `RCAEval/e2e/circa.py::circa`, source SHA-256
  `2e7c0a4fc860f3401dc1b0b002cb3e3b5d2553d8f79914d942d3041d90984324`.
- **Native input:** common metric adapter output and second-based `t0`.
- **Native processing:** full-window RCAEval preprocessing and PC construction
  with literal graph dataset `"ob"`; RHT then loads one-second values from
  `t0-120` through `t0+300` and internally uses 111 train and 10 test points.
- **Window:** `WINDOW-COMPATIBLE-WITH-NATIVE-INTERNAL-PROCESSING`.
- **Native output:** adjacency matrix, node names, and an ordered subset of
  indicator nodes with RHT scores discarded by the callable.
- **Mapping/candidates:** common projection; completion `NONE`.
- **Metric legality:** AC@1/3/5 and Avg@5 `ADAPTED-BUT-VALID`; MRR
  `NOT-IDENTIFIABLE`.
- **Failures:** RCAEval's `@rca` decorator returns `adj=[]` and preprocessed
  column order after an exception. The adapter detects this exact signature and
  persists `METHOD_FAILURE`.
- **Randomness:** RHT calls `np.random.choice`; canonical seed `20260830`.

### 4.3 MicroCause

- **Family:** temporal causal PCMCI plus random walk.
- **Provenance:** official RCAEval `RCAEval/e2e/microcause.py::microcause`,
  source SHA-256
  `373bbe69b71a7608889169d8b114ed7234b71f70cb31157d195475c3b276855f`;
  the file records lineage from `PanYicheng/dycause_rca` with updates.
- **Native input:** common metric adapter output and the frozen label-independent
  dataset SLI. The entry point does not otherwise use `inject_time`.
- **Native processing:** full supplied series, PCMCI with lag up to 10,
  partial-correlation transition matrix, and random walk.
- **Window:** `WINDOW-ALIGNED` at the source boundary; native processing does
  not split pre/post.
- **Native output:** graph, node names, and a complete ordered list of retained
  indicators; scores are internal and not returned.
- **Mapping/candidates:** common projection; completion `NONE`.
- **Metric legality:** AC@1/3/5 and Avg@5 `ADAPTED-BUT-VALID`; MRR
  `NOT-IDENTIFIABLE`.
- **Failures:** exception, invalid SLI, empty graph/ranking, or invalid
  transition probability is `METHOD_FAILURE`.
- **Randomness:** NumPy random walk; canonical seed `20260830`.

### 4.4 MicroRank

- **Family:** trace coverage graph, PageRank, and spectrum ranking.
- **Provenance:** official RCAEval `RCAEval/e2e/microrank.py::microrank`,
  source SHA-256
  `717be27e7fbe631c9606b8f917c0fb58484c49d37af5fdcd87bdc054660021f8`;
  file header points to `IntelligentDDS/MicroRank`.
- **Native input:** common raw-trace adapter output and microsecond `t0`.
- **Native processing:** span-end split; pre-event operation latency SLO;
  post-event normal/anomalous trace groups; coverage graphs; DStar2.
- **Window:** `WINDOW-COMPATIBLE-WITH-NATIVE-INTERNAL-PROCESSING`.
- **Native output:** capped ordered operation list. The pinned implementation
  calls `top_max=5` but retains indices `< top_max + 6`; the real cap is 11,
  not 5. Internal scores are not returned.
- **Mapping/candidates:** common projection; only the first-five adapted prefix
  identifies top-5 utility; completion `NONE`.
- **Metric legality:** AC@1/3/5 and Avg@5 `ADAPTED-BUT-VALID`; MRR
  `NOT-IDENTIFIABLE`.
- **Failures:** missing pre-event operation SLO, empty graph/list, numerical
  failure, or output longer than 11 is `METHOD_FAILURE`.
- **Randomness:** no explicit entry-point RNG, but unordered sets require worker
  `PYTHONHASHSEED=20260830`.

### 4.5 TraceRCA

- **Family:** trace latency anomaly support/confidence ranking.
- **Provenance:** official RCAEval `RCAEval/e2e/tracerca.py::tracerca`, source
  SHA-256
  `1ef420e4430a7ad0379689c1d18eee9dd7fb0d15ac4371f6ff968900a22b0946`;
  header says refactored from MicroRank, so direct original TraceRCA provenance
  remains ambiguous.
- **Native input:** common raw-trace adapter output and microsecond `t0`.
- **Native processing:** span-end split, pre-event operation SLO, post-event
  abnormal flag, support/confidence harmonic score.
- **Window:** `WINDOW-COMPATIBLE-WITH-NATIVE-INTERNAL-PROCESSING`.
- **Native output:** ordered observed post-event operations with NaN scores
  omitted; scores are not returned; list is partial.
- **Mapping/candidates:** common projection; completion `NONE`.
- **Metric legality:** AC@1/3/5 and Avg@5 `ADAPTED-BUT-VALID`; MRR
  `NOT-IDENTIFIABLE`.
- **Failures:** unseen post-event operation, zero abnormal denominator, empty
  list, or exception is `METHOD_FAILURE`.
- **Randomness:** no explicit RNG in the audited path.

### 4.6 Multi-source BARO (`mmbaro`)

- **Family:** multi-source independent robust anomaly scoring.
- **Provenance:** official RCAEval `RCAEval/e2e/baro.py::mmbaro`, same source
  digest as BARO.
- **Native input:** exact-window metric, `logts`, `tracets_err`, and
  `tracets_lat`; actual raw logs/traces are supplied for required native keys
  but are not consumed. `cluster_info=None` is a non-consumed integration
  placeholder. Dataset key is exactly `mm-ob` or `mm-tt`, enabling the official
  trace branches.
- **Native processing:** metric row stride 15; per-source split at `t0`;
  source-specific constant removal/fill; pre-event `RobustScaler`; two values
  removed from the normal trace-error vector; merged score sort.
- **Window:** `WINDOW-COMPATIBLE-WITH-NATIVE-INTERNAL-PROCESSING`.
- **Native output:** ordered cross-modality indicator list, including possible
  multiple indicators per service; scores are not returned.
- **Mapping/candidates:** common projection; completion `NONE`.
- **Metric legality:** AC@1/3/5 and Avg@5 `ADAPTED-BUT-VALID`; MRR
  `NOT-IDENTIFIABLE`.
- **Failures:** missing consumed key/source, length mismatch, scaler error,
  empty ranking, or no legal mapping is a persisted failure.
- **Randomness:** no explicit RNG in the audited path.

### 4.7 CausalRCA

- **Family:** neural graph learning plus PageRank.
- **Provenance:** official RCAEval `RCAEval/e2e/causalrca.py::causalrca`, source
  SHA-256
  `74aebfb9f8211db3a48385a73ae577e9673a432d719f859771bbf66dc2a008f0`.
- **Native input:** common metric adapter output; the optional dict branch is
  outside this row.
- **Native processing:** per-case max scaling, neural adjacency learning, and
  PageRank over retained indicators.
- **Window:** `WINDOW-ALIGNED`.
- **Native output:** graph, node names, and ordered retained indicators; scores
  are internal and not returned.
- **Mapping/candidates:** common projection; completion `NONE`.
- **Metric legality:** AC@1/3/5 and Avg@5 `ADAPTED-BUT-VALID`; MRR
  `NOT-IDENTIFIABLE`.
- **Failures:** the native empty-graph branch returns input node order. An empty
  adjacency with ranks equal to input node order is `METHOD_FAILURE`.
- **Randomness:** Python/NumPy/Torch seed `20260830`, CPU only, deterministic
  Torch algorithms.

### 4.8 RCD

- **Family:** distribution-change localized PC with an F-node.
- **Provenance:** official RCAEval `RCAEval/e2e/rcd.py::rcd`, source SHA-256
  `e6a7df13e4f3256b45da0713b07b6bf41fb9178333e31397701ab2f08872f628`.
- **Native input:** common metric adapter output and second-based `t0`.
- **Native processing:** pre/post split, separate constant removal, matched
  columns, F-node construction, discretization, random chunks, localized PC.
- **Window:** `WINDOW-ALIGNED`.
- **Native output:** selected indicator ordering; partial; no scores or graph in
  returned artifact.
- **Mapping/candidates:** common projection; completion `NONE`.
- **Metric legality if authorized:** AC@1/3/5 and Avg@5
  `ADAPTED-BUT-VALID`; MRR `NOT-IDENTIFIABLE`.
- **Failures:** method exceptions/empty lists are `METHOD_FAILURE`.
- **Randomness/environment:** NumPy seed `20260830`; official runner routes RCD
  through Python 3.8 and `requirements_rcd.lock`. No compatible frozen venv is
  yet established, so execution remains blocked pending environment audit.

## 5. Context-only contracts

### 5.1 Multi-source CIRCA

No `mmcirca` or equivalent callable implementation exists in the pinned
RCAEval checkout. Metric-only `circa()` cannot be relabeled multi-source.
Inputs, output, window, and metric legality are therefore not established.

### 5.2 PDiagnose

`RCAEval/e2e/pdiagnose.py` exposes only a hard-coded OB demo `main()`, prints a
ranking, uses a whole-file log count without the canonical window, and is not
exported by `e2e/__init__.py`. Turning it into a case callable would be
substantial integration/semantic work. It remains context-only.

### 5.3 Multi-source RCD (`mmrcd`)

The callable indexes metric, log, and trace-derived keys but computes its
ranking from metrics only. Executing it as a multi-source representative would
misstate the consumed evidence, and executing it as metric RCD is scientifically
redundant with the unresolved RCD row. It remains context-only in V1.

## 6. Output and failure invariant

Native output is validated before service mapping. Mapping is validated before
`SUCCESS`. A non-success record carries no native or adapted ranking. Every
selected method must persist one terminal record for every one of the 90 frozen
case IDs before any evaluation phase may begin.
