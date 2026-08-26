"""Frozen P4-G0 candidate-relative representation and conditional logit."""

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import minimize
from scipy.stats import rankdata
from sklearn.preprocessing import StandardScaler


P4_VARIANTS = ("a0", "a1", "a2", "a3")


@dataclass(frozen=True)
class CandidateEvent:
    case_id: str
    candidates: Tuple[str, ...]
    features: np.ndarray

    def __post_init__(self) -> None:
        values = np.asarray(self.features, dtype=np.float64)
        if values.ndim != 2 or values.shape[0] != len(self.candidates):
            raise ValueError("features must have one row per candidate")
        if len(self.candidates) < 2 or len(set(self.candidates)) != len(self.candidates):
            raise ValueError("candidates must be unique and contain at least two services")
        if not np.all(np.isfinite(values)):
            raise ValueError("P4 features must be finite")
        object.__setattr__(self, "features", values)


@dataclass(frozen=True)
class ConditionalLogitFit:
    weights: np.ndarray
    scaler_mean: np.ndarray
    scaler_scale: np.ndarray
    initial_loss: float
    final_loss: float
    gradient_norm: float
    iterations: int
    converged: bool
    message: str

    def transform(self, values: np.ndarray) -> np.ndarray:
        values = np.asarray(values, dtype=np.float64)
        return (values - self.scaler_mean) / self.scaler_scale

    def scores(self, values: np.ndarray) -> np.ndarray:
        return self.transform(values).dot(self.weights)


def within_event_percentiles(values: np.ndarray) -> np.ndarray:
    """Feature-wise ascending average ranks scaled to [0, 1]."""
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 2 or values.shape[0] < 2:
        raise ValueError("percentiles require a 2-D matrix with at least two candidates")
    if not np.all(np.isfinite(values)):
        raise ValueError("percentile input must be finite")
    ranks = rankdata(values, method="average", axis=0)
    return (ranks - 1.0) / float(values.shape[0] - 1)


def foreign_context_percentiles(values: np.ndarray, context: np.ndarray) -> np.ndarray:
    """Mid-distribution empirical percentiles against a foreign event."""
    values = np.asarray(values, dtype=np.float64)
    context = np.asarray(context, dtype=np.float64)
    if values.ndim != 2 or context.ndim != 2 or values.shape[1] != context.shape[1]:
        raise ValueError("values and context must be 2-D with matching feature counts")
    if context.shape[0] < 1 or not np.all(np.isfinite(values)) or not np.all(np.isfinite(context)):
        raise ValueError("foreign percentile inputs must be finite and non-empty")
    less = np.sum(context[None, :, :] < values[:, None, :], axis=1)
    equal = np.sum(context[None, :, :] == values[:, None, :], axis=1)
    return (less + 0.5 * equal) / float(context.shape[0])


def build_candidate_representation(values: np.ndarray, relative: bool) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if not relative:
        if values.ndim != 2 or not np.all(np.isfinite(values)):
            raise ValueError("absolute features must be a finite 2-D matrix")
        return values.copy()
    return np.concatenate((values, within_event_percentiles(values)), axis=1)


