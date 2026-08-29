import unittest

from scripts.run_v2_f0 import (
    MODALITIES,
    VARIANT_MODALITIES,
    feature_indices,
    feature_names,
    full_z2_identity,
)
from src.rca.final_method import FINAL_Z2_FEATURE_NAMES


class V2F0Test(unittest.TestCase):
    def test_modality_order_and_fixed_variant_set(self):
        self.assertEqual(MODALITIES, ("M", "L", "TE", "TL"))
        self.assertEqual(tuple(name for name, _ in VARIANT_MODALITIES), (
            "M", "L", "TE", "TL",
            "M+L", "M+TE", "M+TL", "L+TE", "L+TL", "TE+TL",
            "FULL-M", "FULL-L", "FULL-TE", "FULL-TL", "FULL-Z2",
        ))

    def test_each_modality_is_the_frozen_contiguous_17d_block(self):
        for index, modality in enumerate(MODALITIES):
            self.assertEqual(
                feature_indices((modality,)),
                tuple(range(index * 17, (index + 1) * 17)),
            )
            self.assertEqual(len(feature_names((modality,))), 17)
        self.assertEqual(feature_names(MODALITIES), FINAL_Z2_FEATURE_NAMES)
        self.assertEqual(len(feature_indices(MODALITIES)), 68)

    def test_f0_identity_is_ranking_and_metric_identity(self):
        fresh = ({
            "case_id": "opaque-case",
            "ranking": ["a", "b"],
            "candidate_scores": {"a": 2.0, "b": 1.0},
        },)
        committed = ({
            "case_id": "opaque-case",
            "ranking": ["a", "b"],
            "candidate_scores": {"a": 2.0 + 2e-12, "b": 1.0},
        },)
        metrics = {"Avg@5": 1.0}
        identity = full_z2_identity(fresh, committed, metrics, dict(metrics))
        self.assertTrue(identity["integrity_valid"])
        self.assertTrue(identity["ranking_identical"])
        self.assertTrue(identity["overall_metrics_identical"])
        self.assertGreater(identity["max_abs_score_difference"], 1e-12)


if __name__ == "__main__":
    unittest.main()
