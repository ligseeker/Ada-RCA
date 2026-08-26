import unittest

from src.rca.schema import (
    RCACaseInput,
    RCACaseLabel,
    SchemaValidationError,
    TelemetryRef,
    validate_case_collection,
)


def make_input(metadata=None, services=("a", "b")):
    ref = TelemetryRef("rcaeval://opaque/metrics", "csv", "time", metadata={})
    return RCACaseInput("case-1", "toy", 100.0, services, ref, ref, ref, metadata or {})


class SchemaTest(unittest.TestCase):
    def test_root_candidate_invariant(self):
        with self.assertRaises(SchemaValidationError):
            validate_case_collection((make_input(),), (RCACaseLabel("case-1", "not-a", "cpu"),))

    def test_label_metadata_is_rejected(self):
        with self.assertRaises(SchemaValidationError):
            make_input({"root_service": "a"})

    def test_duplicate_candidates_are_rejected(self):
        with self.assertRaises(SchemaValidationError):
            make_input(services=("a", "a"))

    def test_input_label_separation(self):
        case = make_input()
        label = RCACaseLabel(case.case_id, "a", "cpu")
        validate_case_collection((case,), (label,))
        self.assertFalse(hasattr(case, "root_service"))


if __name__ == "__main__":
    unittest.main()
