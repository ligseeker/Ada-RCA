import unittest

from src.rca.schema import RCACaseInput, RCACaseLabel, SchemaValidationError, TelemetryRef, validate_case_collection


class LabelFirewallTest(unittest.TestCase):
    def test_nested_label_tokens_rejected(self):
        ref = TelemetryRef("rcaeval://x", "csv", "time")
        with self.assertRaises(SchemaValidationError):
            RCACaseInput("x", "toy", 1, ("a",), ref, ref, ref, {"nested": {"faultType": "cpu"}})

    def test_label_only_sidecar_can_validate(self):
        ref = TelemetryRef("rcaeval://x", "csv", "time")
        case = RCACaseInput("x", "toy", 1, ("a",), ref, ref, ref)
        validate_case_collection((case,), (RCACaseLabel("x", "a", "cpu"),))


if __name__ == "__main__":
    unittest.main()
