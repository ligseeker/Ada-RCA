import hashlib
import json
from pathlib import Path
import unittest

from src.baseline_eval import (
    STARTING_HEAD,
    assert_ada_rca_frozen_unchanged,
    audit_frozen_inputs,
)


ROOT = Path(__file__).resolve().parents[1]


class BaselineEvalFrozenIntegrityTest(unittest.TestCase):
    def test_canonical_90_case_identity_is_frozen(self):
        audit = audit_frozen_inputs(ROOT)
        expected = {
            "re2ob": {
                "case_count": 90,
                "inputs_sha256": "151cdf4cf89d89b5036cbf7b309c95e04fbf4a77a0012bd54cf7784778206dbb",
                "sources_sha256": "c162bb9882035d7b50d94f69e25fd638746519a3f3d4ad6029468d1eee606591",
            },
            "re2tt": {
                "case_count": 90,
                "inputs_sha256": "1ca5e91387641c891e75a6e26bc3979f2398dae93e46147e97864cd503c7655d",
                "sources_sha256": "866ee17bec973d004984822eadef3076ca12c3b67505ba2ccabd7f4cfb9bc931",
            },
        }
        for dataset, values in expected.items():
            self.assertEqual(audit[dataset]["case_count"], values["case_count"])
            self.assertEqual(audit[dataset]["unique_case_count"], 90)
            self.assertEqual(audit[dataset]["inputs_sha256"], values["inputs_sha256"])
            self.assertEqual(audit[dataset]["sources_sha256"], values["sources_sha256"])
            self.assertTrue(audit[dataset]["case_ids_aligned"])
            self.assertTrue(audit[dataset]["anchors_match_sources"])

    def test_frozen_root_mapping_identity(self):
        audit = audit_frozen_inputs(ROOT)
        self.assertEqual(
            audit["re2ob"]["labels_sha256"],
            "f3dd164e03d9207af4d4e432a1848c2100ec7a65c125b420c80642a56be3dba7",
        )
        self.assertEqual(
            audit["re2tt"]["labels_sha256"],
            "950885c2d89872f670d8cb06121a0d8d4c3e9fbd6be5e97a29af89a6013481ca",
        )
        for dataset in ("re2ob", "re2tt"):
            self.assertTrue(audit[dataset]["roots_in_registry"])

    def test_frozen_candidate_registry_identity(self):
        audit = audit_frozen_inputs(ROOT)
        self.assertEqual(audit["re2ob"]["candidate_count"], 11)
        self.assertEqual(audit["re2tt"]["candidate_count"], 68)
        self.assertEqual(
            audit["re2ob"]["registry_sha256"],
            "9eae7e79662ade83e0f6034073ab5c424bbf93be5765bd4bc5ea51d90c0efd19",
        )
        self.assertEqual(
            audit["re2tt"]["registry_sha256"],
            "67ad834a58be40802d9a8071ae849b7812ee390b87b08b5d82567596a39d236a",
        )
        for dataset in ("re2ob", "re2tt"):
            self.assertTrue(audit[dataset]["registry_identical_across_cases"])

    def test_ada_rca_frozen_artifacts_are_unchanged(self):
        self.assertEqual(STARTING_HEAD, "9342e06db91945be2e44703437229ba45b18bda8")
        assert_ada_rca_frozen_unchanged(ROOT)


if __name__ == "__main__":
    unittest.main()
