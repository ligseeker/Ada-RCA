import unittest

import numpy as np

from src.rca.supervised_baselines.common import SupervisedEvent, rank_scores
from src.rca.supervised_baselines.tcn import (
    TCN_CONFIG,
    configure_determinism,
    event_probabilities,
    make_model,
)


class SupervisedTCNTest(unittest.TestCase):
    def test_expected_shape_event_softmax_and_complete_ranking(self):
        import torch

        configure_determinism(torch)
        model = make_model(torch)
        event = SupervisedEvent(
            "toy", "re2ob", 0, ("a", "b", "c"),
            np.zeros((3, 32), dtype=float),
            np.zeros((3, 8, 80), dtype=float),
        )
        scores = model(torch.as_tensor(event.trajectory, dtype=torch.float32))
        self.assertEqual(tuple(scores.shape), (3,))
        probabilities = event_probabilities(scores)
        self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=6)
        self.assertEqual(set(rank_scores(event.candidates, scores.detach().numpy())), set(event.candidates))

    def test_fixed_architecture_and_training_contract(self):
        self.assertEqual(TCN_CONFIG["input"], "frozen z plus q_mask, candidate x 8 x 80")
        self.assertEqual(TCN_CONFIG["loss"], "event-level cross entropy over complete candidate axis")
        self.assertEqual(TCN_CONFIG["epochs"], 100)
        self.assertIsNone(TCN_CONFIG["validation"])
        self.assertFalse(TCN_CONFIG["early_stopping"])

    def test_initialization_is_deterministic(self):
        import torch

        configure_determinism(torch)
        left = make_model(torch).state_dict()
        configure_determinism(torch)
        right = make_model(torch).state_dict()
        self.assertEqual(left.keys(), right.keys())
        for key in left:
            self.assertTrue(torch.equal(left[key], right[key]))


if __name__ == "__main__":
    unittest.main()
