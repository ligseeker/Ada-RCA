import unittest
import json

import numpy as np
from pathlib import Path

from src.rca.final_audit import (
    S1_FEATURE_NAMES,
    S2_FEATURE_NAMES,
    aggregate_expected,
    observability_event,
    fit_control_oof,
    _pre_binned_indicators,
    _pre_q_by_service,
    s0_rankings,
)
from src.rca.final_method import load_dataset
from src.rca.features import _binned_indicators, _q_by_service
from src.rca.p4_stats import evaluate_predictions
from src.rca.p4 import CandidateEvent


class FinalAuditControlsTest(unittest.TestCase):
    def test_s1_uses_only_coverage_and_channel_availability(self):
        base = np.arange(2 * 4 * 8, dtype=float).reshape(2, 4, 8)
        event = observability_event("case", ("a", "b"), base)
        expected = base[:, :, (6, 7)].reshape(2, 8)
        np.testing.assert_array_equal(event.features, expected)
        self.assertEqual(len(S1_FEATURE_NAMES), 8)
        self.assertFalse(any("onset" in name or "magnitude" in name for name in S1_FEATURE_NAMES))

    def test_s2_schema_is_exactly_four_pre_fields_per_channel(self):
        self.assertEqual(len(S2_FEATURE_NAMES), 16)
        self.assertEqual(S2_FEATURE_NAMES[:4], (
            "metric.pre_mean_q", "metric.pre_max_q", "metric.pre_coverage", "metric.pre_available",
        ))
        self.assertTrue(all("post" not in name for name in S2_FEATURE_NAMES))

    def test_s0_tie_neutral_expectation_is_analytical(self):
        candidates = ("a", "b", "c", "d")
        events = {
            "train_a": CandidateEvent("train_a", candidates, np.zeros((4, 1))),
            "train_b": CandidateEvent("train_b", candidates, np.zeros((4, 1))),
            "test": CandidateEvent("test", candidates, np.zeros((4, 1))),
        }
        roots = {"train_a": "a", "train_b": "b", "test": "a"}
        assignments = {"train_a": 1, "train_b": 2, "test": 0}
        deterministic, expected, seen = s0_rankings(events, roots, assignments)
        test_row = next(row for row in expected if row["case_id"] == "test")
        self.assertEqual(test_row["tie_group_size"], 2)
        self.assertEqual(test_row["higher_score_count"], 0)
        self.assertEqual(test_row["AC@1"], 0.5)
        self.assertEqual(test_row["AC@3"], 1.0)
        self.assertAlmostEqual(test_row["MRR"], 0.75)

    def test_formal_observability_control_satisfies_gradient_tolerance(self):
        root = Path(__file__).resolve().parents[1]
        events, labels, roots, assignments = load_dataset(root, "re2ob")
        s1_events = {}
        for case_id, event in events.items():
            with np.load(root / "artifacts" / "features" / "re2ob" / (case_id + ".npz")) as data:
                s1_events[case_id] = observability_event(case_id, event.candidates, data["base"])
        predictions, fits = fit_control_oof(s1_events, roots, assignments)
        self.assertEqual(len(predictions), 90)
        self.assertTrue(all(fit.converged for fit in fits.values()))
        self.assertLessEqual(max(fit.gradient_norm for fit in fits.values()), 1e-8)

    def test_pre_only_q_matches_frozen_full_path_on_pre_bins(self):
        root = Path(__file__).resolve().parents[1]
        dataset = "re2ob"
        inputs = [json.loads(line) for line in (root / "artifacts" / "source" / dataset / "inputs.jsonl").read_text().splitlines()]
        sources = [json.loads(line) for line in (root / "artifacts" / "source" / dataset / "sources.jsonl").read_text().splitlines()]
        input_row = sorted(inputs, key=lambda row: row["case_id"])[0]
        source_row = {row["case_id"]: row for row in sources}[input_row["case_id"]]
        candidates = tuple(input_row["candidates"])
        pre_indicators = _pre_binned_indicators(Path(source_row["simple_metrics_path"]), "time", candidates, "metric", input_row["anchor_time"])
        full_indicators = _binned_indicators(Path(source_row["simple_metrics_path"]), "time", candidates, "metric", input_row["anchor_time"])
        pre_q = _pre_q_by_service(pre_indicators, candidates)
        full_q, _ = _q_by_service(full_indicators, candidates)
        np.testing.assert_allclose(pre_q, full_q[:, :40], rtol=0, atol=0, equal_nan=True)

    def test_formal_control_artifacts_recompute_and_converge(self):
        root = Path(__file__).resolve().parents[1]
        audit_root = root / "artifacts" / "final_audit"
        if not (audit_root / "summary.json").is_file():
            self.skipTest("formal controls not generated")
        summary = json.loads((audit_root / "summary.json").read_text())
        self.assertEqual(
            {name: report["state"] for name, report in summary["comparisons"].items()},
            {"s0_deterministic": "CONTROL_SEPARATED", "s0_tie_neutral": "CONTROL_SEPARATED", "s1": "CONTROL_SEPARATED", "s2": "CONTROL_SEPARATED"},
        )
        for dataset in ("re2ob", "re2tt"):
            events, labels, roots, assignments = load_dataset(root, dataset)
            candidates = {case_id: event.candidates for case_id, event in events.items()}
            for control in ("s0_deterministic", "s1", "s2"):
                rows = [json.loads(line) for line in (audit_root / "controls" / dataset / (control + "_predictions.jsonl")).read_text().splitlines()]
                persisted = json.loads((audit_root / "controls" / dataset / (control + "_metrics.json")).read_text())
                self.assertEqual(evaluate_predictions(rows, candidates, roots)["overall_cases"], persisted["overall_cases"])
            for control in ("s1", "s2"):
                manifest = json.loads((audit_root / "controls" / dataset / (control + "_model_state") / "manifest.json").read_text())
                self.assertTrue(all(row["converged"] for row in manifest.values()))
                self.assertLessEqual(max(row["gradient_norm"] for row in manifest.values()), 1e-8)
            pre_manifest = json.loads((audit_root / "pre_event_features" / dataset / "manifest.json").read_text())
            self.assertEqual(pre_manifest["window"], "[t0-600,t0)")
            self.assertFalse(pre_manifest["post_event_information_used"])


if __name__ == "__main__":
    unittest.main()
