import unittest

from scripts.run_v2_f0 import (
    MODALITIES,
    VARIANT_MODALITIES,
    feature_indices,
    feature_names,
)
from src.rca.final_method import FINAL_Z2_FEATURE_NAMES


class V2F0Test(unittest.TestCase):
    def test_modality_order_and_fixed_variant_set(self):
        self.assertEqual(MODALITIES, ("M", "L", "TE", "TL"))
        self.assertEqual(tuple(name for name, _ in VARIANT_MODALITIES), (
            "M", "L", "TE", "TL",
            "M+L", "M+TE", "M+TL", "L+TE", "L+TL", "TE+TL",
            "FULL-M", "FULL-L", "FULL-TE", "FULL-TL", "FULL-Z2",
        ))

    def test_each_modality_is_the_frozen_contiguous_17d_block(self):
        for index, modality in enumerate(MODALITIES):
            self.assertEqual(
                feature_indices((modality,)),
                tuple(range(index * 17, (index + 1) * 17)),
            )
            self.assertEqual(len(feature_names((modality,))), 17)
        self.assertEqual(feature_names(MODALITIES), FINAL_Z2_FEATURE_NAMES)
        self.assertEqual(len(feature_indices(MODALITIES)), 68)


if __name__ == "__main__":
    unittest.main()
