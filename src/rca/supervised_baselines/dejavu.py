"""Pinned DejaVu GAT task adapter for prepared RE2 event inputs."""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import random
import sys
from typing import Mapping, Sequence, Tuple

import numpy as np

from .common import SEED, read_json, sha256_file


DEJAVU_COMMIT = "d1f082b086cef5597f5301a7b02882b5d0238ebe"
DEJAVU_CONFIG = {
    "method": "DejaVu official GAT with minimal RE2 task adapter",
    "input": "simple_metrics CPU/MEM, candidate x 2 x 20; trace-derived source FDG",
    "feature_projector_type": "CNN",
    "FI_feature_dim": 3,
    "GAT_layers": 1,
    "GAT_num_heads": 1,
    "GAT_residual": True,
    "GAT_shared_feature_mapper": False,
    "dropout": False,
    "augmentation": False,
    "drop_FDG_edges_fraction": 0.0,
    "batch_size": 16,
    "test_batch_size": 128,
    "window_size": [10, 10],
    "optimizer": "Adam",
    "learning_rate": 1e-2,
    "weight_decay": 1e-2,
    "max_epochs": 3000,
    "validation_frequency_epochs": 10,
    "early_stopping_patience_epochs": 500,
    "checkpoint_metric": "validation loss",
    "gradient_clip_value": 1.0,
    "automatic_lr_find": False,
    "stock_test_callback": False,
    "random_seed": SEED,
    "device": "cpu",
    "normalization": "event-local official clip and pre-window mean subtraction",
    "hyperparameter_search": False,
}


@dataclass(frozen=True)
class PreparedDejaVuEvent:
    case_id: str
    candidates: Tuple[str, ...]
    metric_tensor: np.ndarray
    source_indices: np.ndarray
    destination_indices: np.ndarray

    def __post_init__(self):
        tensor = np.asarray(self.metric_tensor, dtype=np.float32)
        source = np.asarray(self.source_indices, dtype=np.int64)
        destination = np.asarray(self.destination_indices, dtype=np.int64)
        if tensor.shape != (len(self.candidates), 2, 20):
            raise ValueError("DejaVu metric tensor shape mismatch")
        if source.shape != destination.shape or source.ndim != 1:
            raise ValueError("DejaVu graph edge arrays mismatch")
        if not np.all(np.isfinite(tensor)):
            raise ValueError("DejaVu metric tensor must be finite")
        if len(set(self.candidates)) != len(self.candidates):
            raise ValueError("DejaVu candidates must be unique")
        if len(source) and (
            source.min() < 0 or destination.min() < 0
            or source.max() >= len(self.candidates)
            or destination.max() >= len(self.candidates)
        ):
            raise ValueError("DejaVu graph edge index out of range")
        object.__setattr__(self, "metric_tensor", tensor)
        object.__setattr__(self, "source_indices", source)
        object.__setattr__(self, "destination_indices", destination)


def load_prepared_events(project_root: Path, dataset: str) -> Mapping[str, PreparedDejaVuEvent]:
    directory = Path(project_root) / "artifacts" / "supervised_baselines" / "dejavu" / "prepared" / dataset
    manifest = read_json(directory / "manifest.json")
    if manifest["status"] != "PASS" or not manifest["label_free"]:
        raise ValueError("prepared DejaVu manifest is not label-free PASS")
    candidates = tuple(str(value) for value in manifest["candidates"])
    events = {}
    for record in manifest["files"]:
        path = directory / record["path"]
        if sha256_file(path) != record["sha256"]:
            raise ValueError("prepared DejaVu case digest mismatch")
        with np.load(path) as data:
            event = PreparedDejaVuEvent(
                case_id=str(data["case_id"][0]),
                candidates=tuple(str(value) for value in data["candidates"]),
                metric_tensor=data["metric_tensor"],
                source_indices=data["source_indices"],
                destination_indices=data["destination_indices"],
            )
        if event.case_id != record["case_id"] or event.candidates != candidates:
            raise ValueError("prepared DejaVu case identity mismatch")
        events[event.case_id] = event
    if len(events) != 90:
        raise ValueError("prepared DejaVu dataset must contain 90 events")
    return events


def configure_dejavu_runtime(dejavu_root: Path):
    import subprocess
    import torch

    root = Path(dejavu_root).resolve()
    head = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=str(root), text=True).strip()
    dirty = subprocess.check_output(("git", "status", "--porcelain"), cwd=str(root), text=True).strip()
    if head != DEJAVU_COMMIT or dirty:
        raise ValueError("official DejaVu checkout identity/cleanliness mismatch")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    return torch


def _make_graph(torch, event: PreparedDejaVuEvent):
    import dgl

    graph = dgl.graph(
        (
            torch.as_tensor(event.source_indices, dtype=torch.int64),
            torch.as_tensor(event.destination_indices, dtype=torch.int64),
        ),
        num_nodes=len(event.candidates),
    )
    graph.ndata[dgl.NID] = torch.arange(len(event.candidates), dtype=torch.int64)
    return dgl.add_self_loop(dgl.to_bidirected(graph, copy_ndata=True))


