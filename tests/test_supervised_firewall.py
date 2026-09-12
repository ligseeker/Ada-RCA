from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from src.rca.supervised_baselines import common


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SupervisedFirewallTest(unittest.TestCase):
    def test_custom_artifact_output_root_allows_previous_fold_artifacts(self):
        artifact_parent = PROJECT_ROOT / "artifacts"
        with tempfile.TemporaryDirectory(
            prefix="supervised_baselines_replay_test_", dir=str(artifact_parent)
        ) as output_root_text, patch.dict(
            os.environ, {"PYTHONHASHSEED": "20260826"}
        ):
            output_root = Path(output_root_text)
            relative_output = output_root.relative_to(PROJECT_ROOT).as_posix()
            dirty_entries = (
                "?? artifacts/supervised_baselines/dejavu_gate_final.json",
                "?? {}/logistic/re2ob/fold_0/status.json".format(relative_output),
            )

            def fit_predict(_train_events, _train_roots, test_events, _run_dir):
                return {
                    event.case_id: np.arange(len(event.candidates), dtype=float)
                    for event in test_events
                }

            with patch.object(
                common,
                "current_git_identity",
                return_value={
                    "head": "test",
                    "branch": "test",
                    "dirty_entries": dirty_entries,
                },
            ):
                result = common.run_fold(
                    PROJECT_ROOT,
                    "re2ob",
                    1,
                    "toy",
                    output_root,
                    {"normalization": "none"},
                    fit_predict,
                    {},
                )
            self.assertEqual(result["integrity"]["status"], "PASS")

    def test_in_worktree_output_root_cannot_escape_supervised_namespace(self):
        output_root = PROJECT_ROOT / "docs" / "supervised_baseline_test_output"
        with patch.dict(
            os.environ, {"PYTHONHASHSEED": "20260826"}
        ), patch.object(
            common,
            "current_git_identity",
            return_value={"head": "test", "branch": "test", "dirty_entries": ()},
        ):
            with self.assertRaisesRegex(ValueError, "supervised_baselines"):
                common.run_fold(
                    PROJECT_ROOT,
                    "re2ob",
                    0,
                    "toy",
                    output_root,
                    {"normalization": "none"},
                    lambda *_args: {},
                    {},
                )
        self.assertFalse(output_root.exists())

    def test_non_artifact_dirty_entry_remains_rejected(self):
        with tempfile.TemporaryDirectory() as output_root, patch.dict(
            os.environ, {"PYTHONHASHSEED": "20260826"}
        ), patch.object(
            common,
            "current_git_identity",
            return_value={
                "head": "test",
                "branch": "test",
                "dirty_entries": (" M src/rca/supervised_baselines/common.py",),
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "non-artifact worktree changes"):
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
