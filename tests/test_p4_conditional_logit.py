import unittest

import numpy as np

from src.rca.p4 import CandidateEvent, event_softmax, fit_conditional_logit


class P4ConditionalLogitTest(unittest.TestCase):
    def test_softmax_and_synthetic_ranking_recovery(self):
        events = []
        roots = {}
        for index in range(12):
            root = index % 3
            values = np.zeros((3, 2), dtype=float)
            values[root, 0] = 3.0
            values[:, 1] = np.array([0.0, 0.1, 0.2])
            case_id = "e{}".format(index)
            events.append(CandidateEvent(case_id, ("a", "b", "c"), values))
            roots[case_id] = ("a", "b", "c")[root]
        fit = fit_conditional_logit(events, roots)
        self.assertTrue(fit.converged)
        self.assertLess(fit.final_loss, fit.initial_loss)
        for event in events:
            probabilities = event_softmax(fit.scores(event.features))
            self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=14)
            self.assertEqual(event.candidates[int(np.argmax(probabilities))], roots[event.case_id])


if __name__ == "__main__":
    unittest.main()
