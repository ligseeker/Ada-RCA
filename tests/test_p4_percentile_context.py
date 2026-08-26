import unittest

import numpy as np

from src.rca.p4 import within_event_percentiles


class P4PercentileContextTest(unittest.TestCase):
    def test_bounds_and_average_rank_ties(self):
        values = np.array([[1.0, 4.0], [1.0, 2.0], [3.0, 2.0]])
        actual = within_event_percentiles(values)
        expected = np.array([[0.25, 1.0], [0.25, 0.25], [1.0, 0.25]])
        np.testing.assert_allclose(actual, expected, rtol=0, atol=0)
        self.assertTrue(np.all((actual >= 0) & (actual <= 1)))

    def test_all_equal_is_one_half(self):
        actual = within_event_percentiles(np.ones((5, 3)))
        np.testing.assert_allclose(actual, 0.5, rtol=0, atol=0)


if __name__ == "__main__":
    unittest.main()
