import json
import unittest
from pathlib import Path

from src.rca.evidence_semantics import (
    FAIL,
    NOT_AUDITABLE,
    PASS,
    build_evidence_semantic_correction,
    semantic_status,
)


ROOT = Path(__file__).resolve().parents[1]


class EvidenceGate5SemanticsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = build_evidence_semantic_correction(ROOT)

    def test_pass_fail_not_auditable_are_distinct(self):
        self.assertEqual(
            semantic_status(evidence_exists=True, condition_verified=True), PASS
        )
        self.assertEqual(
            semantic_status(evidence_exists=True, condition_verified=False), FAIL
        )
        self.assertEqual(
            semantic_status(evidence_exists=False, condition_verified=None),
            NOT_AUDITABLE,
        )
        with self.assertRaises(ValueError):
            semantic_status(evidence_exists=True, condition_verified=None)

    def test_per_dataset_full_ranking_limitation_is_preserved(self):
        for dataset in ("re2ob", "re2tt"):
            record = self.audit["tracks"]["PER-DATASET-OPT"]["datasets"][dataset]
            self.assertEqual(
                record["FULL_RANKING_INTEGRITY"],
                "FULL_RANKING_INTEGRITY_NOT_AUDITABLE",
            )
            for check in record["ranking_object_checks"].values():
                self.assertEqual(check["status"], NOT_AUDITABLE)

    def test_per_dataset_rank_metric_sufficiency_is_preserved(self):
        expected_passes = {
            "case_coverage",
            "fold_provenance",
            "root_mapping",
            "root_belongs_to_registry",
            "root_rank_integer",
            "root_rank_range",
            "root_rank_artifact_immutability",
            "sha_and_commit_provenance",
            "no_model_refit_required",
        }
        for dataset in ("re2ob", "re2tt"):
            record = self.audit["tracks"]["PER-DATASET-OPT"]["datasets"][dataset]
            self.assertEqual(
                record["RANK_METRIC_SUFFICIENT"],
                "RANK_METRIC_SUFFICIENT_PASS",
            )
            self.assertEqual(set(record["direct_root_rank_checks"]), expected_passes)
            self.assertTrue(
                all(
                    check["status"] == PASS
                    for check in record["direct_root_rank_checks"].values()
                )
            )

    def test_historical_failures_are_semantically_corrected(self):
        statuses = {
            (row["historical_check"], row["canonical_status"])
            for row in self.audit["corrections"]
        }
        self.assertIn(
            ("immutable_complete_candidate_ranking", NOT_AUDITABLE), statuses
        )
        self.assertIn(
            ("valid_fold_and_case_provenance", PASS), statuses
        )
        self.assertTrue(
            all(row["historical_status"] == FAIL for row in self.audit["corrections"])
        )
        self.assertEqual(self.audit["summary"]["genuine_fail_count"], 0)

    def test_generated_artifact_matches_builder(self):
        path = (
            ROOT
            / "artifacts/evidence_closure/evidence_semantic_correction_v1_1.json"
        )
        persisted = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(persisted, self.audit)


if __name__ == "__main__":
    unittest.main()
