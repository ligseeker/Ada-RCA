from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from src.baseline_eval.confirmatory import DATASET_ORDER, expected_case_ids, sha256_file
from src.baseline_eval.final_comparison import (
    FINAL_BASELINE_METHODS,
    FINAL_OUTPUT_RELATIVES,
    FINAL_REPORT_ORDER,
    FINAL_REPORT_RELATIVE,
    FROZEN_V2_EVALUATION_SHA256,
    SCOPE_LOCK_RELATIVE,
    V2_EVALUATION_RELATIVES,
    FinalComparisonBlocked,
    _assert_file_digest,
    _load_frozen_v2_evidence,
    _load_scope_lock,
    validate_final_outputs,
    verify_baro_v1_lock,
    verify_six_method_v2_lock,
)


ROOT = Path(__file__).resolve().parents[1]


def _published_v3() -> bool:
    return all((ROOT / relative).is_file() for relative in FINAL_OUTPUT_RELATIVES) and (
        ROOT / FINAL_REPORT_RELATIVE
    ).is_file()


class FinalComparisonScopeAndBaroLockTest(unittest.TestCase):
    def test_scope_lock_must_be_committed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / SCOPE_LOCK_RELATIVE).parent.mkdir(parents=True)
            shutil.copy2(ROOT / SCOPE_LOCK_RELATIVE, root / SCOPE_LOCK_RELATIVE)
            subprocess.run(("git", "init", "--quiet"), cwd=root, check=True)
            with self.assertRaises(FinalComparisonBlocked):
                _load_scope_lock(root)

    def test_baro_lock_is_complete_and_label_free(self):
        audit = verify_baro_v1_lock(ROOT)
        lock = audit["lock"]
        self.assertEqual(lock["method"], "BARO")
        self.assertEqual(lock["disposition"], "EXECUTION_COMPLETE")
        self.assertFalse(lock["contains_evaluation"])
        self.assertEqual(lock["record_counts"], {dataset: 90 for dataset in DATASET_ORDER})
        for dataset in DATASET_ORDER:
            self.assertEqual(
                lock["status_counts"][dataset],
                {
                    "SUCCESS": 90,
                    "METHOD_FAILURE": 0,
                    "ADAPTER_FAILURE": 0,
                    "DATA_FAILURE": 0,
                    "TIMEOUT": 0,
                },
            )
            self.assertEqual(len(audit["records"][dataset]), 90)
        self.assertEqual(audit["lock_commit"], "fbfb6e6e1f112f93fe544f8b6c71aca4f5b336f7")

    def test_baro_record_digest_mutation_fails_closed(self):
        audit = verify_baro_v1_lock(ROOT)
        lock = audit["lock"]
        bound = next(item for item in lock["terminal_record_digests"] if item["dataset"] == "re2ob")
        source = ROOT / "artifacts/baseline_eval/execution_v1/records/baro" / lock["attempt_id"] / bound["dataset"] / f"{bound['case_id']}.json"
        with tempfile.TemporaryDirectory() as temporary:
            mutated = Path(temporary) / source.name
            mutated.write_bytes(source.read_bytes() + b"\n")
            with self.assertRaises(FinalComparisonBlocked):
                _assert_file_digest(mutated, bound["sha256"], "mutated BARO record")

    def test_baro_case_universe_is_exactly_the_frozen_90_case_universe(self):
        audit = verify_baro_v1_lock(ROOT)
        lock = audit["lock"]
        for dataset in DATASET_ORDER:
            expected = tuple(expected_case_ids(ROOT, dataset))
            observed = tuple(row["case_id"] for row in audit["records"][dataset])
            self.assertEqual(observed, expected)
            self.assertEqual(lock["expected_case_ids"][dataset], list(expected))
            self.assertEqual(len(set(observed)), 90)

    def test_six_method_combined_lock_is_verified_without_evaluation(self):
        audit = verify_six_method_v2_lock(ROOT)
        self.assertEqual(audit["lock"]["method_order"], list(FINAL_BASELINE_METHODS[1:]))
        self.assertFalse(audit["lock"]["labels_joined"])
        self.assertFalse(audit["lock"]["contains_evaluation"])


