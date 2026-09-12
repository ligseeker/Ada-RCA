import inspect
from pathlib import Path
import tempfile
import unittest

import numpy as np

from src.rca.final_method import FINAL_Z2_DIMENSION, FINAL_Z2_FEATURE_ORDER_SHA256
from src.rca.supervised_baselines.common import (
    EXPECTED_CANDIDATES,
    SupervisedEvent,
    load_prediction_events,
)
from src.rca.supervised_baselines.xgb_ranker import XGB_CONFIG
from src.rca.supervised_baselines.z2_xgb_ranker import (
    Z2_XGB_CONFIG,
    build_grouped_training_matrix,
    fit_score_and_save,
    scorer_parameters,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def synthetic_event(case_id, candidates, fold=0):
    count = len(candidates)
    return SupervisedEvent(
        case_id,
        "re2ob",
        fold,
        tuple(candidates),
        np.arange(count * 32, dtype=float).reshape(count, 32),
        np.zeros((count, 8, 80), dtype=float),
        np.arange(count * FINAL_Z2_DIMENSION, dtype=float).reshape(
            count, FINAL_Z2_DIMENSION
        ),
    )


class Z2XGBClosureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = {
            dataset: load_prediction_events(PROJECT_ROOT, dataset)
            for dataset in ("re2ob", "re2tt")
        }

    def test_committed_z2_identity_is_68d_and_candidate_aligned(self):
        for dataset, events in self.events.items():
            self.assertEqual(len(events), 90)
            self.assertEqual(
                {len(event.candidates) for event in events.values()},
                {EXPECTED_CANDIDATES[dataset]},
            )
            for case_id, event in events.items():
                self.assertEqual(case_id, event.case_id)
                self.assertEqual(event.z1.shape, (len(event.candidates), 32))
                self.assertEqual(event.z2.shape, (len(event.candidates), 68))
                self.assertTrue(np.isfinite(event.z2).all())

    def test_scorer_parameters_match_z1_xgb(self):
        for key, value in scorer_parameters().items():
            self.assertEqual(value, XGB_CONFIG[key])
        self.assertEqual(Z2_XGB_CONFIG["input"], "frozen Z2 68D only")
        self.assertEqual(Z2_XGB_CONFIG["method"], "z2_xgb_ranker")
        self.assertEqual(Z2_XGB_CONFIG["random_state"], 20260826)
        self.assertEqual(Z2_XGB_CONFIG["n_jobs"], 1)
        self.assertEqual(Z2_XGB_CONFIG["tree_method"], "hist")

    def test_group_sizes_and_one_positive_root(self):
        events = (
            synthetic_event("one", ("a", "b", "c")),
            synthetic_event("two", ("a", "b", "c")),
        )
        matrix, target, group = build_grouped_training_matrix(
            events, {"one": "b", "two": "c"}
        )
        self.assertEqual(matrix.shape, (6, 68))
        np.testing.assert_array_equal(group, (3, 3))
        np.testing.assert_array_equal(target, (0, 1, 0, 0, 0, 1))
        self.assertEqual(int(target.sum()), len(events))

    def test_prediction_interface_has_no_test_label_fields(self):
        parameters = inspect.signature(SupervisedEvent).parameters
        self.assertNotIn("root_service", parameters)
        self.assertNotIn("fault_type", parameters)
        self.assertNotIn("root_service", inspect.signature(fit_score_and_save).parameters)
        self.assertNotIn("fault_type", inspect.signature(fit_score_and_save).parameters)

    def test_repeated_z2_fit_is_deterministic(self):
        events = (
            synthetic_event("one", ("a", "b", "c")),
            synthetic_event("two", ("a", "b", "c")),
            synthetic_event("three", ("a", "b", "c")),
        )
        roots = {"one": "a", "two": "b"}
        with tempfile.TemporaryDirectory() as left_dir, tempfile.TemporaryDirectory() as right_dir:
            left = fit_score_and_save(events[:2], roots, events[2:], Path(left_dir))
            right = fit_score_and_save(events[:2], roots, events[2:], Path(right_dir))
        np.testing.assert_array_equal(left["three"], right["three"])

    def test_frozen_feature_order_digest_is_present(self):
        self.assertEqual(len(FINAL_Z2_FEATURE_ORDER_SHA256), 64)
        self.assertEqual(FINAL_Z2_DIMENSION, 68)


if __name__ == "__main__":
    unittest.main()
