import unittest
import tempfile
from pathlib import Path

import numpy as np

from src.rca.supervised_baselines.common import SupervisedEvent
from src.rca.supervised_baselines.xgb_ranker import (
    XGB_CONFIG,
    build_grouped_training_matrix,
    fit_score_and_save,
)


def event(case_id, candidates):
    count = len(candidates)
    return SupervisedEvent(
        case_id,
        "re2ob",
        0,
        tuple(candidates),
        np.arange(count * 32, dtype=float).reshape(count, 32),
        np.zeros((count, 8, 80), dtype=float),
    )


class SupervisedXGBTest(unittest.TestCase):
    def test_event_group_boundaries_and_labels(self):
        events = (event("one", ("a", "b", "c")), event("two", ("a", "b", "c")))
        matrix, target, group = build_grouped_training_matrix(events, {"one": "b", "two": "c"})
        self.assertEqual(matrix.shape, (6, 32))
        np.testing.assert_array_equal(group, (3, 3))
        np.testing.assert_array_equal(target, (0, 1, 0, 0, 0, 1))
        self.assertEqual(int(group.sum()), matrix.shape[0])

    def test_configuration_is_frozen_and_deterministic(self):
        self.assertEqual(XGB_CONFIG["objective"], "rank:pairwise")
        self.assertEqual(XGB_CONFIG["random_state"], 20260826)
        self.assertEqual(XGB_CONFIG["n_jobs"], 1)
        self.assertEqual(XGB_CONFIG["tree_method"], "hist")

    def test_repeated_fit_has_deterministic_output(self):
        events = (
            event("one", ("a", "b", "c")),
            event("two", ("a", "b", "c")),
            event("three", ("a", "b", "c")),
        )
        roots = {"one": "a", "two": "b"}
        with tempfile.TemporaryDirectory() as left_dir, tempfile.TemporaryDirectory() as right_dir:
            left = fit_score_and_save(events[:2], roots, events[2:], Path(left_dir))
            right = fit_score_and_save(events[:2], roots, events[2:], Path(right_dir))
        np.testing.assert_array_equal(left["three"], right["three"])


if __name__ == "__main__":
    unittest.main()
