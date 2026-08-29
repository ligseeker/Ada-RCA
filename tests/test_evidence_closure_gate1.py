import hashlib
import inspect
import unittest
from pathlib import Path

import src.rca.evidence_closure as evidence_closure
from src.rca.evidence_closure import (
    DATASETS,
    METRIC_TOLERANCE,
    RANK_METRICS,
    aggregate_independent_rank_metrics,
    build_metric_reconstruction,
    classify_evidence_levels,
    independent_case_metrics,
    load_frozen_rank_cases,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SOURCE_SHA256 = {
    ("V1-SCIENTIFIC", "re2ob"): "1d3bbc30869062c30569bd7b752cc2520d8e1337b8861bf11e55bbd69eaf5ff5",
    ("V1-SCIENTIFIC", "re2tt"): "e937897d182735651959ad9449a7d6837ac71b029bec0fe90e143395009dd57d",
    ("GLOBAL-OPT", "re2ob"): "1d3bbc30869062c30569bd7b752cc2520d8e1337b8861bf11e55bbd69eaf5ff5",
    ("GLOBAL-OPT", "re2tt"): "e937897d182735651959ad9449a7d6837ac71b029bec0fe90e143395009dd57d",
    ("PER-DATASET-OPT", "re2ob"): "dd1d6ec06e96e627320f8978f4c2c9deb19c4c7a5b9226e624cb0349accaf7c7",
    ("PER-DATASET-OPT", "re2tt"): "8758769c66809804faf168b2a5e0a4601f0a40990b2c183dcff314780b52b700",
}


class EvidenceClosureGate1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.levels = classify_evidence_levels(ROOT)
        cls.reconstruction = build_metric_reconstruction(ROOT)

    def test_evidence_level_classification(self):
        for dataset in DATASETS:
            for track in ("V1-SCIENTIFIC", "GLOBAL-OPT"):
                level = self.levels[track]["datasets"][dataset]
                self.assertEqual(
                    level["FULL_RANKING_INTEGRITY"]["status"],
                    "FULL_RANKING_INTEGRITY_PASS",
                )
                self.assertEqual(
                    level["RANK_METRIC_SUFFICIENT"]["status"],
                    "RANK_METRIC_SUFFICIENT_PASS",
                )
            per_dataset = self.levels["PER-DATASET-OPT"]["datasets"][dataset]
            self.assertEqual(
                per_dataset["FULL_RANKING_INTEGRITY"]["status"],
                "FULL_RANKING_INTEGRITY_NOT_AUDITABLE",
            )
            self.assertEqual(
                per_dataset["RANK_METRIC_SUFFICIENT"]["status"],
                "RANK_METRIC_SUFFICIENT_PASS",
            )

    def test_immutable_root_rank_source_sha(self):
        for (track, dataset), expected in EXPECTED_SOURCE_SHA256.items():
            level = self.levels[track]["datasets"][dataset]["RANK_METRIC_SUFFICIENT"]
            path = ROOT / level["source_file"]
            self.assertEqual(level["source_sha256"], expected)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
            self.assertEqual(level["checks"]["no_post_audit_root_rank_modification"], "PASS")

    def test_root_rank_range_and_case_integrity(self):
        candidate_counts = {"re2ob": 11, "re2tt": 68}
        for track in ("V1-SCIENTIFIC", "GLOBAL-OPT", "PER-DATASET-OPT"):
            for dataset in DATASETS:
                cases = load_frozen_rank_cases(ROOT, track, dataset)
                self.assertEqual(len(cases), 90)
                self.assertEqual(len({row["case_id"] for row in cases}), 90)
                for row in cases:
                    self.assertIsInstance(row["root_rank"], int)
                    self.assertGreaterEqual(row["root_rank"], 1)
                    self.assertLessEqual(row["root_rank"], candidate_counts[dataset])

    def test_independent_metric_definitions(self):
        rank_one = independent_case_metrics(1)
        self.assertEqual(rank_one, {metric: 1.0 for metric in RANK_METRICS})
        rank_three = independent_case_metrics(3)
        self.assertEqual(rank_three["AC@1"], 0.0)
        self.assertEqual(rank_three["AC@3"], 1.0)
        self.assertEqual(rank_three["AC@5"], 1.0)
        self.assertAlmostEqual(rank_three["Avg@5"], 0.6)
        self.assertAlmostEqual(rank_three["MRR"], 1.0 / 3.0)
        rank_six = independent_case_metrics(6)
        self.assertEqual(rank_six["AC@5"], 0.0)
        self.assertEqual(rank_six["Avg@5"], 0.0)
        self.assertAlmostEqual(rank_six["MRR"], 1.0 / 6.0)
        with self.assertRaises(ValueError):
            independent_case_metrics(0)
        with self.assertRaises(ValueError):
            independent_case_metrics(True)

    def test_independent_aggregation(self):
        metrics = aggregate_independent_rank_metrics(
            ({"root_rank": 1}, {"root_rank": 3}, {"root_rank": 6})
        )
        self.assertAlmostEqual(metrics["AC@1"], 1.0 / 3.0)
        self.assertAlmostEqual(metrics["AC@3"], 2.0 / 3.0)
        self.assertAlmostEqual(metrics["AC@5"], 2.0 / 3.0)
        self.assertAlmostEqual(metrics["Avg@5"], (1.0 + 0.6) / 3.0)
        self.assertAlmostEqual(metrics["MRR"], (1.0 + 1.0 / 3.0 + 1.0 / 6.0) / 3.0)

    def test_implementation_does_not_import_legacy_evaluator(self):
        source = inspect.getsource(evidence_closure)
        self.assertNotIn("from .evaluator import", source)
        self.assertNotIn("from src.rca.evaluator import", source)

    def test_legacy_metric_consistency(self):
        for track in self.reconstruction["tracks"].values():
            for dataset in track["datasets"].values():
                self.assertEqual(dataset["status"], "PASS")
                for metric in RANK_METRICS:
                    detail = dataset["metric_comparison"][metric]
                    self.assertLessEqual(detail["absolute_difference"], METRIC_TOLERANCE)
                    self.assertEqual(detail["status"], "PASS")
        self.assertEqual(self.reconstruction["gate_1"]["status"], "PASS")
        self.assertEqual(
            self.reconstruction["gate_1"]["bootstrap_authorization"],
            "GATE_2_AUTHORIZED",
        )

    def test_amendment_precedes_corrected_outputs(self):
        timing = self.reconstruction["protocol_amendment"]
        self.assertTrue(timing["commit_is_ancestor_of_execution_head"])
        self.assertTrue(all(timing["corrected_outputs_absent_at_amendment_commit"].values()))


if __name__ == "__main__":
    unittest.main()
