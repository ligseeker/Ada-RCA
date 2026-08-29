import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import pandas as pd

from src.rca.p6_e4 import (
    BASE_SHA,
    DATASETS,
    RCAEVAL_SHA,
    SOURCE_CHECKSUM_PATHS,
    build_smoke_manifest,
    sha256_file,
)
from src.rca.p6_baselines import (
    TRACE_CONVERSION_FACTOR,
    build_mmbaro_alias_audit,
    build_mmbaro_input_dictionary_audit,
    build_mmbaro_modality_audit,
    indicator_service,
    load_metric_window,
    load_trace_window,
    operation_service_map,
    project_indicator_ranking,
    project_operation_ranking,
    raw_call,
    summarize_repeat_records,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RCAEVAL_ROOT = Path("/home/zhangll24/RCA_project/RCAEval-clean")
ARTIFACT_ROOT = PROJECT_ROOT / "artifacts" / "p6_e4"


class P6E4BaselineQualificationTest(unittest.TestCase):
    def test_01_baseline_branch_base_sha_guard(self):
        branch = subprocess.check_output(
            ("git", "branch", "--show-current"), cwd=PROJECT_ROOT, text=True
        ).strip()
        merge_base = subprocess.check_output(
            ("git", "merge-base", "HEAD", "main"), cwd=PROJECT_ROOT, text=True
        ).strip()
        self.assertEqual(branch, "exp/p6-baselines")
        self.assertEqual(merge_base, BASE_SHA)

    def test_02_clean_rcaeval_pinned_sha_guard(self):
        head = subprocess.check_output(
            ("git", "rev-parse", "HEAD"), cwd=RCAEVAL_ROOT, text=True
        ).strip()
        status = subprocess.check_output(
            ("git", "status", "--porcelain"), cwd=RCAEVAL_ROOT, text=True
        ).strip()
        self.assertEqual(head, RCAEVAL_SHA)
        self.assertEqual(status, "")

    def test_03_source_checksum_guard(self):
        provenance = json.loads((ARTIFACT_ROOT / "upstream_provenance.json").read_text())
        current = {path: sha256_file(RCAEVAL_ROOT / path) for path in SOURCE_CHECKSUM_PATHS}
        self.assertEqual(current, provenance["source_sha256"])

    def test_04_smoke_manifest_determinism(self):
        stored = json.loads((ARTIFACT_ROOT / "smoke_case_manifest.json").read_text())
        self.assertEqual(build_smoke_manifest(DATASETS), stored)

    def test_05_qualification_has_no_label_or_evaluator_dependency(self):
        source = "\n".join(
            (PROJECT_ROOT / path).read_text()
            for path in ("src/rca/p6_e4.py", "src/rca/p6_baselines.py", "scripts/p6_e4_qualify.py")
        )
        for forbidden in ("src.rca.evaluator", "RCAEval.benchmark", "RCACaseLabel", "root_service"):
            self.assertNotIn(forbidden, source)

    def test_06_baro_window_correctness(self):
        with tempfile.TemporaryDirectory() as directory:
            case = Path(directory)
            t0 = 1000
            rows = ["time,svc_cpu,svc_mem"]
            rows.extend("{},{},{}".format(time, time, time) for time in range(399, 1601))
            (case / "simple_metrics.csv").write_text("\n".join(rows) + "\n")
            loaded = load_metric_window(case, t0)
            self.assertEqual(loaded["window_rows"], 1200)
            self.assertEqual(loaded["pre_rows"], 600)
            self.assertEqual(loaded["post_rows"], 600)
            self.assertEqual(int(loaded["data"]["time"].min()), 400)
            self.assertEqual(int(loaded["data"]["time"].max()), 1599)

    def test_07_baro_mapping_correctness(self):
        registry = ("frontend", "ts-auth-service")
        self.assertEqual(indicator_service("frontend_cpu", registry), ("frontend", "LEGAL_PREFIX"))
        self.assertEqual(
            indicator_service("ts-auth-service_latency", registry),
            ("ts-auth-service", "LEGAL_PREFIX"),
        )

    def test_08_service_dedup_preserves_first_occurrence(self):
        result = project_indicator_ranking(
            ("svc_cpu", "other_mem", "svc_mem"), ("svc", "other")
        )
        self.assertEqual(result["ranking"], ["svc", "other"])
        self.assertEqual(result["duplicate_count"], 1)

    def test_09_partial_ranking_is_not_completed(self):
        result = project_indicator_ranking(("svc_cpu",), ("svc", "other"))
        self.assertEqual(result["ranking"], ["svc"])
        self.assertFalse(result["completed_with_unranked_services"])

    def test_10_tracerca_timestamp_conversion_rule(self):
        audit = json.loads(
            (ARTIFACT_ROOT / "tracerca" / "timestamp_unit_audit.json").read_text()
        )
        self.assertEqual(TRACE_CONVERSION_FACTOR, 1_000_000)
        self.assertEqual(audit["chosen_conversion_factor"], TRACE_CONVERSION_FACTOR)
        self.assertEqual(audit["status"], "UNIQUE_SEMANTICS_JUSTIFIED")

    def test_11_tracerca_pre_post_partition(self):
        with tempfile.TemporaryDirectory() as directory:
            case = Path(directory)
            frame = pd.DataFrame(
                {
                    "traceID": ["a", "b", "c", "d"],
                    "spanID": ["1", "2", "3", "4"],
                    "serviceName": ["svc"] * 4,
                    "methodName": ["m"] * 4,
                    "operationName": ["m"] * 4,
                    "startTime": [399_000_000, 999_000_000, 1_200_000_000, 1_599_000_000],
                    "duration": [1_000_000, 1_000_000, 1_000_000, 1_000_000],
                }
            )
            frame.to_csv(case / "traces.csv", index=False)
            loaded = load_trace_window(case, 1000)
            self.assertEqual(loaded["selected_spans"], 3)
            self.assertEqual(loaded["pre_spans"], 1)
            self.assertEqual(loaded["post_spans"], 2)

    def test_12_tracerca_operation_to_service_mapping(self):
        spans = pd.DataFrame(
            {
                "serviceName": ["svc", "other"],
                "methodName": ["m", None],
                "operationName": ["m", "fallback"],
            }
        )
        audit = operation_service_map(spans)
        self.assertEqual(audit["conflicts"], {})
        projected = project_operation_ranking(
            ("svc_m", "other_fallback"), audit["mapping"], ("svc", "other")
        )
        self.assertEqual(projected["ranking"], ["svc", "other"])

    def test_13_mmbaro_input_dictionary_schema(self):
        audit = build_mmbaro_input_dictionary_audit(RCAEVAL_ROOT / "RCAEval/e2e/baro.py")
        self.assertEqual(
            audit["dictionary_keys_accessed"],
            ["cluster_info", "logs", "logts", "metric", "traces", "tracets_err", "tracets_lat"],
        )

    def test_14_mmbaro_dataset_alias_guard(self):
        audit = build_mmbaro_alias_audit()
        self.assertFalse(audit["mapping_frozen"])
        self.assertEqual(audit["status"], "BLOCKED / SEMANTIC_AMBIGUITY")

    def test_15_mmbaro_modality_activation(self):
        audit = build_mmbaro_modality_audit(build_mmbaro_alias_audit())
        self.assertEqual(audit["modalities"]["metric"], "USED")
        self.assertEqual(audit["modalities"]["log_time_series"], "USED")
        self.assertEqual(audit["modalities"]["trace_error_time_series"], "LOADED_NOT_USED")
        self.assertFalse(audit["tri_modal_claim_permitted"])

    def test_16_raw_exception_interception(self):
        def failing(*args, **kwargs):
            raise KeyError("unseen operation")

        result = raw_call(failing, object())
        self.assertEqual(result["execution_status"], "F-A_ALGORITHMIC_FAILURE")
        self.assertEqual(result["exception_type"], "KeyError")

    def test_17_no_dummy_fallback_accepted(self):
        def successful(*args, **kwargs):
            return {"ranks": ["svc_cpu"]}

        result = raw_call(successful, object())
        self.assertEqual(result["execution_status"], "SUCCESS")
        self.assertFalse(result["dummy_fallback_accepted"])

    def test_18_deterministic_repeat_smoke_output(self):
        for method in ("baro", "tracerca"):
            for filename in ("ob_smoke.jsonl", "tt_smoke.jsonl"):
                rows = [
                    json.loads(line)
                    for line in (ARTIFACT_ROOT / method / filename).read_text().splitlines()
                ]
                self.assertEqual(len(rows), 6)
                self.assertTrue(summarize_repeat_records(rows)["deterministic_repeats"])


if __name__ == "__main__":
    unittest.main()
