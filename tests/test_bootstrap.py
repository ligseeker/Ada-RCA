import unittest
import numpy as np


class BootstrapTest(unittest.TestCase):
    def test_fixed_seed_is_repeatable(self):
        a = np.random.RandomState(20260826).randint(0, 10, 10)
        b = np.random.RandomState(20260826).randint(0, 10, 10)
        self.assertTrue(np.array_equal(a, b))


if __name__ == "__main__":
    unittest.main()
