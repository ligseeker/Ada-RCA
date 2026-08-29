import hashlib
import json
import unittest
from pathlib import Path

from src.rca.evidence_closure import (
    DATASETS,
    FROZEN_COMMIT,
    build_input_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class EvidenceClosureGate0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = build_input_manifest(ROOT)

    def test_frozen_input_sha_validation(self):
        for track in self.manifest["evidence"].values():
            for dataset in track["datasets"].values():
                for record in dataset["source_files"]:
                    path = ROOT / record["source_file"]
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])
                    self.assertEqual(record["sha256"], record["git_blob_sha256_at_frozen_commit"])
                    self.assertTrue(record["working_copy_matches_frozen_commit"])
                    self.assertEqual(record["repository_commit"], FROZEN_COMMIT)

    def test_case_count_integrity(self):
        for track in self.manifest["evidence"].values():
            for dataset in DATASETS:
                integrity = track["datasets"][dataset]["integrity"]
                self.assertEqual(integrity["event_count"], 90)
                self.assertEqual(integrity["expected_event_count"], 90)
                self.assertEqual(integrity["expected_case_coverage"], "PASS")
                self.assertEqual(integrity["event_id_uniqueness"], "PASS")
                self.assertEqual(integrity["fold_coverage"], {"0": 30, "1": 30, "2": 30})

    def test_root_and_candidate_registry_integrity(self):
        expected_counts = {"re2ob": 11, "re2tt": 68}
        for track in self.manifest["evidence"].values():
            for dataset in DATASETS:
                integrity = track["datasets"][dataset]["integrity"]
                self.assertEqual(integrity["candidate_registry_count"], expected_counts[dataset])
                self.assertEqual(integrity["candidate_registry_consistency"], "PASS")
                self.assertEqual(integrity["root_mapping_consistency"], "PASS")
                self.assertEqual(integrity["root_presence"], "PASS")

    def test_complete_rankings_for_v1_and_global(self):
        for track_name in ("V1-SCIENTIFIC", "GLOBAL-OPT"):
            for dataset in DATASETS:
                integrity = self.manifest["evidence"][track_name]["datasets"][dataset]["integrity"]
                self.assertEqual(integrity["ranking_completeness"], "PASS")
                self.assertEqual(integrity["ranking_deterministic"], "PASS")
                self.assertEqual(integrity["duplicate_ranking_entries"], "PASS")

    def test_per_dataset_full_ranking_evidence_is_unavailable(self):
        for dataset in DATASETS:
            integrity = self.manifest["evidence"]["PER-DATASET-OPT"]["datasets"][dataset]["integrity"]
            self.assertFalse(integrity["full_prediction_ranking_evidence_exists"])
            self.assertEqual(integrity["frozen_prediction_status"], "FROZEN_PREDICTION_EVIDENCE_UNAVAILABLE")
            self.assertEqual(integrity["ranking_completeness"], "FAIL")
            self.assertEqual(integrity["candidate_coverage"]["status"], "NOT_AUDITABLE_FROM_ROOT_RANK_ONLY")

    def test_v1_reference_is_byte_traceable(self):
        traceability = self.manifest["v1_reference_traceability"]
        self.assertTrue(traceability["reference_is_ancestor_of_frozen_commit"])
        for dataset in DATASETS:
            self.assertTrue(traceability["prediction_artifact_identity"][dataset]["byte_identical"])

    def test_frozen_prediction_files_are_not_evidence_closure_outputs(self):
        output_root = (ROOT / "artifacts/evidence_closure").resolve()
        for track in self.manifest["evidence"].values():
            for dataset in track["datasets"].values():
                prediction = (ROOT / dataset["source_files"][0]["source_file"]).resolve()
                self.assertNotEqual(output_root, prediction)
                self.assertNotIn(output_root, prediction.parents)

    def test_gate_stops_on_fatal_incomplete_ranking(self):
        gate = self.manifest["gate_0"]
        self.assertEqual(gate["status"], "FAIL")
        self.assertEqual(gate["downstream_gate_authorization"], "STOP")
        self.assertEqual(gate["terminal_state_if_unresolved"], "RCA_EVIDENCE_NOT_CLOSED")
        defects = {(item["track"], item["dataset"], item["defect"]) for item in gate["fatal_defects"]}
        for dataset in DATASETS:
            self.assertIn(("PER-DATASET-OPT", dataset, "FROZEN_PREDICTION_EVIDENCE_UNAVAILABLE"), defects)
            self.assertIn(("PER-DATASET-OPT", dataset, "RANKING_COMPLETENESS_FAILURE"), defects)


if __name__ == "__main__":
    unittest.main()
