# DejaVu Feasibility Audit for RCAEval RE2-OB / RE2-TT

Status: `DEJAVU_NOT_RUN_FEASIBILITY_BLOCKED`

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
The event window is configured as a `(before, after)` window in seconds in the
official configuration; the default is `(10, 10)` and the dataset adds a
five-second extra context on each side
([FDG_config.py, lines 40-49](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/failure_dependency_graph/FDG_config.py#L40-L49),
[dataset.py, lines 30-46](https://github.com/NetManAIOps/DejaVu/blob/d1f082b086cef5597f5301a7b02882b5d0238ebe/DejaVu/dataset.py#L30-L46)).

The official DejaVu input is therefore not equivalent to the frozen Ada-RCA
multimodal RE2 representation. A metric-only adapter could be a clear
external baseline, but it must explicitly document the representation change;
logs, traces, Z1, Z2, morphology, and raw trace graphs must not be added.

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

## 6. Local RE2 provenance and FDG search

The search was restricted to the committed worktree
`/home/zhangll24/RCA_project/Ada-RCA-supervised-baselines` and included
source artifacts, feature manifests, split manifests, scripts, and docs.
The relevant committed evidence is:

| Local artifact | What it establishes | FDG/topology evidence |
|---|---|---|
| `artifacts/source/re2ob/manifest.json:2-49` | 90 cases, 11 candidates, label-sidecar-only input, forbidden input fields, source root | No graph/topology file or graph field |
| `artifacts/source/re2tt/manifest.json:2-106` | 90 cases, 68 candidates, label-sidecar-only input, forbidden input fields, source root | No graph/topology file or graph field |
| `artifacts/source/re2ob/service_registry.json:2-19` | label-free candidate registry derived from simple_metrics CPU/memory entities | Service names only; no edges |
| `artifacts/source/re2tt/service_registry.json:2-20` | label-free candidate registry derived from simple_metrics CPU/memory entities | Service names only; no edges |
| `artifacts/source/re2ob/inputs.jsonl:1-90` | metric/log/trace telemetry URIs and candidate universe | No dependency/FDG field |
| `artifacts/source/re2tt/inputs.jsonl:1-90` | metric/log/trace telemetry URIs and candidate universe | No dependency/FDG field |
| `artifacts/features/re2ob/manifest.json` and `artifacts/features/re2tt/manifest.json` | frozen feature/trajectory inputs | No graph object or edge list |
| `artifacts/splits/re2ob/*` and `artifacts/splits/re2tt/*` | frozen 3-fold OOF assignments | Split records only; no topology |
| `src/rca/rcaeval.py`, `src/rca/features.py`, `docs/REPRESENTATION_FREEZE.md` | current telemetry mapping and frozen representation | Explicitly no topology/graph feature in Ada-RCA representation |

An exhaustive filename and content search found no committed `graph.yml`,
`graphs/*.yml`, GraphML, DOT, NetworkX/DGL graph artifact, service dependency
edge list, or trace-derived dependency graph in this worktree. The committed
RE2 manifests point to external raw-data paths, but those paths are not a
provenance-bound FDG artifact in the worktree and the input manifests expose
telemetry URIs rather than dependency edges. The local `service_registry.json`
files therefore cannot be promoted to FDGs.

No full-connected, random, identity, candidate-order, trace-co-occurrence, or
other synthetic graph was constructed. No legal RE2-to-DejaVu FDG mapping was
identified in the audited local evidence.

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
| RE2 FDG provenance | No committed graph/topology source found | Blocking |

Final decision:

```text
DEJAVU_NOT_RUN_FEASIBILITY_BLOCKED
```

The DejaVu gate has passed, so the audit was authorized. The audit does not
authorize implementation or execution because the current RE2 worktree lacks
a provenance-bound FDG/topology source. Running DejaVu with a synthetic or
arbitrarily inferred graph would no longer be a legally interpretable DejaVu
baseline. The appropriate next action is to obtain and bind an official or
benchmark-provided RE2 service dependency graph (with source identity and
deterministic service-node mapping), then re-audit the dependency environment
and adapter protocol before any training.

## 8. No-run record

- Adapter implementation: not started.
- Graph construction: not performed.
- Dependency installation: not attempted.
- Dataset preparation: not performed.
- Fold smoke test: not performed.
- Training/prediction/metrics: not performed.
- Existing Ada-RCA method and supervised-baseline artifacts: untouched.
