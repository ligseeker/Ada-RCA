import hashlib
import unittest
from pathlib import Path

from src.rca.evidence_bootstrap import (
    BOOTSTRAP_METRICS,
    LEGACY_BOOTSTRAP_SHA256,
    build_bootstrap_forensic_audit,
    load_frozen_rank_cases,
    paired_fault_stratified_rank_bootstrap,
    validate_pair_alignment,
)


ROOT = Path(__file__).resolve().parents[1]


class EvidenceClosureGate2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = build_bootstrap_forensic_audit(ROOT)

    def _invariants(self):
        for comparison in self.audit["invariants"].values():
            for dataset in comparison["datasets"].values():
                yield dataset

    def test_bootstrap_identity(self):
        for dataset in self._invariants():
            self.assertEqual(dataset["checks"]["identity"], "PASS")
            for metric in BOOTSTRAP_METRICS:
                self.assertEqual(dataset["identity"][metric]["point_delta"], 0.0)
                self.assertEqual(dataset["identity"][metric]["ci95"], [0.0, 0.0])

    def test_bootstrap_antisymmetry(self):
        for dataset in self._invariants():
            self.assertEqual(dataset["checks"]["antisymmetry"], "PASS")
            for metric in BOOTSTRAP_METRICS:
                detail = dataset["antisymmetry"][metric]
                self.assertAlmostEqual(detail["forward_point"], -detail["reverse_point"])
                self.assertAlmostEqual(detail["forward_ci95"][0], -detail["reverse_ci95"][1])
                self.assertAlmostEqual(detail["forward_ci95"][1], -detail["reverse_ci95"][0])

    def test_bootstrap_direct_point_consistency(self):
        for dataset in self._invariants():
            self.assertEqual(dataset["checks"]["direct_point_consistency"], "PASS")
            for detail in dataset["direct_point_consistency"].values():
                self.assertLessEqual(detail["absolute_difference"], detail["tolerance"])

    def test_bootstrap_pairing(self):
        for dataset in self._invariants():
            self.assertEqual(dataset["checks"]["pair_alignment"], "PASS")
            alignment = dataset["pair_alignment"]
            self.assertEqual(alignment["case_count"], 90)
            self.assertTrue(alignment["identical_case_ids"])
            self.assertTrue(alignment["identical_fault_assignments"])
            self.assertTrue(alignment["sampled_case_ids_shared_by_construction"])

        candidate = load_frozen_rank_cases(ROOT, "PER-DATASET-OPT", "re2ob")
        v1 = load_frozen_rank_cases(ROOT, "V1-SCIENTIFIC", "re2ob")
        with self.assertRaises(ValueError):
            validate_pair_alignment(candidate[:-1], v1)

    def test_bootstrap_stratification_accounting(self):
        for dataset in self._invariants():
            self.assertEqual(dataset["checks"]["fault_stratum_accounting"], "PASS")
            accounting = dataset["fault_stratum_accounting"]
            self.assertEqual(set(accounting["original_size_by_stratum"].values()), {15})
            self.assertEqual(set(accounting["bootstrap_size_by_stratum_per_iteration"].values()), {15})
            self.assertEqual(accounting["total_cases_per_iteration"], 90)
            self.assertEqual(accounting["sample_plan_shape"], [10000, 6, 15])

    def test_bootstrap_deterministic_seed(self):
        for dataset in self._invariants():
            self.assertEqual(dataset["checks"]["deterministic_seed"], "PASS")
            detail = dataset["deterministic_seed"]
            self.assertEqual(detail["first_plan_sha256"], detail["repeat_plan_sha256"])

        candidate = load_frozen_rank_cases(ROOT, "PER-DATASET-OPT", "re2tt")
        v1 = load_frozen_rank_cases(ROOT, "V1-SCIENTIFIC", "re2tt")
        first = paired_fault_stratified_rank_bootstrap(candidate, v1, "Avg@5", 100, 20260829)
        second = paired_fault_stratified_rank_bootstrap(candidate, v1, "Avg@5", 100, 20260829)
        self.assertEqual(first, second)

    def test_legacy_artifact_is_unchanged(self):
        path = ROOT / "artifacts/opt/final/bootstrap.json"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), LEGACY_BOOTSTRAP_SHA256)
        forensic = self.audit["legacy_forensic"]
        self.assertTrue(forensic["source_unchanged"])
        self.assertEqual(forensic["discrepancy_classification"], "MULTIPLE_CAUSES")
        self.assertTrue(forensic["causes"]["DOCUMENTATION_DIRECTION_ERROR"].startswith("CONFIRMED"))
        self.assertTrue(forensic["causes"]["ESTIMATOR_MISMATCH"].startswith("CONFIRMED"))
        self.assertTrue(forensic["causes"]["IMPLEMENTATION_ERROR"].startswith("UNRESOLVED"))

        tt_avg5 = forensic["comparison"]["PER-DATASET-OPT"]["datasets"]["re2tt"]["metrics"]["Avg@5"]
        self.assertAlmostEqual(tt_avg5["legacy_point"], 0.006666666666666653)
        self.assertEqual(tt_avg5["legacy_ci95"], [-0.14000000000000004, -0.024444444444444446])
        self.assertFalse(tt_avg5["legacy_ci_matches_candidate_minus_v1_estimator"])
        self.assertFalse(tt_avg5["legacy_ci_matches_v1_minus_candidate_estimator"])

    def test_gate_2_passes_only_with_all_invariants(self):
        self.assertEqual(self.audit["gate_2"]["status"], "PASS")
        self.assertEqual(self.audit["gate_2"]["invariants_status"], "PASS")
        self.assertEqual(self.audit["gate_2"]["legacy_source_immutability"], "PASS")
        self.assertEqual(self.audit["gate_2"]["telemetry_authorization"], "GATE_3_AUTHORIZED")
        for dataset in self._invariants():
            self.assertEqual(dataset["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
