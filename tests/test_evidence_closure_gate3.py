import json
import unittest
from pathlib import Path

import numpy as np

from src.rca.evidence_telemetry import N_BINS, PRE_BINS, indicator_diagnostics


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/evidence_closure/telemetry_information_loss_v1_1.json"


class EvidenceClosureGate3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def test_indicator_zero_scale_diagnostic(self):
        series = np.zeros(N_BINS, dtype=float)
        series[PRE_BINS + 2] = 1.0
        diagnostic = indicator_diagnostics(series)
        self.assertTrue(diagnostic["pre_all_zero"])
        self.assertTrue(diagnostic["pre_constant"])
        self.assertTrue(diagnostic["post_positive"])
        self.assertTrue(diagnostic["post_changed"])
        self.assertTrue(diagnostic["MAD_pre_zero"])
        self.assertTrue(diagnostic["IQR_pre_zero"])
        self.assertFalse(diagnostic["scale_valid"])

    def test_indicator_variable_pre_scale_is_valid(self):
        series = np.zeros(N_BINS, dtype=float)
        series[:PRE_BINS] = np.arange(PRE_BINS, dtype=float)
        series[PRE_BINS:] = np.arange(PRE_BINS, dtype=float) + 1.0
        diagnostic = indicator_diagnostics(series)
        self.assertFalse(diagnostic["pre_all_zero"])
        self.assertFalse(diagnostic["pre_constant"])
        self.assertTrue(diagnostic["scale_valid"])

    def test_candidate_case_funnel_is_monotonic(self):
        order = (
            "eligible",
            "mapped",
            "window_observed",
            "pre_observed",
            "post_observed",
            "scale_valid",
            "feature_active",
        )
        for dataset in self.audit["datasets"].values():
            self.assertEqual(dataset["invariants"]["funnel_monotonic"], "PASS")
            self.assertEqual(
                dataset["invariants"]["feature_active_subset_of_scale_valid"], "PASS"
            )
            for channel in dataset["candidate_case_funnel"].values():
                counts = channel["counts"]
                self.assertTrue(
                    all(counts[order[index]] >= counts[order[index + 1]] for index in range(6))
                )

    def test_dataset_candidate_case_denominators(self):
        expected = {"re2ob": 990, "re2tt": 6120}
        for dataset, denominator in expected.items():
            for channel in self.audit["datasets"][dataset]["candidate_case_funnel"].values():
                self.assertEqual(channel["statistical_unit"], "candidate-case pair")
                self.assertEqual(channel["counts"]["eligible"], denominator)

    def test_trace_error_zero_scale_counts(self):
        ob = self.audit["datasets"]["re2ob"]
        tt = self.audit["datasets"]["re2tt"]
        self.assertEqual(ob["candidate_case_funnel"]["Trace Error"]["counts"]["feature_active"], 0)
        self.assertEqual(tt["candidate_case_funnel"]["Trace Error"]["counts"]["feature_active"], 0)
        self.assertEqual(
            ob["trace_error_diagnostics"]["counts"][
                "pre_all_zero_AND_post_positive_AND_rejected_by_scale"
            ],
            30,
        )
        self.assertEqual(
            tt["trace_error_diagnostics"]["counts"][
                "pre_all_zero_AND_post_positive_AND_rejected_by_scale"
            ],
            0,
        )

    def test_canonical_derived_sources_are_hash_bound(self):
        for dataset in self.audit["datasets"].values():
            provenance = dataset["provenance"]
            self.assertEqual(provenance["used_canonical_derived_files"], 360)
            self.assertTrue(provenance["all_used_files_match_recorded_size_and_sha256"])
            self.assertEqual(provenance["source_file_mismatches"], [])
            self.assertTrue(provenance["source_manifests_match_frozen_commit"])
            self.assertTrue(provenance["feature_artifacts_match_frozen_commit"])

    def test_raw_lineage_limitation_is_explicit(self):
        self.assertEqual(
            self.audit["auditability"]["raw_record_to_derived_cell_lineage"],
            "NOT_FULLY_AUDITABLE_FROM_AVAILABLE_CANONICAL_ARTIFACTS",
        )
        self.assertEqual(
            self.audit["scope"]["raw_record_counts"],
            "NOT_MIXED_WITH_CANDIDATE_CASE_FUNNEL",
        )
        self.assertEqual(self.audit["gate_3"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
