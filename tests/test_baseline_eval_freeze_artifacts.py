import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "artifacts/baseline_eval/protocol_freeze_v1.json"
MATRIX = ROOT / "artifacts/baseline_eval/execution_matrix_v1.json"


class BaselineEvalFreezeArtifactsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        cls.matrix = json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_freeze_decision_requires_review_and_has_partial_authorization(self):
        self.assertEqual(
            self.protocol["final_decision"],
            "BASELINE_PROTOCOL_FROZEN_PARTIAL_AUTHORIZATION",
        )
        self.assertTrue(self.protocol["performance_blind"])
        self.assertTrue(self.protocol["user_review_required_before_execution"])
        self.assertFalse(self.protocol["performance_firewall"]["baseline_performance_exposed"])

    def test_execution_matrix_and_protocol_have_identical_authorization(self):
        protocol_status = {
            method: row["execution_authorization"]
            for method, row in self.protocol["methods"].items()
        }
        matrix_status = {
            row["method"]: row["execution_authorization"]
            for row in self.matrix["methods"]
        }
        self.assertEqual(protocol_status, matrix_status)
        self.assertEqual(len(protocol_status), 11)
        allowed = {
            "AUTHORIZED_FOR_CONFIRMATORY_EXECUTION",
            "BLOCKED_PENDING_SEMANTIC_AUDIT",
            "BLOCKED_INCOMPATIBLE",
            "CONTEXT_ONLY",
        }
        self.assertTrue(set(protocol_status.values()).issubset(allowed))

    def test_exact_authorized_set_is_frozen(self):
        authorized = {
            method
            for method, row in self.protocol["methods"].items()
            if row["execution_authorization"] == "AUTHORIZED_FOR_CONFIRMATORY_EXECUTION"
        }
        self.assertEqual(
            authorized,
            {"BARO", "CIRCA", "MicroCause", "MicroRank", "TraceRCA", "mmBARO", "CausalRCA"},
        )
        self.assertEqual(
            self.protocol["methods"]["RCD"]["execution_authorization"],
            "BLOCKED_PENDING_SEMANTIC_AUDIT",
        )

    def test_metric_legality_contains_states_not_values(self):
        allowed = {"NATIVE", "ADAPTED-BUT-VALID", "NOT-IDENTIFIABLE"}
        for method in self.protocol["methods"].values():
            legality = method["metric_legality"]
            self.assertEqual(set(legality), {"AC@1", "AC@3", "AC@5", "Avg@5", "MRR"})
            self.assertTrue(set(legality.values()).issubset(allowed))
        encoded = json.dumps(self.protocol, sort_keys=True).lower()
        for forbidden in ('"root_rank"', '"performance_results"', '"observed_metrics"', '"winner"', '"delta"'):
            self.assertNotIn(forbidden, encoded)

    def test_completion_failure_and_denominator_are_frozen(self):
        self.assertEqual(self.protocol["candidate_completion"]["policy"], "NONE")
        self.assertEqual(self.protocol["datasets"]["re2ob"]["case_count"], 90)
        self.assertEqual(self.protocol["datasets"]["re2tt"]["case_count"], 90)
        self.assertEqual(
            set(self.protocol["failure_policy"]["terminal_statuses"]),
            {"SUCCESS", "METHOD_FAILURE", "ADAPTER_FAILURE", "DATA_FAILURE", "TIMEOUT"},
        )
        self.assertFalse(self.protocol["failure_policy"]["successful_subset_allowed"])


if __name__ == "__main__":
    unittest.main()
