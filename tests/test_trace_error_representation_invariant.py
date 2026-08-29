import json
import subprocess
import unittest
from pathlib import Path

from src.rca.evidence_closure import FROZEN_COMMIT
from src.rca.evidence_trace_error import (
    TRACE_ERROR_DIMENSION,
    build_trace_error_representation_invariant,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT / "artifacts/evidence_closure/trace_error_representation_invariant.json"
)


class TraceErrorRepresentationInvariantTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = build_trace_error_representation_invariant(ROOT)

    def test_computation_is_deterministic(self):
        repeated = build_trace_error_representation_invariant(ROOT)
        self.assertEqual(self.audit, repeated)
        self.assertEqual(
            self.audit,
            json.loads(ARTIFACT.read_text(encoding="utf-8")),
        )

    def test_trace_error_block_is_exactly_17_dimensions(self):
        self.assertEqual(TRACE_ERROR_DIMENSION, 17)
        self.assertEqual(self.audit["feature_order"]["trace_error_dimension"], 17)
        self.assertEqual(len(self.audit["feature_order"]["feature_names"]), 17)
        self.assertEqual(len(self.audit["feature_order"]["frozen_z2_indices"]), 17)

    def test_candidate_case_row_counts(self):
        self.assertEqual(self.audit["datasets"]["re2ob"]["total_candidate_case_rows"], 990)
        self.assertEqual(self.audit["datasets"]["re2tt"]["total_candidate_case_rows"], 6120)

    def test_nonzero_but_nondiscriminative(self):
        for dataset in ("re2ob", "re2tt"):
            record = self.audit["datasets"][dataset]
            self.assertEqual(record["all_zero_rows"], 0)
            self.assertEqual(
                record["nonzero_rows"], record["total_candidate_case_rows"]
            )
            self.assertEqual(record["unique_trace_error_vectors"], 1)
            self.assertEqual(record["dimensions_with_nonzero_variance"], 0)
            self.assertEqual(
                record["within_case_candidate_discriminative_variation"][
                    "case_count"
                ],
                0,
            )
            self.assertTrue(
                record["removal_invariant"][
                    "change_is_constant_across_candidates_in_every_case"
                ]
            )
            self.assertEqual(
                record["classification"],
                "TRACE_ERROR_EFFECTIVELY_NONDISCRIMINATIVE_IN_FROZEN_Z2",
            )

    def test_exact_field_relationship(self):
        for record in self.audit["datasets"].values():
            rows = record["total_candidate_case_rows"]
            relationship = record["field_relationship"]
            self.assertEqual(relationship["base_coverage_zero_rows"], rows)
            self.assertEqual(relationship["base_channel_available_zero_rows"], rows)
            self.assertEqual(relationship["morphology_active_zero_rows"], rows)
            self.assertEqual(relationship["remaining_morphology_all_zero_rows"], rows)
            self.assertEqual(relationship["onset_missing_one_rows"], rows)

    def test_frozen_selection_traces_are_consistent_secondary_evidence(self):
        cross_check = self.audit["optimization_trace_cross_check"]
        self.assertEqual(
            cross_check["status"], "CONSISTENT_WITH_TE_NONDISCRIMINATIVE"
        )
        self.assertEqual(cross_check["role"], "SECONDARY_ONLY")
        expected = {
            "M+TE_vs_Z1-M": (6, 6),
            "FULL-Z2_vs_M+L+TL": (6, 12),
        }
        for name, (screen_count, grid_count) in expected.items():
            record = cross_check["equivalences"][name]
            self.assertEqual(
                record["representation_screen_comparisons_available"], screen_count
            )
            self.assertEqual(
                record["representation_screen_comparisons_exact"], screen_count
            )
            self.assertEqual(record["ranker_grid_comparisons_available"], grid_count)
            self.assertEqual(record["ranker_grid_comparisons_exact"], grid_count)
            self.assertTrue(record["all_available_comparisons_exact"])
            self.assertEqual(
                record["interpretation"],
                "CONSISTENT_WITH_TE_NONDISCRIMINATIVE",
            )

    def test_feature_matrices_are_unchanged(self):
        for record in self.audit["datasets"].values():
            self.assertEqual(record["provenance"]["feature_file_count"], 90)
            self.assertTrue(
                record["provenance"]["all_feature_files_match_frozen_commit"]
            )
            self.assertTrue(
                all(
                    file_record["matches_frozen_commit"]
                    for file_record in record["provenance"]["feature_files"]
                )
            )
        changed = subprocess.check_output(
            (
                "git",
                "diff",
                "--name-only",
                FROZEN_COMMIT,
                "--",
                "artifacts/features",
            ),
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(changed, "")


if __name__ == "__main__":
    unittest.main()
