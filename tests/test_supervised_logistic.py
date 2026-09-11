import unittest

import numpy as np

from src.rca.supervised_baselines.common import SupervisedEvent, rank_scores
from src.rca.supervised_baselines.logistic import LOGISTIC_CONFIG, fit_logistic


def event(case_id, fold, offset):
    candidates = ("a", "b", "c")
    values = np.zeros((3, 32), dtype=float)
    values[:, 0] = np.asarray((0.0, 1.0, 2.0)) + offset
    trajectory = np.zeros((3, 8, 80), dtype=float)
    return SupervisedEvent(case_id, "re2ob", fold, candidates, values, trajectory)


class SupervisedLogisticTest(unittest.TestCase):
    def test_scaler_is_fit_on_training_rows_only(self):
        train = (event("train-1", 0, 0.0), event("train-2", 1, 3.0))
        roots = {"train-1": "c", "train-2": "c"}
        held_out = event("test", 2, 1000.0)
        scorer = fit_logistic(train, roots)
        expected = np.concatenate([row.z1 for row in train], axis=0).mean(axis=0)
        np.testing.assert_allclose(scorer.scaler.mean_, expected)
        self.assertNotAlmostEqual(scorer.scaler.mean_[0], np.concatenate([
            train[0].z1, train[1].z1, held_out.z1
        ]).mean(axis=0)[0])

    def test_deterministic_complete_ranking(self):
        train = (event("train-1", 0, 0.0), event("train-2", 1, 3.0))
        roots = {"train-1": "c", "train-2": "c"}
        test = event("test", 2, 6.0)
        left = fit_logistic(train, roots).score(test)
        right = fit_logistic(train, roots).score(test)
        np.testing.assert_array_equal(left, right)
        self.assertEqual(set(rank_scores(test.candidates, left)), set(test.candidates))
        self.assertEqual(LOGISTIC_CONFIG["random_state"], 20260826)


if __name__ == "__main__":
    unittest.main()
