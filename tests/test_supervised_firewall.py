from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.rca.supervised_baselines import common


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SupervisedFirewallTest(unittest.TestCase):
    def test_test_labels_are_joined_only_after_prediction(self):
        events = common.load_prediction_events(PROJECT_ROOT, "re2ob")
        train, test = common.partition_fold(events, 0)
        train_ids = {event.case_id for event in train}
        test_ids = {event.case_id for event in test}
        calls = []

        def labels(_root, _dataset, case_ids):
            ids = tuple(case_ids)
            phase = "train_labels" if set(ids) == train_ids else "test_labels"
            calls.append(phase)
            rows = {}
            for index, case_id in enumerate(ids):
                rows[case_id] = {
                    "root_service": events[case_id].candidates[0],
                    "fault_type": ("cpu", "mem", "disk", "socket", "delay", "loss")[index % 6],
                }
            return rows

        def fit_predict(train_events, train_roots, test_events, run_dir):
            calls.append("fit_predict")
            self.assertEqual(set(train_roots), train_ids)
            self.assertTrue(all(not hasattr(event, "root_service") for event in test_events))
            return {
                event.case_id: np.arange(len(event.candidates), dtype=float)
                for event in test_events
            }

        with tempfile.TemporaryDirectory() as output_root, patch.dict(
            os.environ, {"PYTHONHASHSEED": "20260826"}
        ):
            with patch.object(common, "load_label_subset", side_effect=labels), patch.object(
                common,
                "current_git_identity",
                return_value={"head": "test", "branch": "test", "dirty_entries": ()},
            ):
                common.run_fold(
                    PROJECT_ROOT,
                    "re2ob",
                    0,
                    "toy",
                    Path(output_root),
                    {"normalization": "none"},
                    fit_predict,
                    {},
                )
        self.assertEqual(calls, ["train_labels", "fit_predict", "test_labels"])

    def test_wrong_python_hash_seed_is_rejected_before_artifact_creation(self):
        with tempfile.TemporaryDirectory() as output_root, patch.dict(
            os.environ, {"PYTHONHASHSEED": "20260830"}
        ), patch.object(
            common,
            "current_git_identity",
            return_value={"head": "test", "branch": "test", "dirty_entries": ()},
        ):
            with self.assertRaisesRegex(RuntimeError, "PYTHONHASHSEED=20260826"):
                common.run_fold(
                    PROJECT_ROOT,
                    "re2ob",
                    0,
                    "toy",
                    Path(output_root),
                    {"normalization": "none"},
                    lambda *_args: {},
                    {},
                )
            self.assertEqual(list(Path(output_root).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