@unittest.skipUnless(_published_v3(), "published V3 final comparison is required")
class PublishedFinalComparisonRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = validate_final_outputs(ROOT, require_committed=False)
        cls.final = cls.data["final"]
        cls.v2 = cls.data["v2"]

    def test_existing_six_method_overall_values_are_exactly_unchanged(self):
        actual = {row["Method"]: row for row in self.final["overall"]["table_a"]["rows"]}
        for method in (*FINAL_BASELINE_METHODS[1:], "Ada-RCA"):
            self.assertEqual(actual[method], self.v2["overall_by_method"][method])
            for dataset in DATASET_ORDER:
                key = f"{method}__{dataset}"
                self.assertEqual(
                    self.final["overall"]["method_dataset_metrics"][key],
                    self.v2["payloads"]["overall"]["method_dataset_metrics"][key],
                )

    def test_existing_six_method_fault_rows_are_exactly_unchanged(self):
        actual = {
            (row["method"], row["dataset"], row["fault"]): row
            for row in self.final["fault_level"]["rows"]
        }
        for key, row in self.v2["fault_index"].items():
            self.assertEqual(actual[key], row)

    def test_existing_six_method_bootstrap_rows_are_exactly_unchanged(self):
        actual = {
            (row["method"], row["dataset"]): row
            for row in self.final["paired_bootstrap"]["rows"]
        }
        for key, row in self.v2["bootstrap_index"].items():
            self.assertEqual(actual[key], row)

    def test_final_table_contains_exactly_seven_baselines_and_ada_rca(self):
        self.assertEqual(
            [row["Method"] for row in self.final["overall"]["table_a"]["rows"]],
            list(FINAL_REPORT_ORDER),
        )
        self.assertEqual(
            {row["method"] for row in self.final["fault_level"]["rows"]},
            set(FINAL_REPORT_ORDER),
        )

    def test_ada_rca_identity_is_preserved(self):
        ada = next(row for row in self.final["overall"]["table_a"]["rows"] if row["Method"] == "Ada-RCA")
        self.assertEqual(ada["OB AC@1"], 0.8777777778)
        self.assertEqual(ada["OB AC@3"], 0.9888888889)
        self.assertEqual(ada["OB AC@5"], 0.9888888889)
        self.assertEqual(ada["OB Avg@5"], 0.9622222222)
        self.assertEqual(ada["TT AC@1"], 0.7111111111)
        self.assertEqual(ada["TT AC@3"], 0.8666666667)
        self.assertEqual(ada["TT AC@5"], 0.9333333333)
        self.assertEqual(ada["TT Avg@5"], 0.8511111111)

    def test_baro_mrr_and_candidate_completion_are_not_invented(self):
        for dataset in DATASET_ORDER:
            metrics = self.final["overall"]["method_dataset_metrics"][f"BARO__{dataset}"]
            self.assertEqual(metrics["MRR"], "NOT-IDENTIFIABLE")
            self.assertEqual(metrics["MRR_legality"], "NOT-IDENTIFIABLE")
        provenance = self.final["provenance"]
        self.assertEqual(provenance["adapter_contract"]["candidate_completion"], "NONE")
        baro_row = next(
            row for row in self.final["comparability"]["table_d"]["rows"] if row["method"] == "BARO"
        )
        self.assertEqual(baro_row["complete_service_ranking"], "NO")

    def test_datasets_remain_separate(self):
        self.assertIn("FORBIDDEN", self.final["overall"]["table_a"]["pooling"])
        self.assertTrue(self.final["paired_bootstrap"]["datasets_separate"])
        self.assertEqual(
            {(row["method"], row["dataset"]) for row in self.final["paired_bootstrap"]["rows"]},
            {(method, dataset) for method in FINAL_BASELINE_METHODS for dataset in DATASET_ORDER},
        )

    def test_final_report_contains_baro_and_composite_wording(self):
        report = (ROOT / FINAL_REPORT_RELATIVE).read_text(encoding="utf-8")
        normalized_report = " ".join(report.split())
        for text in (
            "BARO",
            "Seven-Baseline Final Composite Comparison",
            "composite comparison",
            "not a claim that all seven baselines were executed under one original pre-label global lock",
            "V1_LOCKED_COMPLETE",
            "NOT-IDENTIFIABLE",
            "does not support an SOTA",
        ):
            self.assertIn(text, normalized_report)

    def test_old_v2_evaluation_files_retain_frozen_sha256(self):
        for name, relative in V2_EVALUATION_RELATIVES.items():
            self.assertEqual(sha256_file(ROOT / relative), FROZEN_V2_EVALUATION_SHA256[name])

    def test_final_artifact_method_sets_and_tracks_are_valid(self):
        self.assertEqual(
            {row["method"] for row in self.final["robustness"]["table_c"]["rows"]},
            set(FINAL_BASELINE_METHODS),
        )
        self.assertEqual(
            {row["method"] for row in self.final["comparability"]["table_d"]["rows"]},
            set(FINAL_REPORT_ORDER),
        )
        self.assertEqual(
            self.final["provenance"]["evidence_tracks"]["BARO"],
            "V1_LOCKED_COMPLETE",
        )


if __name__ == "__main__":
    unittest.main()
