import unittest

import numpy as np

from src.rca.p4 import CandidateEvent, fit_conditional_logit


class P4EventBatchingTest(unittest.TestCase):
    def test_training_loss_counts_events_not_candidate_rows(self):
        events = (
            CandidateEvent("x", ("a", "b"), np.zeros((2, 1))),
            CandidateEvent("y", ("a", "b", "c", "d"), np.zeros((4, 1))),
        )
        fit = fit_conditional_logit(events, {"x": "a", "y": "a"})
        self.assertAlmostEqual(fit.initial_loss, np.log(2.0) + np.log(4.0), places=12)
        self.assertAlmostEqual(fit.final_loss, fit.initial_loss, places=12)


if __name__ == "__main__":
    unittest.main()
