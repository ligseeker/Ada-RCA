import json
from pathlib import Path
import unittest

from scripts.run_v2_f0 import (
    MODALITIES,
    VARIANT_MODALITIES,
    feature_indices,
    feature_names,
    full_z2_identity,
    verify_checksums,
)
from src.rca.final_method import FINAL_Z2_FEATURE_NAMES, load_dataset, read_jsonl
from src.rca.p4 import verify_complete_prediction
from src.rca.p4_stats import evaluate_predictions


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

    def test_f0_identity_is_ranking_and_metric_identity(self):
        fresh = ({
            "case_id": "opaque-case",
            "ranking": ["a", "b"],
            "candidate_scores": {"a": 2.0, "b": 1.0},
        },)
        committed = ({
            "case_id": "opaque-case",
            "ranking": ["a", "b"],
            "candidate_scores": {"a": 2.0 + 2e-12, "b": 1.0},
        },)
        metrics = {"Avg@5": 1.0}
        identity = full_z2_identity(fresh, committed, metrics, dict(metrics))
        self.assertTrue(identity["integrity_valid"])
        self.assertTrue(identity["ranking_identical"])
        self.assertTrue(identity["overall_metrics_identical"])
        self.assertGreater(identity["max_abs_score_difference"], 1e-12)


class V2F0FormalArtifactTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parents[1]
        cls.artifact_root = cls.project_root / "artifacts" / "v2" / "f0_modality_audit"
        if not cls.artifact_root.is_dir():
            raise unittest.SkipTest("formal V2-F0 artifacts not generated")

    def test_root_and_per_run_checksums(self):
        self.assertTrue(verify_checksums(self.artifact_root))
        for dataset in ("re2ob", "re2tt"):
            for variant, _ in VARIANT_MODALITIES:
                self.assertTrue(verify_checksums(self.artifact_root / variant / dataset))

    def test_all_variant_metrics_recompute_from_complete_rankings(self):
        for dataset in ("re2ob", "re2tt"):
            events, labels, roots, assignments = load_dataset(self.project_root, dataset)
            candidates = {case_id: event.candidates for case_id, event in events.items()}
            for variant, modalities in VARIANT_MODALITIES:
                run_dir = self.artifact_root / variant / dataset
                rows = list(read_jsonl(run_dir / "predictions.jsonl"))
                self.assertEqual(len(rows), 90)
                for row in rows:
                    case_id = str(row["case_id"])
                    verify_complete_prediction(row, candidates[case_id], roots[case_id])
                    self.assertEqual(int(row["fold"]), assignments[case_id])
                    self.assertEqual(int(row["root_rank"]), row["ranking"].index(roots[case_id]) + 1)
                recomputed = evaluate_predictions(rows, candidates, roots)
                persisted = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
                self.assertEqual(recomputed["overall_cases"], persisted["overall_cases"])
                config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
                self.assertEqual(config["feature_dimension"], 17 * len(modalities))
                self.assertEqual(tuple(config["feature_names"]), feature_names(modalities))

    def test_resume_and_v1_identity_are_disclosed(self):
        manifest = json.loads((self.artifact_root / "run_manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["resumed"])
        self.assertFalse(manifest["fits_rerun"])
        self.assertEqual(manifest["fit_source_commits"], ["d3041956ca376835831293e971304bcad0129afa"])
        for dataset in ("re2ob", "re2tt"):
            identity = manifest["identity"][dataset]
            self.assertTrue(identity["integrity_valid"])
            self.assertTrue(identity["ranking_identical"])
            self.assertTrue(identity["overall_metrics_identical"])


if __name__ == "__main__":
    unittest.main()
