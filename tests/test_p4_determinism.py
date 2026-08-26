import unittest

import numpy as np

from src.rca.p4 import CandidateEvent, fit_conditional_logit


class P4DeterminismTest(unittest.TestCase):
    def test_repeated_fit_is_strictly_equal(self):
        events = tuple(
            CandidateEvent("e{}".format(i), ("a", "b", "c"), np.array([[i + 1., 0.], [0., i + 1.], [0.5, 0.5]]))
            for i in range(6)
        )
        roots = {event.case_id: ("a" if index % 2 == 0 else "b") for index, event in enumerate(events)}
        first = fit_conditional_logit(events, roots)
        second = fit_conditional_logit(events, roots)
        np.testing.assert_array_equal(first.weights, second.weights)
        np.testing.assert_array_equal(first.scaler_mean, second.scaler_mean)
        np.testing.assert_array_equal(first.scaler_scale, second.scaler_scale)
        self.assertEqual(first.final_loss, second.final_loss)


if __name__ == "__main__":
    unittest.main()