def conditional_logit_loss_gradient(
    weights: np.ndarray,
    event_matrices: Sequence[np.ndarray],
    root_indices: Sequence[int],
    l2_lambda: float = 1.0,
) -> Tuple[float, np.ndarray]:
    weights = np.asarray(weights, dtype=np.float64)
    if len(event_matrices) != len(root_indices) or not event_matrices:
        raise ValueError("event matrices and roots must be non-empty and aligned")
    loss = 0.5 * float(l2_lambda) * float(weights.dot(weights))
    gradient = float(l2_lambda) * weights.copy()
    for matrix, root_index in zip(event_matrices, root_indices):
        matrix = np.asarray(matrix, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != weights.size:
            raise ValueError("event feature dimension mismatch")
        if root_index < 0 or root_index >= matrix.shape[0]:
            raise ValueError("root index outside candidate event")
        scores = matrix.dot(weights)
        maximum = float(np.max(scores))
        exp_scores = np.exp(scores - maximum)
        probabilities = exp_scores / np.sum(exp_scores)
        loss += maximum + float(np.log(np.sum(exp_scores))) - float(scores[root_index])
        gradient += matrix.T.dot(probabilities)
        gradient -= matrix[root_index]
    return float(loss), gradient


def conditional_logit_hessian(
    weights: np.ndarray,
    event_matrices: Sequence[np.ndarray],
    l2_lambda: float = 1.0,
) -> np.ndarray:
    weights = np.asarray(weights, dtype=np.float64)
    hessian = float(l2_lambda) * np.eye(weights.size, dtype=np.float64)
    for matrix in event_matrices:
        scores = matrix.dot(weights)
        probabilities = event_softmax(scores)
        centered = matrix - probabilities.dot(matrix)[None, :]
        hessian += centered.T.dot(probabilities[:, None] * centered)
    return hessian


def event_softmax(scores: np.ndarray) -> np.ndarray:
    scores = np.asarray(scores, dtype=np.float64)
    shifted = scores - np.max(scores)
    values = np.exp(shifted)
    return values / np.sum(values)


def fit_conditional_logit(
    events: Sequence[CandidateEvent],
    roots: Mapping[str, str],
    l2_lambda: float = 1.0,
    max_iter: int = 1000,
    gradient_tolerance: float = 1e-8,
) -> ConditionalLogitFit:
    if not events:
        raise ValueError("cannot fit zero events")
    feature_count = events[0].features.shape[1]
    if any(event.features.shape[1] != feature_count for event in events):
        raise ValueError("all events must have the same feature dimension")
    rows = np.concatenate([event.features for event in events], axis=0)
    scaler = StandardScaler().fit(rows)
    matrices = [scaler.transform(event.features).astype(np.float64) for event in events]
    root_indices = []
    for event in events:
        root = roots[event.case_id]
        if root not in event.candidates:
            raise ValueError("root candidate absent for {}".format(event.case_id))
        root_indices.append(event.candidates.index(root))
    initial = np.zeros(feature_count, dtype=np.float64)
    initial_loss, _ = conditional_logit_loss_gradient(initial, matrices, root_indices, l2_lambda)

    def objective(weights):
        return conditional_logit_loss_gradient(weights, matrices, root_indices, l2_lambda)

    result = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": int(max_iter), "gtol": float(gradient_tolerance), "ftol": 1e-15, "maxls": 50},
    )
    # L-BFGS-B can report relative-function convergence while its projected
    # gradient is above the protocol tolerance.  Deterministic Newton polishing
    # on the same convex objective closes that numerical gap without changing
    # the representation, split, scorer, or regularization.
    polished = np.asarray(result.x, dtype=np.float64).copy()
    for _ in range(32):
        polish_loss, polish_gradient = objective(polished)
        if np.linalg.norm(polish_gradient, ord=np.inf) <= float(gradient_tolerance):
            break
        hessian = conditional_logit_hessian(polished, matrices, l2_lambda)
        try:
            step = np.linalg.solve(hessian, polish_gradient)
        except np.linalg.LinAlgError:
            break
        step_size = 1.0
        while step_size >= 2.0 ** -30:
            candidate = polished - step_size * step
            candidate_loss, _ = objective(candidate)
            if candidate_loss < polish_loss:
                polished = candidate
                break
            step_size *= 0.5
        else:
            break
    final_loss, final_gradient = objective(polished)
    return ConditionalLogitFit(
        weights=polished,
        scaler_mean=np.asarray(scaler.mean_, dtype=np.float64),
        scaler_scale=np.asarray(scaler.scale_, dtype=np.float64),
        initial_loss=float(initial_loss),
        final_loss=float(final_loss),
        gradient_norm=float(np.linalg.norm(final_gradient, ord=np.inf)),
        iterations=int(result.nit),
        converged=bool(result.success) and float(np.linalg.norm(final_gradient, ord=np.inf)) <= float(gradient_tolerance),
        message=str(result.message) + "; Newton polish gradient_inf={:.3e}".format(float(np.linalg.norm(final_gradient, ord=np.inf))),
    )


def rank_candidates(candidates: Sequence[str], scores: np.ndarray) -> Tuple[str, ...]:
    if len(candidates) != len(scores) or len(set(candidates)) != len(candidates):
        raise ValueError("candidate scores must be complete and unique")
    order = sorted(range(len(candidates)), key=lambda index: (-float(scores[index]), str(candidates[index])))
    return tuple(candidates[index] for index in order)


def fit_predict_oof(
    raw_events: Mapping[str, CandidateEvent],
    roots: Mapping[str, str],
    fold_assignments: Mapping[str, int],
    relative: bool,
    l2_lambda: float = 1.0,
    max_iter: int = 1000,
    gradient_tolerance: float = 1e-8,
) -> Tuple[Tuple[Mapping[str, object], ...], Mapping[int, ConditionalLogitFit]]:
    if set(raw_events) != set(roots) or set(raw_events) != set(fold_assignments):
        raise ValueError("events, roots, and split assignments must align exactly")
    represented = {
        case_id: CandidateEvent(event.case_id, event.candidates, build_candidate_representation(event.features, relative))
        for case_id, event in raw_events.items()
    }
    predictions = []
    fits: Dict[int, ConditionalLogitFit] = {}
    for fold in (0, 1, 2):
        train = [represented[case_id] for case_id in sorted(represented) if fold_assignments[case_id] != fold]
        test = [represented[case_id] for case_id in sorted(represented) if fold_assignments[case_id] == fold]
        if not train or not test:
            raise ValueError("every fold must have train and test events")
        fit = fit_conditional_logit(train, roots, l2_lambda, max_iter, gradient_tolerance)
        fits[fold] = fit
        for event in test:
            scores = fit.scores(event.features)
            predictions.append({
                "case_id": event.case_id,
                "fold": fold,
                "candidate_scores": {candidate: float(scores[index]) for index, candidate in enumerate(event.candidates)},
                "ranking": list(rank_candidates(event.candidates, scores)),
            })
    return tuple(sorted(predictions, key=lambda row: row["case_id"])), fits


def permute_event(event: CandidateEvent, permutation: Sequence[int]) -> CandidateEvent:
    permutation = np.asarray(permutation, dtype=int)
    if sorted(permutation.tolist()) != list(range(len(event.candidates))):
        raise ValueError("permutation must contain each candidate index once")
    return CandidateEvent(
        event.case_id,
        tuple(event.candidates[index] for index in permutation),
        event.features[permutation],
    )


def verify_complete_prediction(row: Mapping[str, object], candidates: Sequence[str], root: Optional[str] = None) -> None:
    ranking = tuple(row["ranking"])
    scores = row["candidate_scores"]
    if len(ranking) != len(candidates) or set(ranking) != set(candidates) or len(set(ranking)) != len(ranking):
        raise ValueError("prediction ranking is incomplete or duplicated")
    if set(scores) != set(candidates):
        raise ValueError("candidate score map is incomplete")
    if root is not None and root not in ranking:
        raise ValueError("root candidate absent from prediction")
