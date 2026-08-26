import unittest
from src.rca.zero_model import VARIANTS


class ZeroModelTest(unittest.TestCase):
    def test_variant_set_is_frozen(self):
        self.assertEqual(VARIANTS, ("z0", "z1", "z2", "z3", "z3_shuffle"))


if __name__ == "__main__":
    unittest.main()
