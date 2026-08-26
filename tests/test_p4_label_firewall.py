import inspect
import unittest

import numpy as np

from src.rca.p4 import build_candidate_representation, within_event_percentiles


class P4LabelFirewallTest(unittest.TestCase):
    def test_percentile_builder_needs_no_label_object(self):
        self.assertEqual(tuple(inspect.signature(within_event_percentiles).parameters), ("values",))
        self.assertEqual(build_candidate_representation(np.array([[0.], [1.]]), True).shape, (2, 2))


if __name__ == "__main__":
    unittest.main()
