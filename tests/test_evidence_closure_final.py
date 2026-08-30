import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from src.rca.evidence_final import build_final_evidence_decision


ROOT = Path(__file__).resolve().parents[1]
STARTING_HEAD = "781f4535d7d48c859d348657a01d932650cb521e"
FINAL_ARTIFACT = ROOT / "artifacts/evidence_closure/final_decision_v1_1.json"
BOOTSTRAP = ROOT / "artifacts/evidence_closure/bootstrap_corrected_v1_1.json"
LEGACY_BOOTSTRAP = ROOT / "artifacts/opt/final/bootstrap.json"
LEGACY_BOOTSTRAP_SHA256 = (
    "23cd9e27592746191f116a163341f5b8d241ad290a7572aef2ea882f711d927e"
)


def _sha256(path):
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class EvidenceClosureFinalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = build_final_evidence_decision(ROOT)
        cls.bootstrap = json.loads(BOOTSTRAP.read_text(encoding="utf-8"))

    def test_final_decision_matches_persisted_artifact(self):
        persisted = json.loads(FINAL_ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(persisted, self.decision)
        self.assertEqual(
            self.decision["final_decision"],
            "RCA_FREEZE_READY_WITH_LIMITATION",
        )
        self.assertTrue(self.decision["integrity_conditions_pass"])
        self.assertFalse(self.decision["unconditional_scientific_freeze_ready"])
        self.assertTrue(all(self.decision["conditions"].values()))

    def test_v1_and_per_dataset_evidence_levels_remain_distinct(self):
        v1 = self.decision["v1_scientific_integrity"]
        self.assertEqual(v1["full_ranking_integrity"], "FULL_RANKING_INTEGRITY_PASS")
        self.assertEqual(v1["independent_rank_metrics"], "PASS")
        per_dataset = self.decision["optimization_post_study_integrity"]
        self.assertEqual(
            per_dataset["per_dataset_full_ranking_integrity"],
            "FULL_RANKING_INTEGRITY_NOT_AUDITABLE",
        )
        self.assertEqual(
            per_dataset["per_dataset_rank_metric_sufficiency"],
            "RANK_METRIC_SUFFICIENT_PASS",
        )

    def test_canonical_bootstrap_values_are_unchanged(self):
        comparisons = self.bootstrap["comparisons"]
        global_comparison = comparisons["GLOBAL-OPT_minus_V1"]["datasets"]
        for dataset in global_comparison.values():
            for metric in dataset["metrics"].values():
                self.assertEqual(metric["point_delta"], 0.0)
                self.assertEqual(metric["ci95"], [0.0, 0.0])

        per_dataset = comparisons["PER-DATASET-OPT_minus_V1"]["datasets"]
        expected = {
            "re2ob": {
                "Avg@5": (-0.011111111111111112, [-0.026666666666666665, 0.0]),
                "AC@1": (-0.022222222222222223, [-0.05555555555555555, 0.0]),
                "MRR": (-0.015740740740740743, [-0.03796296296296297, 0.0]),
            },
            "re2tt": {
                "Avg@5": (0.006666666666666665, [-0.03333333333333334, 0.04666666666666667]),
                "AC@1": (0.07777777777777778, [0.0, 0.15555555555555556]),
                "MRR": (0.03577755517298001, [-0.013265047709492146, 0.08708927613175976]),
            },
        }
        for dataset, metrics in expected.items():
            for metric_name, (point, interval) in metrics.items():
                actual = per_dataset[dataset]["metrics"][metric_name]
                self.assertEqual(actual["point_delta"], point)
                self.assertEqual(actual["ci95"], interval)

    def test_legacy_bootstrap_artifact_is_untouched(self):
        self.assertEqual(_sha256(LEGACY_BOOTSTRAP), LEGACY_BOOTSTRAP_SHA256)
        changed = subprocess.check_output(
            (
                "git",
                "diff",
                "--name-only",
                STARTING_HEAD,
                "--",
                "artifacts/opt/final/bootstrap.json",
            ),
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(changed, "")

    def test_tree_rankers_remain_not_executed(self):
        statuses = self.decision["historical_and_ranker_semantics"]["rankers"]
        self.assertEqual(statuses["Conditional Logit"], "EXECUTED")
        for ranker in ("XGBoost", "LightGBM"):
            self.assertEqual(
                statuses[ranker],
                "NOT EXECUTED — DEPENDENCY UNAVAILABLE",
            )

    def test_frozen_prediction_rank_score_and_feature_files_are_unchanged(self):
        changed = subprocess.check_output(
            (
                "git",
                "diff",
                "--name-only",
                STARTING_HEAD,
                "--",
                "artifacts/final_method",
                "artifacts/opt/final",
                "artifacts/opt/o4_nested",
                "artifacts/features",
            ),
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(changed, "")
        self.assertEqual(
            self.decision["immutability"]["changed_frozen_predictive_paths"], []
        )

    def test_final_evidence_docs_do_not_canonize_legacy_tt_interval(self):
        forbidden = "[-0.1400, -0.0244]"
        for relative_path in (
            "docs/RCA_FINAL_SCIENTIFIC_FREEZE_V1.md",
            "docs/RCA_THESIS_RESULTS_PACKAGE.md",
            "docs/RCA_THESIS_CLAIM_MATRIX.md",
        ):
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn(forbidden, text, relative_path)

    def test_canonical_index_routes_and_marks_legacy_summary_superseded(self):
        index = (ROOT / "docs/RCA_EVIDENCE_INDEX.md").read_text(encoding="utf-8")
        readme = (ROOT / "docs/README.md").read_text(encoding="utf-8")
        self.assertIn("## CANONICAL CURRENT EVIDENCE", index)
        self.assertIn("## HISTORICAL / SUPERSEDED", index)
        for filename in (
            "RCA_FINAL_SCIENTIFIC_FREEZE_V1.md",
            "RCA_THESIS_RESULTS_PACKAGE.md",
            "RCA_THESIS_CLAIM_MATRIX.md",
            "BOOTSTRAP_FORENSIC_AUDIT.md",
            "TELEMETRY_INFORMATION_LOSS_AUDIT_V1_1.md",
            "TRACE_ERROR_REPRESENTATION_INVARIANT.md",
            "EVIDENCE_ERRATA.md",
        ):
            self.assertIn(filename, index)
        legacy_section = index.split("## HISTORICAL / SUPERSEDED", 1)[1]
        normalized_legacy = " ".join(legacy_section.split())
        self.assertIn("OPT_FINAL_EVIDENCE_SUMMARY.md", normalized_legacy)
        self.assertIn("bootstrap intervals are superseded", normalized_legacy)
        self.assertIn("historical terminology is superseded", normalized_legacy)
        self.assertIn(
            "must not be used as canonical thesis evidence", normalized_legacy
        )
        self.assertIn("RCA_EVIDENCE_CLOSURE_FAILURE.md", normalized_legacy)
        self.assertIn("RCA_EVIDENCE_INDEX.md", readme)


if __name__ == "__main__":
    unittest.main()