def make_official_model(torch, candidate_count: int):
    from DejaVu.models.GAT import GAT

    return GAT(
        node_types=["service"],
        input_features=[torch.Size((candidate_count, 2, 20))],
        feature_size=3,
        feature_projector_type="CNN",
        GAT_layers=1,
        num_heads=1,
        residual=True,
        has_dropout=False,
        shared_feature_mapper=False,
    ).cpu()


def _batch(torch, ids, events, graphs, roots=None):
    tensors = torch.stack([
        torch.as_tensor(events[case_id].metric_tensor, dtype=torch.float32)
        for case_id in ids
    ])
    labels = None
    if roots is not None:
        labels = torch.zeros((len(ids), len(events[ids[0]].candidates)), dtype=torch.float32)
        for row, case_id in enumerate(ids):
            root = roots[case_id]
            labels[row, events[case_id].candidates.index(root)] = 1.0
    return [tensors], [graphs[case_id] for case_id in ids], labels


def _mean_loss(torch, model, ids, events, graphs, roots, batch_size):
    from DejaVu.models.interface.loss import binary_classification_loss

    total = 0.0
    count = 0
    model.eval()
    with torch.no_grad():
        for start in range(0, len(ids), batch_size):
            batch_ids = ids[start:start + batch_size]
            features, batch_graphs, labels = _batch(torch, batch_ids, events, graphs, roots)
            scores = model(features, batch_graphs)
            loss = binary_classification_loss(scores, labels, gamma=0.0)
            if not torch.isfinite(loss):
                raise FloatingPointError("DejaVu validation loss is non-finite")
            total += float(loss) * len(batch_ids)
            count += len(batch_ids)
    return total / count


def train_dejavu(
    events: Mapping[str, PreparedDejaVuEvent],
    train_ids: Sequence[str],
    validation_ids: Sequence[str],
    roots: Mapping[str, str],
    dejavu_root: Path,
    *,
    smoke: bool,
):
    torch = configure_dejavu_runtime(dejavu_root)
    from DejaVu.models.interface.loss import binary_classification_loss

    model = make_official_model(torch, len(next(iter(events.values())).candidates))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-2, weight_decay=1e-2)
    needed_ids = tuple(train_ids) + tuple(validation_ids)
    graphs = {case_id: _make_graph(torch, events[case_id]) for case_id in needed_ids}
    best_state = None
    best_loss = float("inf")
    best_epoch = None
    checks_without_improvement = 0
    history = []
    max_epochs = 1 if smoke else 3000
    for epoch in range(max_epochs):
        generator = torch.Generator(device="cpu")
        generator.manual_seed(SEED + epoch)
        order = torch.randperm(len(train_ids), generator=generator).tolist()
        ordered_ids = [train_ids[index] for index in order]
        model.train()
        epoch_total = 0.0
        epoch_count = 0
        for start in range(0, len(ordered_ids), 16):
            batch_ids = ordered_ids[start:start + 16]
            features, batch_graphs, labels = _batch(torch, batch_ids, events, graphs, roots)
            optimizer.zero_grad(set_to_none=True)
            scores = model(features, batch_graphs)
            loss = binary_classification_loss(scores, labels, gamma=0.0)
            if not torch.isfinite(loss):
                raise FloatingPointError("DejaVu training loss is non-finite")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_total += float(loss.detach()) * len(batch_ids)
            epoch_count += len(batch_ids)
            if smoke:
                break
        training_loss = epoch_total / epoch_count
        should_validate = smoke or (epoch + 1) % 10 == 0
        if should_validate:
            validation_loss = _mean_loss(
                torch, model, tuple(validation_ids), events, graphs, roots, 16
            )
            improved = validation_loss < best_loss
            if improved:
                best_loss = validation_loss
                best_epoch = epoch + 1
                best_state = deepcopy(model.state_dict())
                checks_without_improvement = 0
            else:
                checks_without_improvement += 1
            history.append({
                "epoch": epoch + 1,
                "training_loss": training_loss,
                "validation_loss": validation_loss,
                "checkpoint_improved": improved,
            })
            if not smoke and checks_without_improvement >= 50:
                break
    if best_state is None:
        raise RuntimeError("DejaVu produced no validation checkpoint")
    model.load_state_dict(best_state)
    return model, history, {
        "best_epoch": best_epoch,
        "best_validation_loss": best_loss,
        "epochs_executed": epoch + 1,
        "smoke": smoke,
    }


def score_dejavu(model, events, case_ids, dejavu_root):
    torch = configure_dejavu_runtime(dejavu_root)
    graphs = {case_id: _make_graph(torch, events[case_id]) for case_id in case_ids}
    result = {}
    model.eval()
    with torch.no_grad():
        for start in range(0, len(case_ids), 128):
            batch_ids = tuple(case_ids[start:start + 128])
            features, batch_graphs, _ = _batch(torch, batch_ids, events, graphs)
            scores = model(features, batch_graphs)
            if scores.shape != (len(batch_ids), len(events[batch_ids[0]].candidates)):
                raise ValueError("DejaVu score matrix shape mismatch")
            if not torch.isfinite(scores).all():
                raise ValueError("DejaVu scores must be finite")
            for case_id, values in zip(batch_ids, scores.cpu().numpy()):
                result[case_id] = values.astype(np.float64)
    return result
