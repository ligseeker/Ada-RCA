"""Non-invasive CausalRCA runtime diagnostics and output classification.

The historical CausalRCA records do not retain the adjacency matrix or the
PageRank exception.  This module provides a human-invoked diagnostic seam for
future evidence collection.  It never changes the return value or exception
behavior of the patched PageRank implementation.
"""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from typing import Any, Iterator, Mapping, MutableSequence

import numpy as np


CAUSALRCA_FAILURE_STATUS = "METHOD_FAILURE"
CAUSALRCA_SUCCESS_STATUS = "SUCCESS"
CAUSALRCA_UNRESOLVED_STATUS = "UNRESOLVED_SILENT_FALLBACK"


def _sha256_json(value: Any) -> str:
    import json

    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def summarize_matrix(matrix: Any) -> dict[str, Any]:
    """Summarize a PageRank input without retaining the matrix values."""

    array = np.asarray(matrix)
    summary: dict[str, Any] = {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "size": int(array.size),
        "nonzero_count": int(np.count_nonzero(array)) if array.size else 0,
    }
    summary["density"] = (
        summary["nonzero_count"] / summary["size"] if summary["size"] else 0.0
    )
    if array.size and np.issubdtype(array.dtype, np.number):
        finite = np.isfinite(array)
        summary["finite"] = bool(finite.all())
        if bool(finite.any()):
            finite_values = array[finite]
            summary["min"] = float(finite_values.min())
            summary["max"] = float(finite_values.max())
    else:
        summary["finite"] = None
    return summary


def summarize_scores(scores: Any) -> dict[str, Any]:
    """Summarize PageRank scores while preserving no score vector."""

    array = np.asarray(scores)
    flattened = array.reshape(-1)
    summary: dict[str, Any] = {
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "count": int(flattened.size),
        "digest": _sha256_json(flattened.tolist()),
        "unique_count": int(np.unique(flattened).size) if flattened.size else 0,
    }
    if flattened.size and np.issubdtype(flattened.dtype, np.number):
        finite = np.isfinite(flattened)
        summary["finite"] = bool(finite.all())
        if bool(finite.any()):
            finite_values = flattened[finite]
            summary["min"] = float(finite_values.min())
            summary["max"] = float(finite_values.max())
            summary["std"] = float(finite_values.std())
    else:
        summary["finite"] = None
    return summary


class PageRankRecorder:
    """Append-only diagnostic event collector for one process."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def record_call(self, matrix: Any) -> None:
        self.events.append({
            "event": "pagerank_called",
            "matrix": summarize_matrix(matrix),
        })

    def record_success(self, scores: Any) -> None:
        self.events.append({
            "event": "pagerank_success",
            "scores": summarize_scores(scores),
        })

    def record_exception(self, exc: BaseException) -> None:
        self.events.append({
            "event": "pagerank_exception",
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        })


@contextmanager
def instrument_pagerank(
    page_rank_class: type[Any], recorder: PageRankRecorder
) -> Iterator[None]:
    """Patch only ``fit_transform`` and restore it unconditionally.

    The original method is called with the original arguments.  A successful
    return is passed through unchanged, and an exception is recorded and
    re-raised unchanged so the pinned CausalRCA ``try/except`` owns fallback
    behavior exactly as it would without instrumentation.
    """

    original = page_rank_class.fit_transform

    def wrapped(self: Any, matrix: Any, *args: Any, **kwargs: Any) -> Any:
        recorder.record_call(matrix)
        try:
            result = original(self, matrix, *args, **kwargs)
        except BaseException as exc:
            recorder.record_exception(exc)
            raise
        recorder.record_success(result)
        return result

    page_rank_class.fit_transform = wrapped
    try:
        yield
    finally:
        page_rank_class.fit_transform = original


def classify_causalrca_output(
    *,
    returned_ranks: Any,
    node_names: Any,
    adjacency: Any,
    pagerank_exception_observed: bool = False,
    fallback_signature_observed: bool = False,
) -> dict[str, Any]:
    """Classify diagnostics without treating order equality as proof of failure.

    Equality between ``returned_ranks`` and ``node_names`` is reported as a
    signature, but is not itself a failure.  A PageRank exception or an
    independently observed fallback branch is required for a diagnostic
    ``METHOD_FAILURE`` classification.
    """

    ranks = list(returned_ranks) if isinstance(returned_ranks, (list, tuple)) else []
    names = list(node_names) if isinstance(node_names, (list, tuple)) else []
    try:
        adjacency_array = np.asarray(adjacency)
        adjacency_empty = adjacency_array.size == 0 or not bool(np.any(adjacency_array))
    except (TypeError, ValueError):
        adjacency_empty = None
    order_signature = ranks == names and bool(ranks)
    if pagerank_exception_observed or fallback_signature_observed:
        status = CAUSALRCA_FAILURE_STATUS
        reason = (
            "PageRank exception observed"
            if pagerank_exception_observed
            else "fallback branch independently observed"
        )
    elif not ranks:
        status = CAUSALRCA_FAILURE_STATUS
        reason = "returned ranking is empty or malformed"
    elif order_signature and adjacency_empty:
        status = CAUSALRCA_UNRESOLVED_STATUS
        reason = "order/empty-graph signature without runtime trigger evidence"
    else:
        status = CAUSALRCA_SUCCESS_STATUS
        reason = "no diagnostic failure trigger observed"
    return {
        "classification": status,
        "reason": reason,
        "ranks_equal_node_names": order_signature,
        "adjacency_empty_or_zero": adjacency_empty,
        "runtime_trigger_required_for_failure": True,
    }


__all__ = [
    "CAUSALRCA_FAILURE_STATUS",
    "CAUSALRCA_SUCCESS_STATUS",
    "CAUSALRCA_UNRESOLVED_STATUS",
    "PageRankRecorder",
    "classify_causalrca_output",
    "instrument_pagerank",
    "summarize_matrix",
    "summarize_scores",
]
