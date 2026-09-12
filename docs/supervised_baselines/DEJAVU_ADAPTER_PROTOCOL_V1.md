# DejaVu RE2 Adapter Protocol V1

Status: `FROZEN BEFORE DEJAVU DATASET PREPARATION OR TRAINING`

Freeze date: 2026-09-12 (Asia/Shanghai)

This is a minimal task adapter for the published DejaVu implementation. It is
not an Ada-RCA extension and does not authorize representation, topology,
architecture, or hyperparameter search.

## 1. Source identity and scope

The only authorized upstream source is:

```text
repository = https://github.com/NetManAIOps/DejaVu.git
commit = d1f082b086cef5597f5301a7b02882b5d0238ebe
license = MIT
```

The checkout is external and read-only. Adapter code may subclass or wrap the
official interfaces, but must not copy-edit the upstream checkout. The method
under evaluation is the official DejaVu GAT path, not its DNN, random-forest,
iSQUAD, JSS20, or other repository baselines.

## 2. Dataset and candidate identity

RE2-OB and RE2-TT remain separate experiments. Candidate services are exactly
the committed registries already used by Ada-RCA and the three generic
supervised comparators:

```text
RE2-OB: 11 candidates
RE2-TT: 68 candidates
```

Each candidate service maps one-to-one to one DejaVu failure instance with
node type `service`. Candidate IDs and final exact-tie order are the canonical
registry order. Every per-event graph and every score vector must contain all
candidates exactly once, including candidates that are isolated in that
event's observed call graph.

## 3. Metric-only feature input

The model feature tensor uses only `simple_metrics.csv` and only the two
indicator families present for every candidate in both datasets:

```text
<candidate>_cpu
<candidate>_mem
```

The metric order is `cpu, mem`. No log values, trace values, Ada-RCA Z1/Z2,
morphology, trace-error, trace-latency, workload, disk, socket, error-rate, or
latency-percentile channel enters the model feature tensor. Raw traces are
used only for the FDG described in Section 4.

For each event and candidate, sample the metric rows at exact 60-second offsets
from `t0 - 600` through `t0 + 540`, producing `candidate x 2 x 20`. Apply the
official forward-fill rule independently within that event and metric series;
the fill state must reset at every event boundary. A missing value is legal
only when an earlier finite value exists in the same event series. Leading
missing values fail closed rather than using another event or a dataset-wide
mean. Then reproduce the remaining applicable official preprocessing: clip
values to `[-10, 10]` and subtract each candidate-metric's mean over the first
10 bins.

This event-local construction prevents telemetry from independent benchmark
runs from being forward-filled across cases. It uses no fitted scaler and no
root label. The input shape and preprocessing are identical for outer-train,
inner-validation, and outer-test events.

## 4. Trace-derived per-event FDG

For each event, read its provenance-bound `traces.csv`. Within each `traceID`,
join every nonempty child `parentSpanID` to the unique parent `spanID` in that
trace. The directed edge is:

```text
parent service -> child service
```

Apply only the frozen RE2-OB alias `frontendservice -> frontend`. Retain an
edge only when both endpoints are different registered candidates. Deduplicate
and lexicographically sort the edge list. Include all canonical candidates as
nodes even if they have no retained edge.

The following are forbidden in the source FDG: labels or condition names in
graph construction, trace co-occurrence edges, inferred transitive edges,
full-connected graphs, identity graphs, random edges, self loops, reverse-edge
completion, and edges added merely to eliminate zero degree. Unmapped trace
services and isolated candidates are reported, not repaired. After the source
FDG is fixed, the official `IncompleteFDGFactory` transformation remains part
of DejaVu: it converts retained edges to bidirectional form and adds self loops
for message passing. These model-internal edges are upstream behavior and are
not reported as trace-derived topology.

The official DGL conversion must be wrapped with an explicit node count for
the `service` type. The single source relation type is
`service-calls-service`, and an empty typed edge tensor is legal. Explicit
node counts preserve isolated candidates through conversion; the unchanged
official factory then supplies the bidirectionality and self loops expected by
the official `GATConv`. No `GATConv` setting is changed.

## 5. Raw-source lock

