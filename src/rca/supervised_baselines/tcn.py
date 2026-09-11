"""Frozen full-trajectory event-level convolutional TCN comparator."""

from pathlib import Path
import random
from typing import Mapping, Sequence

import numpy as np

from .common import SEED, SupervisedEvent, write_json


TCN_CONFIG = {
    "method": "trajectory_tcn",
    "input": "frozen z plus q_mask, candidate x 8 x 80",
    "channel_order": [
        "z.metric", "z.log", "z.trace-error", "z.trace-latency",
        "mask.metric", "mask.log", "mask.trace-error", "mask.trace-latency",
    ],
    "architecture": [
        "Conv1d(8,32,kernel_size=3,padding=1)",
        "ReLU", "Dropout(0.2)",
        "Conv1d(32,64,kernel_size=3,padding=1)",
        "ReLU", "Dropout(0.2)",
        "AdaptiveAvgPool1d(1)", "Linear(64,1)",
    ],
    "loss": "event-level cross entropy over complete candidate axis",
    "optimizer": "Adam",
    "learning_rate": 1e-3,
    "weight_decay": 1e-4,
    "epochs": 100,
    "event_batch_size": 1,
    "random_seed": SEED,
    "dtype": "float32",
    "device": "cpu",
    "torch_num_threads": 1,
    "deterministic_algorithms": True,
    "normalization": "frozen case-local trajectory normalization only; no fold scaler",
    "validation": None,
    "early_stopping": False,
    "checkpoint_selection": "final epoch only",
    "hyperparameter_search": False,
}


def configure_determinism(torch) -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def make_model(torch):
    class TrajectoryTCN(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = torch.nn.Sequential(
                torch.nn.Conv1d(8, 32, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.2),
                torch.nn.Conv1d(32, 64, kernel_size=3, padding=1),
                torch.nn.ReLU(),
                torch.nn.Dropout(0.2),
                torch.nn.AdaptiveAvgPool1d(1),
            )
            self.output = torch.nn.Linear(64, 1)

        def forward(self, values):
            encoded = self.encoder(values).squeeze(-1)
            return self.output(encoded).squeeze(-1)

    return TrajectoryTCN()


def event_probabilities(scores):
    import torch

    if scores.ndim != 1:
        raise ValueError("event scores must have one dimension over candidates")
    return torch.softmax(scores, dim=0)


def fit_tcn(
    train_events: Sequence[SupervisedEvent], train_roots: Mapping[str, str]
):
    import torch

    configure_determinism(torch)
    model = make_model(torch).cpu()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_history = []
    for epoch in range(100):
        model.train()
        generator = torch.Generator(device="cpu")
        generator.manual_seed(SEED + epoch)
        order = torch.randperm(len(train_events), generator=generator).tolist()
        epoch_loss = 0.0
        for index in order:
            event = train_events[index]
            root = train_roots[event.case_id]
            if root not in event.candidates:
                raise ValueError("training root absent from event candidates")
            values = torch.as_tensor(event.trajectory, dtype=torch.float32, device="cpu")
            target = torch.tensor([event.candidates.index(root)], dtype=torch.long, device="cpu")
            optimizer.zero_grad(set_to_none=True)
            scores = model(values)
            if scores.shape != (len(event.candidates),):
                raise ValueError("TCN must return one score per candidate")
            loss = torch.nn.functional.cross_entropy(scores.unsqueeze(0), target)
            if not torch.isfinite(loss):
                raise FloatingPointError("TCN training loss is not finite")
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.detach().cpu())
        mean_loss = epoch_loss / len(train_events)
        if not np.isfinite(mean_loss):
            raise FloatingPointError("TCN epoch loss is not finite")
        loss_history.append(mean_loss)
    return model, tuple(loss_history)


def score_events(model, test_events: Sequence[SupervisedEvent]):
    import torch

    model.eval()
    result = {}
    with torch.no_grad():
        for event in test_events:
            values = torch.as_tensor(event.trajectory, dtype=torch.float32, device="cpu")
            scores = model(values)
            if scores.shape != (len(event.candidates),) or not torch.isfinite(scores).all():
                raise ValueError("TCN prediction scores are incomplete or non-finite")
            result[event.case_id] = scores.cpu().numpy().astype(np.float64)
    return result


def fit_score_and_save(
    train_events: Sequence[SupervisedEvent],
    train_roots: Mapping[str, str],
    test_events: Sequence[SupervisedEvent],
    run_dir: Path,
):
    import torch

    model, loss_history = fit_tcn(train_events, train_roots)
    torch.save(model.state_dict(), str(run_dir / "model_state.pt"))
    write_json(run_dir / "training_loss.json", {
        "epochs": len(loss_history),
        "mean_event_loss_by_epoch": list(loss_history),
        "finite": bool(np.all(np.isfinite(loss_history))),
        "selection_use": "numerical failure audit only; final epoch fixed a priori",
    })
    return score_events(model, test_events)
