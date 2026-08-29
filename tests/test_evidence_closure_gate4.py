import json
import unittest
from pathlib import Path

from src.rca.evidence_provenance import build_provenance_normalization


ROOT = Path(__file__).resolve().parents[1]


class EvidenceClosureGate4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = build_provenance_normalization(ROOT)

    def test_historical_reference_is_recovered_not_replayed(self):
        historical = self.audit["historical_reference"]
        self.assertEqual(historical["status"], "PASS")
        self.assertEqual(historical["normalized_term"], "HIST-BEST-RECOVERED-REFERENCE")
        self.assertEqual(
            historical["required_qualifier"],
            "Recovered legacy result; not canonically replayed; not an unbiased comparator.",
        )
        self.assertEqual(historical["evidence"]["replay_capable_historical_files"], [])
        self.assertTrue(historical["legacy_artifacts_match_frozen_commit"])

    def test_ranker_execution_semantics(self):
        rankers = self.audit["ranker_execution"]
        self.assertEqual(
            rankers["canonical_status"],
            {
                "Conditional Logit": "EXECUTED",
                "XGBoost": "NOT EXECUTED — DEPENDENCY UNAVAILABLE",
                "LightGBM": "NOT EXECUTED — DEPENDENCY UNAVAILABLE",
            },
        )
        self.assertEqual(rankers["selection_trace_rankers"], ["R0-ConditionalLogit"])
        self.assertTrue(rankers["only_conditional_logit_in_selection_trace"])

    def test_errata_contains_required_claim_boundaries(self):
        errata = (ROOT / "docs/EVIDENCE_ERRATA.md").read_text(encoding="utf-8")
        self.assertIn("HIST-BEST-RECOVERED-REFERENCE", errata)
        self.assertIn(
            "Recovered legacy result; not canonically replayed; not an unbiased comparator.",
            errata,
        )
        self.assertIn("NO_EXPLICIT_LABEL_LEAKAGE_DETECTED", errata)

    def test_gate_4_passes(self):
        self.assertEqual(self.audit["gate_4"]["status"], "PASS")
        self.assertEqual(
            self.audit["gate_4"]["final_decision_authorization"],
            "GATE_5_AUTHORIZED",
        )


if __name__ == "__main__":
    unittest.main()