Before dataset preparation, a committed machine-readable audit must bind all
180 `traces.csv` and 180 `simple_metrics.csv` files by dataset, case ID,
resolved path, byte size, and SHA-256. It must also bind:

- source-registry SHA-256 and candidate-registry SHA-256;
- exact trace headers and required metric columns;
- parent-span join integrity, duplicate-key counts, and conflicting-service
  ambiguity counts;
- retained edge counts and node coverage per case and dataset;
- unmapped trace services and isolated registered candidates.

The audit is label-blind and must never open `labels.jsonl`. Any missing file,
schema mismatch, conflicting-service parent-span key, unfillable leading
metric sample, or candidate-registry mismatch blocks preparation. Repeated
span keys that resolve to the same service and within-event forward-fillable
metric gaps are retained as audit counts but are not ambiguous and do not
block preparation.

## 6. OOF and label firewall

The outer folds are the existing repetition split: repetition 1/2/3 is outer
fold 0/1/2. Each fold has 60 outer-train and 30 outer-test events.

DejaVu uses validation checkpointing, so the two repetitions in outer train
are assigned deterministically:

- the lower-numbered remaining repetition is model-train (30 events);
- the higher-numbered remaining repetition is inner-validation (30 events);
- the held-out repetition remains outer-test (30 events).

Both subsets belong to the authorized 60-case outer train. This split is
fixed without observing performance. The official 40/20/40 split and seed 233
splitter are bypassed by passing explicit event IDs.

Model-train and inner-validation labels may enter loss and validation
checkpoint selection. Outer-test event objects and dataloaders contain metric
tensors, graphs, opaque case IDs, and candidates only. They contain no root,
fault, or condition field. The stock `TestCallback`, which evaluates the test
dataloader during validation, is disabled. Automatic learning-rate search is
disabled. Outer-test labels are loaded only after the final checkpoint has
written a complete outer-test score matrix.

## 7. Frozen DejaVu configuration

Use the official GAT model and published repository defaults where compatible:

```text
seed = 20260826
device = CPU
feature_projector_type = CNN
FI_feature_dim = 3
GAT_layers = 1
GAT_num_heads = 1
GAT_residual = true
GAT_shared_feature_mapper = false
dropout = false
augmentation = false
drop_FDG_edges_fraction = 0
batch_size = 16
test_batch_size = 128
window_size = (10, 10)
optimizer = Adam
init_lr = 0.01
weight_decay = 0.01
max_epoch = 3000
validation_frequency = 10 epochs
early_stopping = true
early_stopping_patience = 500 epochs
checkpoint_metric = validation loss
gradient_clip_value = 1.0
automatic_lr_find = false
```

There is no configuration search. Training loss and validation loss may be
used only by the frozen optimizer and checkpoint/early-stopping rules.
Outer-test metrics never select a checkpoint or change a setting. Numerical
or API repairs may not change features, graph semantics, architecture, loss,
or the values above without a committed protocol deviation.

## 8. Scores, ranking, and evaluation

The selected validation-loss checkpoint emits one finite suspiciousness score
for every canonical service in every outer-test case. Ranking is descending
score with canonical candidate order for exact ties. The adapter writes the
same full row schema as the generic baselines:

```text
case_id, candidate, score, rank, root_service, root_rank, fold, dataset
```

Root fields are joined only after the complete label-free score file exists.
The retained Ada-RCA evaluator computes `AC@1`, `AC@3`, `AC@5`, `Avg@5`, and
`MRR` separately for OB and TT. The official DejaVu test metrics are not used
as the comparison authority.

## 9. Execution stages

1. Generate and validate the raw-source/schema/FDG audit.
2. Create a separate DejaVu environment outside the repository and freeze its
   exact package manifest.
3. Prepare label-free inputs and run one RE2-OB fold-0 smoke test.
4. Review tensor shape, graph completeness, label firewall, loss finiteness,
   ranking completeness, and artifacts without performance-driven changes.
5. If the smoke passes and runtime permits, run six formal folds and aggregate.

Partial execution cannot answer scientific question Q4. A dependency or data
compatibility failure is retained and reported; no substitute method or fake
graph is authorized.
