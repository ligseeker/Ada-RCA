"""Label-separated, prediction-visible schema for standalone RCA."""

from dataclasses import dataclass, field
import math
import re
from numbers import Real
from typing import Any, Mapping, Optional, Sequence, Tuple


class SchemaValidationError(ValueError):
    """Raised when an RCA input, label, or collection is invalid."""


_FORBIDDEN_KEYS = frozenset(
    {
        "faultlabel", "faulttype", "groundtruth", "label", "labels",
        "rootcause", "rootindicator", "rootlabel", "rootservice", "target",
        "injectiontarget", "injectionservice", "testrootfrequency",
    }
)


def _normal_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _nonempty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SchemaValidationError("{} must be a non-empty trimmed string".format(field_name))
    return value


def _check_label_free(value: Any, path: str) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normal_key(key) in _FORBIDDEN_KEYS:
                raise SchemaValidationError(
                    "Label Firewall rejected metadata key {!r} at {}".format(key, path)
                )
            _check_label_free(nested, "{}.{}".format(path, key))
    elif isinstance(value, (tuple, list)):
        for index, nested in enumerate(value):
            _check_label_free(nested, "{}[{}]".format(path, index))


def _metadata(value: Mapping[str, Any], path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError("{} must be a mapping".format(path))
    copied = dict(value)
    _check_label_free(copied, path)
    return copied


@dataclass(frozen=True)
class TelemetryRef:
    uri: str
    format: str
    timestamp_column: str
    service_column: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _nonempty(self.uri, "TelemetryRef.uri")
        _nonempty(self.format, "TelemetryRef.format")
        _nonempty(self.timestamp_column, "TelemetryRef.timestamp_column")
        object.__setattr__(self, "metadata", _metadata(self.metadata, "TelemetryRef.metadata"))


@dataclass(frozen=True)
class RCACaseInput:
    case_id: str
    dataset: str
    anchor_time: Real
    services: Tuple[str, ...]
    metrics: Optional[TelemetryRef]
    logs: Optional[TelemetryRef]
    traces: Optional[TelemetryRef]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _nonempty(self.case_id, "RCACaseInput.case_id")
        _nonempty(self.dataset, "RCACaseInput.dataset")
        if isinstance(self.anchor_time, bool) or not isinstance(self.anchor_time, Real):
            raise SchemaValidationError("anchor_time must be numeric")
        if not math.isfinite(float(self.anchor_time)):
            raise SchemaValidationError("anchor_time must be finite")
        if not isinstance(self.services, tuple) or not self.services:
            raise SchemaValidationError("services must be a non-empty tuple")
        for index, service in enumerate(self.services):
            _nonempty(service, "services[{}]".format(index))
        if len(set(self.services)) != len(self.services):
            raise SchemaValidationError("services must not contain duplicates")
        for name in ("metrics", "logs", "traces"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, TelemetryRef):
                raise SchemaValidationError("{} must be TelemetryRef or None".format(name))
        object.__setattr__(self, "metadata", _metadata(self.metadata, "RCACaseInput.metadata"))


@dataclass(frozen=True)
class RCACaseLabel:
    case_id: str
    root_service: str
    fault_type: str

    def __post_init__(self) -> None:
        _nonempty(self.case_id, "RCACaseLabel.case_id")
        _nonempty(self.root_service, "RCACaseLabel.root_service")
        _nonempty(self.fault_type, "RCACaseLabel.fault_type")


def assert_label_free(case_input: RCACaseInput) -> None:
    if not isinstance(case_input, RCACaseInput):
        raise TypeError("prediction pipeline accepts RCACaseInput only")
    _check_label_free(case_input.metadata, "RCACaseInput.metadata")
    for name in ("metrics", "logs", "traces"):
        ref = getattr(case_input, name)
        if ref is not None:
            _check_label_free(ref.metadata, "RCACaseInput.{}.metadata".format(name))


def validate_case_collection(
    inputs: Sequence[RCACaseInput], labels: Optional[Sequence[RCACaseLabel]] = None
) -> None:
    input_ids = [case.case_id for case in inputs]
    if len(input_ids) != len(set(input_ids)):
        raise SchemaValidationError("case_id must be unique in inputs")
    for case in inputs:
        assert_label_free(case)
    if labels is None:
        return
    label_ids = [label.case_id for label in labels]
    if len(label_ids) != len(set(label_ids)) or set(input_ids) != set(label_ids):
        raise SchemaValidationError("input and label case IDs must match exactly")
    inputs_by_id = {case.case_id: case for case in inputs}
    for label in labels:
        if label.root_service not in inputs_by_id[label.case_id].services:
            raise SchemaValidationError(
                "root {!r} is not in candidate services for {!r}".format(
                    label.root_service, label.case_id
                )
            )
