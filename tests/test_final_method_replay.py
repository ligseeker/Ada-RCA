import json
from pathlib import Path
import unittest

import numpy as np

from src.rca.final_method import (
    FINAL_Z2_DIMENSION,
    FINAL_Z2_FEATURE_NAMES,
    FINAL_Z2_FEATURE_ORDER_SHA256,
    compare_predictions,
    load_dataset,
    load_fold_state,
    predict_with_persisted_states,
    read_jsonl,
    sha256_file,
)
from src.rca.p4 import verify_complete_prediction
from src.rca.p4_stats import evaluate_predictions


class FinalMethodReplayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.artifact_root = cls.root / "artifacts" / "final_method"
        if not (cls.artifact_root / "re2ob" / "replay_audit.json").is_file():
            raise unittest.SkipTest("formal final-method replay artifacts not generated")

    def test_z2_dimension_and_exact_feature_order(self):
        self.assertEqual(FINAL_Z2_DIMENSION, 68)
        self.assertEqual(len(FINAL_Z2_FEATURE_NAMES), 68)
        self.assertEqual(FINAL_Z2_FEATURE_NAMES[:3], (
            "metric.magnitude", "metric.mean_impact", "metric.pre_post_shift",
        ))
        self.assertEqual(FINAL_Z2_FEATURE_NAMES[-1], "trace-latency.morphology_active")
        for dataset in ("re2ob", "re2tt"):
            config = json.loads((self.artifact_root / dataset / "config.json").read_text())
            self.assertEqual(config["feature_dimension"], 68)
            self.assertEqual(tuple(config["feature_names"]), FINAL_Z2_FEATURE_NAMES)
            self.assertEqual(config["feature_order_sha256"], FINAL_Z2_FEATURE_ORDER_SHA256)

    def test_representation_split_and_dataset_provenance(self):
        for dataset in ("re2ob", "re2tt"):
            provenance = json.loads((self.artifact_root / dataset / "provenance.json").read_text())
            self.assertEqual(provenance["representation_provenance"], "docs/REPRESENTATION_FREEZE.md")
            self.assertEqual(
                provenance["feature_manifest_sha256"],
                sha256_file(self.root / "artifacts" / "features" / dataset / "manifest.json"),
            )
            self.assertEqual(
                provenance["split_manifest_sha256"],
                sha256_file(self.root / "artifacts" / "splits" / dataset / "split_manifest.json"),
            )
            self.assertEqual(len(provenance["dataset_tree_sha256"]), 64)

    def test_label_firewall_and_split_integrity(self):
        forbidden = ("root_service", "fault_type", "service_identity")
        self.assertFalse(any(token in name for name in FINAL_Z2_FEATURE_NAMES for token in forbidden))
        for dataset in ("re2ob", "re2tt"):
            events, labels, roots, assignments = load_dataset(self.root, dataset)
            self.assertEqual(len(events), 90)
            self.assertEqual(set(events), set(labels))
            self.assertEqual(set(events), set(assignments))
            for fold in (0, 1, 2):
                train = {case_id for case_id, value in assignments.items() if value != fold}
                test = {case_id for case_id, value in assignments.items() if value == fold}
                self.assertEqual((len(train), len(test)), (60, 30))
                self.assertFalse(train & test)
            self.assertTrue(all(roots[case_id] in events[case_id].candidates for case_id in events))

    def test_persisted_state_replay_and_p4_a2_identity(self):
        for dataset in ("re2ob", "re2tt"):
            events, labels, roots, assignments = load_dataset(self.root, dataset)
            states = {
                fold: load_fold_state(self.artifact_root / dataset / "model_state" / ("fold_{}.npz".format(fold)))
                for fold in (0, 1, 2)
            }
            replay = predict_with_persisted_states(events, assignments, states)
            committed = read_jsonl(
                self.root / "artifacts" / "p4_g0" / "predictions" / "a2" / dataset / "predictions.jsonl"
            )
            identity = compare_predictions(replay, committed)
            self.assertTrue(identity["ranking_identical"])
            self.assertLessEqual(identity["max_abs_score_difference"], 1e-12)
            for row in replay:
                verify_complete_prediction(row, events[row["case_id"]].candidates, roots[row["case_id"]])

    def test_metric_recomputation_and_gradient_tolerance(self):
        expected = {
            "re2ob": {"AC@1": 0.8777777777777778, "AC@3": 0.9888888888888889, "AC@5": 0.9888888888888889, "Avg@5": 0.9622222222222222, "MRR": 0.9314814814814816},
            "re2tt": {"AC@1": 0.7111111111111111, "AC@3": 0.8666666666666667, "AC@5": 0.9333333333333333, "Avg@5": 0.851111111111111, "MRR": 0.8034718881941106},
        }
        for dataset in ("re2ob", "re2tt"):
            events, labels, roots, assignments = load_dataset(self.root, dataset)
            rows = list(read_jsonl(self.artifact_root / dataset / "predictions.jsonl"))
            metrics = evaluate_predictions(rows, {case_id: event.candidates for case_id, event in events.items()}, roots)
            self.assertEqual(metrics["overall_cases"], expected[dataset])
            audit = json.loads((self.artifact_root / dataset / "replay_audit.json").read_text())
            self.assertEqual(audit["integrity_status"], "INTEGRITY_VALID")
            self.assertTrue(audit["all_folds_converged"])
            self.assertLessEqual(audit["max_gradient_norm"], 1e-8)

    def test_model_arrays_are_float64_and_checksum_bound(self):
        for dataset in ("re2ob", "re2tt"):
            for fold in (0, 1, 2):
                path = self.artifact_root / dataset / "model_state" / ("fold_{}.npz".format(fold))
                metadata = json.loads(path.with_suffix(".json").read_text())
                self.assertEqual(metadata["array_sha256"], sha256_file(path))
                self.assertTrue(metadata["converged"])
                self.assertLessEqual(metadata["gradient_norm"], 1e-8)
                with np.load(path) as data:
                    for name in ("weights", "scaler_mean", "scaler_scale"):
                        self.assertEqual(data[name].dtype, np.float64)
                        self.assertEqual(data[name].shape, (68,))


if __name__ == "__main__":
    unittest.main()

