# DejaVu Feasibility Audit for RCAEval RE2-OB / RE2-TT

Status: `DEJAVU_FEASIBILITY_CONDITIONAL_PASS — PREIMPLEMENTATION_LOCKS_REQUIRED`

Audit date: 2026-09-12 (Asia/Shanghai)

Audit scope: read-only compatibility and provenance audit. No DejaVu adapter,
graph construction, model training, prediction, or metric computation was
performed.

## 1. Audit identity and evidence policy

The official repository was fetched from
`https://github.com/NetManAIOps/DejaVu.git` at the current remote `HEAD` on
2026-09-12. The resolved commit is:

```text
d1f082b086cef5597f5301a7b02882b5d0238ebe
```

The official checkout was clean. No release tag was present in the fetched
repository; therefore this commit, rather than an inferred version number, is
the audited source identity. All official-code claims below link to this
commit. The official README describes the Docker image, data layout, usage,
and published output fields ([README.md, lines 16-56](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/README.md#L16-L56)).

The audit uses only official DejaVu repository files for DejaVu behavior and
the committed Ada-RCA worktree artifacts for RE2 input/provenance facts. No
secondary implementation or undocumented topology inference is used.

## 2. License and dependency audit

### License

The official repository contains an MIT license, including the requirement to
retain the copyright and permission notices in copies or substantial portions
([LICENSE](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/LICENSE#L1-L21)).

### Runtime dependencies

The official `requirements.txt` requires Torch, DGL approximately 0.8,
NetworkX 2.6.3, Pandas 1.4, scikit-learn 1.0, NumPy 1.21, SciPy 1.6.3,
PyYAML, pygraphviz/Graphviz, PyTorch Lightning, tsfresh, and other packages
([requirements.txt, lines 1-35](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/requirements.txt#L1-L35)).
The README specifically states that DGL 0.8 was installed manually from
source at the time and that PyTorch should be at least 1.11
([README.md, lines 16-31](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/README.md#L16-L31)).

This is a material environment risk for the current Python 3.8.20 / PyTorch
1.12.0 project environment: the requested DGL/PyTorch-Lightning/pygraphviz
stack is not part of the generic supervised-baseline environment freeze. No
dependency installation was attempted during this audit.

## 3. Official input telemetry and representation

The official DejaVu path is metric-only. `MetricPreprocessor` expects an FDG
metrics dataframe with `timestamp`, `value`, and `name` columns and constructs
per-failure-class tensors of shape
`(n_failure_instance, n_metrics, n_timestamps)`
([metric_preprocessor.py, lines 20-69](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/metric_preprocess/metric_preprocessor.py#L20-L69)).
The default preprocessing uses 60-second granularity, forward-fills missing
values, fills remaining missing values with a metric mean (or `-10`), and
clips values to `[-10, 10]`
([metric_preprocessor.py, lines 136-209](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/metric_preprocess/metric_preprocessor.py#L136-L209)).
The event window is configured as `(before, after)` counts of time bins. The
official default is `(10, 10)`, the dataset adds five additional bins on each
side, and the default granularity is 60 seconds
([FDG_config.py, lines 40-49](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/FDG_config.py#L40-L49),
[dataset.py, lines 30-46](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/dataset.py#L30-L46)).

The official DejaVu input is therefore not equivalent to the frozen Ada-RCA
multimodal RE2 representation. A metric-only adapter can be a clear external
baseline, but it must explicitly document the representation change. Logs,
Z1, Z2, morphology, and trace values must not enter the feature tensor. Raw
traces may be used only to derive the required service-dependency edges, as
expressly allowed by the supervised-baseline protocol.

## 4. Failure instance, FDG, and root-label semantics

### Failure instances and candidate universe

In the official implementation, a failure instance is an FDG node. The FDG
requires either one overall NetworkX graph or one graph per failure, and each
node is expected to carry a `type` and a list of metric names
([failure_dependency_graph.py, lines 28-58](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/failure_dependency_graph.py#L28-L58)).
The FDG maps node names to global instance IDs (`gid`) and exposes the number
of failure instances and their class grouping
([failure_dependency_graph.py, lines 293-343](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/failure_dependency_graph.py#L293-L343)).

The official README says the expected dataset directory contains
`graph.yml` or `graphs/*.yml`, `metrics.csv`, and `faults.csv`; the latter
contains failures and ground truths, with `FDG.pkl` as an optional cache
([README.md, lines 61-68](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/README.md#L61-L68)).

### Root labels

The official `faults.csv` schema uses a `root_cause_node` field. The dataset
creates a vector with one position per FDG failure instance and sets the
positions corresponding to `root_cause_node` (supporting semicolon-separated
multiple roots)
([dataset.py, lines 77-99](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/dataset.py#L77-L99)).
The FDG helper returns those root instance names by splitting the same field
([failure_dependency_graph.py, lines 409-424](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/failure_dependency_graph.py#L409-L424)).

This can represent the current RE2 `root_service` label only if every RE2
candidate service has a provenance-bound one-to-one mapping to an FDG failure
instance. A root label cannot be used to invent the missing graph or to assign
an arbitrary FDG node ID.

### FDG construction and graph use

The official YAML parser creates typed nodes with metric lists and typed
directed edges
([parse_yaml_graph_config.py, lines 20-86](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/parse_yaml_graph_config.py#L20-L86)).
The GAT model obtains a per-failure graph, uses the graph's retained node IDs,
and performs message passing with DGL before assigning one score to each
candidate instance ([GAT.py, lines 16-77](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/models/GAT.py#L16-L77)).
Consequently, an FDG is a required model input, not an optional explanatory
artifact.

## 5. Official split, training, and ranking output

The official split is not the current Ada-RCA OOF split. `FDGBaseConfig`
defaults to `(0.4, 0.2, 0.4)` train/validation/test ratio
([FDG_config.py, lines 22-35](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/FDG_config.py#L22-L35)).
`split_failures_by_type` groups failures by root-cause class, shuffles each
group with NumPy seed `233`, and then takes the ratio slices
([model_interface.py, lines 193-271](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/model_interface.py#L193-L271)).
The official model interface then builds separate datasets from those IDs
([DejaVu model_interface.py, lines 39-83](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/models/interface/model_interface.py#L39-L83)).

The current fair protocol requires each outer fold to use the already frozen
60-case train and 30-case test assignments, with any validation split made
only inside the 60-case outer train. This is technically feasible because the
official dataset constructor accepts explicit `fault_ids`
([dataset.py, lines 30-50](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/dataset.py#L30-L50)).
However, the adapter would need to replace/bypass the official
fault-type-derived split and ensure that outer-test labels are not used for
checkpoint selection, early stopping, feature processing, or any model
choice. Reusing the official 40/20/40 split would not satisfy the current
OOF protocol.

There is an additional label-firewall incompatibility in the stock workflow.
It installs `TestCallback` in the training callback list
([workflow.py, lines 60-74](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/workflow.py#L60-L74)); that callback invokes the test dataloader during
validation epochs
([callbacks.py, lines 110-145](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/models/interface/callbacks.py#L110-L145)).
The RE2 adapter must disable this callback and must not expose the outer-test
labels to the trainer. It must also disable automatic learning-rate search and
use a preregistered fixed configuration. Outer-test labels may be joined only
after a fold's complete score matrix has been persisted.

The native neural path uses a supervised per-node score vector and the
official loss consumes the root-node multi-hot vector. Its evaluation sorts
all candidate IDs by descending score. The test workflow explicitly builds a
`(n_test_failures, n_failure_instances)` score matrix and returns a complete
descending candidate-ID list ([workflow.py, lines 157-190](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/workflow.py#L157-L190)).
The official metrics are `A@1`, `A@2`, `A@3`, `A@5`, and `MAR`
([evaluation_metrics.py, lines 8-59](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/evaluation_metrics.py#L8-L59)).
An adapter could deterministically map the complete service ranking to the
current evaluator's `AC@1`, `AC@3`, `AC@5`, `Avg@5`, and `MRR`, but this would
be an evaluation-layer conversion rather than an official DejaVu metric.

## 6. Local RE2 provenance and FDG audit

No prebuilt `graph.yml`, GraphML, DOT, NetworkX/DGL artifact, or benchmark
edge list exists in this worktree. That absence is not itself a feasibility
blocker: the committed `artifacts/source/<dataset>/sources.jsonl` records bind
each of the 180 canonical cases to a raw `traces.csv`, and every inspected raw
trace has the fields needed for a deterministic service-call graph:

```text
traceID, spanID, serviceName, parentSpanID
```

The admissible conversion is fixed conceptually as follows. Within each
`traceID`, join a child row's `parentSpanID` to the parent row's `spanID`, map
the two `serviceName` values into the frozen candidate registry, retain only
cross-service edges whose endpoints are registered candidates, deduplicate
and sort edges deterministically, and include every candidate as a node even
when it has no observed edge. RE2-OB must reuse the already frozen
`frontendservice -> frontend` alias from `src/rca/features.py`; no new alias may
be learned from labels. Trace values do not become model features.

This is a trace-derived dependency graph, not a co-occurrence graph: an edge
exists only when an explicit parent span calls a child span. It does not permit
full-connected, random, identity, registry-order, inferred co-occurrence, or
self-loop completion. Candidates absent from the observed trace call graph
remain isolated nodes rather than receiving fabricated edges.

The official FDG loader supports per-failure graphs named from each failure
timestamp
([failure_dependency_graph.py, lines 189-215](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/failure_dependency_graph.py#L189-L215)), so one deterministic graph per RE2 event is compatible with the
official data model. However, the official DGL conversion constructs the
heterograph from edge tensors without an explicit `num_nodes_dict`
([failure_dependency_graph.py, lines 482-497](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/failure_dependency_graph.py#L482-L497)). The adapter must therefore make the smallest compatibility repair needed
to preserve the complete candidate node universe, including isolated nodes;
it must not repair isolation by inventing edges.

Before implementation, the raw source bytes and conversion semantics still
need a committed lock. That lock must cover all 180 trace sources and the
metric-only input sources by path, size, and SHA-256; verify the exact trace
schema and candidate mapping; and report coverage and unmapped names without
consulting root labels. The committed source registry supplies provenance,
but currently stores paths rather than content digests.

## 7. Feasibility decision

| Audit item | Finding | Decision |
|---|---|---|
| Official source identity | Current remote `HEAD` = `d1f082b...` | Reproducible source identity recorded |
| License | MIT | Compatible subject to notice retention |
| Python/PyTorch/DGL stack | Legacy DGL ~0.8 plus Torch >=1.11 and graph dependencies | Requires isolated environment audit before any run |
| Telemetry | Metric time series, class/instance tensorization, official imputation/clip | Metric-only adapter is conceptually possible |
| Failure instances | FDG nodes with typed metrics and global IDs | Requires explicit service-to-instance mapping |
| Root labels | `root_cause_node` multi-hot node labels | RE2 root-service mapping requires graph instance identity |
| Official split | Stratified per fault type, 40/20/40, RNG seed 233 | Must be replaced by current 60/30 outer OOF |
| Ranking output | Complete descending instance-ID ranking | Output conversion is feasible after legal mapping |
| RE2 FDG provenance | No prebuilt graph; committed raw traces contain explicit parent-child spans | Conditionally feasible after content and conversion lock |

Final decision:

```text
DEJAVU_FEASIBILITY_CONDITIONAL_PASS
```

The DejaVu gate passed and a legally interpretable, trace-derived graph source
exists. Implementation remains conditional on a performance-blind source
digest/conversion lock, an isolated dependency environment, preservation of
all candidate nodes, and removal of the stock workflow's outer-test callback.
These are compatibility and protocol controls, not model or topology search.

## 8. No-run record

- Adapter implementation: not started.
- Graph construction: not performed; deterministic conversion semantics are
  identified but not yet locked or executed.
- Dependency installation: not attempted.
- Dataset preparation: not performed.
- Fold smoke test: not performed.
- Training/prediction/metrics: not performed.
- Existing Ada-RCA method and supervised-baseline artifacts: untouched.

The required next stage is to commit `DEJAVU_ADAPTER_PROTOCOL_V1.md` and the
raw-source digest/schema audit before writing the adapter. Only then may an
isolated-environment dataset-preparation smoke test begin.
