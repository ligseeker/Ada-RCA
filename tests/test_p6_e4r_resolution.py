import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.rca.p6_baselines import (
    load_mmbaro_inputs,
    raw_call,
    summarize_repeat_records,
)
from src.rca.p6_e4 import RCAEVAL_SHA


ROOT = Path(__file__).resolve().parents[1]
RCAEVAL_ROOT = Path("/home/zhangll24/RCA_project/RCAEval-clean")
E4R = ROOT / "artifacts" / "p6_e4r"
DATASET = Path("/home/zhangll24/RCA_project/datasets/RCAEval/RE2-OB")


class P6E4RResolutionTest(unittest.TestCase):
    def test_historical_artifacts_unchanged(self):
        expected = {
            "docs/P6_E4_TIER_A_INTEGRATION_QUALIFICATION_PROTOCOL.md": "a29e7d5524ffadcaeb812bd7a48da435c5619ac7969e00a6b0c7ca1ecba90834",
            "docs/P6_E4_TIER_A_INTEGRATION_QUALIFICATION_REPORT.md": "ac8eaa26ed2a423850358d8169d180a4da90f17bff1dd49beddd47d814bd4774",
            "docs/P6_G1_INTEGRATION_QUALIFICATION_DECISION.md": "4a9492a908ea3223b4f7daa80e8ed4f794afba4640f7d9b34137f29f8b988af2",
        }
        for relative, digest in expected.items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), digest)

    def test_unsupported_mm_alias_is_not_used(self):
        audit = json.loads((E4R / "mmbaro/dataset_alias_audit.json").read_text())
        self.assertFalse(audit["alias_used"])
        self.assertEqual(audit["official_dataset_identifiers"], ["re2-ob", "re2-tt"])

    def test_official_identifiers_and_active_modalities(self):
        audit = json.loads((E4R / "mmbaro/modality_activation_audit.json").read_text())
        self.assertEqual(audit["active_score_modalities"], ["metric", "log_time_series"])
        self.assertFalse(audit["trace_branches_active"])
        self.assertFalse(audit["tri_modal_claim_permitted"])
        summary = json.loads((E4R / "mmbaro/qualification_summary.json").read_text())
        self.assertEqual(summary["status"], "READY_OFFICIAL_RE2_METRIC_LOG")

    def test_raw_modalities_are_not_misreported(self):
        audit = json.loads((E4R / "mmbaro/modality_activation_audit.json").read_text())
        for key in ("raw_logs", "raw_spans", "cluster_info", "trace_error_time_series", "trace_latency_time_series"):
            self.assertEqual(audit[key], "NOT_USED_BY_SCORE")

    def test_no_candidate_completion_or_performance_dependency(self):
        source = "\n".join((ROOT / path).read_text() for path in ("src/rca/p6_e4.py", "src/rca/p6_baselines.py", "scripts/p6_e4r_mmbaro.py"))
        self.assertNotIn("RCACaseLabel", source)
        self.assertNotIn("root_service", source)
        self.assertNotIn("RCAEval.benchmark", source)
        self.assertNotIn("completed_with_unranked_services = True", source)
        for path in (E4R / "mmbaro/ob_smoke.jsonl", E4R / "mmbaro/tt_smoke.jsonl"):
            for line in path.read_text().splitlines():
                self.assertFalse(json.loads(line)["completed_with_unranked_services"])

    def test_deterministic_mmbaro_repeats(self):
        for name in ("ob_smoke.jsonl", "tt_smoke.jsonl"):
            rows = [json.loads(line) for line in (E4R / "mmbaro" / name).read_text().splitlines()]
            self.assertEqual(len(rows), 6)
            self.assertTrue(summarize_repeat_records(rows)["deterministic_repeats"])
            self.assertTrue(all(row["dataset_alias_used"] is False for row in rows))

    def test_fa_is_distinct_from_fb(self):
        result = raw_call(lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyError("native")), object())
        self.assertEqual(result["execution_status"], "F-A_ALGORITHMIC_FAILURE")
        self.assertNotEqual(result["execution_status"], "F-B_UNSUPPORTED_INPUT")

    def test_fc_fd_policy_is_explicit(self):
        policy = (ROOT / "docs/P6_E5_BASELINE_FAILURE_POLICY.md").read_text()
        self.assertIn("NR / NOT RUN", policy)
        self.assertIn("F-D means the adapter or integration is invalid", policy)
        self.assertIn("assign utility 0", policy)
        self.assertIn("F-B only when upstream explicitly establishes", policy)

    def test_clean_rcaeval_and_official_source(self):
        head = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=RCAEVAL_ROOT, text=True).strip()
        status = subprocess.check_output(("git", "status", "--porcelain"), cwd=RCAEVAL_ROOT, text=True).strip()
        self.assertEqual(head, RCAEVAL_SHA)
        self.assertEqual(status, "")

    def test_input_dictionary_has_active_sources(self):
        case = next(DATASET.glob("*/*"))
        inject = int((case / "inject_time.txt").read_text().strip())
        loaded = load_mmbaro_inputs(case, inject)
        self.assertEqual(loaded["active_modalities"], ["metric", "log_time_series"])
        self.assertGreater(loaded["metric"]["pre_rows"], 0)
        self.assertGreater(loaded["metric"]["post_rows"], 0)
        self.assertGreater(loaded["logts"]["pre_rows"], 0)
        self.assertGreater(loaded["logts"]["post_rows"], 0)


if __name__ == "__main__":
    unittest.main()
