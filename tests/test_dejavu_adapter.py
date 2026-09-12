import csv
from pathlib import Path
import tempfile
import unittest


from src.rca.supervised_baselines.dejavu_adapter import (
    audit_case_source,
    audit_source_registry,
    build_graph_spec,
    prepare_metric_tensor,
)


class DejaVuSourceAuditTest(unittest.TestCase):
    def _write_case(self, root):
        metrics_path = root / "simple_metrics.csv"
        traces_path = root / "traces.csv"
        inject_path = root / "inject_time.txt"
        inject_path.write_text("1000\n", encoding="utf-8")

        with metrics_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["time", "frontend_cpu", "worker_cpu", "idle_cpu",
                 "frontend_mem", "worker_mem", "idle_mem"]
            )
            for offset in range(-600, 541, 60):
                writer.writerow([1000 + offset, 1, 2, 3, 4, 5, 6])

        with traces_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["time", "traceID", "spanID", "serviceName", "methodName",
                 "operationName", "startTimeMillis", "startTime", "duration",
                 "statusCode", "parentSpanID"]
            )
            writer.writerow([900, "t1", "p1", "frontendservice", "", "", "", "", 1, 200, ""])
            writer.writerow([901, "t1", "c1", "worker", "", "", "", "", 1, 200, "p1"])
            writer.writerow([902, "t2", "x1", "external", "", "", "", "", 1, 200, ""])
        return metrics_path, traces_path, inject_path

    def test_case_audit_binds_sources_and_builds_only_parent_child_edges(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics_path, traces_path, inject_path = self._write_case(root)

            result = audit_case_source(
                {
                    "case_id": "case-1",
                    "simple_metrics_path": str(metrics_path),
                    "traces_path": str(traces_path),
                    "inject_time_path": str(inject_path),
                },
                ("frontend", "idle", "worker"),
                "re2ob",
            )

            self.assertEqual(result["case_id"], "case-1")
            self.assertEqual(result["edges"], [["frontend", "worker"]])
            self.assertEqual(result["edge_node_coverage"], ["frontend", "worker"])
            self.assertEqual(result["isolated_candidates"], ["idle"])
            self.assertEqual(result["unmapped_trace_services"], ["external"])
            self.assertEqual(result["required_metric_samples"], 20 * 3 * 2)
            self.assertEqual(result["missing_required_metric_samples"], 0)
            self.assertEqual(len(result["files"]["traces"]["sha256"]), 64)
            self.assertEqual(len(result["files"]["simple_metrics"]["sha256"]), 64)

    def test_registry_audit_is_complete_and_label_blind(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics_path, traces_path, inject_path = self._write_case(root)
            sources_path = root / "sources.jsonl"
            candidates_path = root / "service_registry.json"
            sources_path.write_text(
                '{"case_id":"case-1","simple_metrics_path":"%s",'
                '"traces_path":"%s","inject_time_path":"%s"}\n'
                % (metrics_path, traces_path, inject_path),
                encoding="utf-8",
            )
            candidates_path.write_text(
                '{"services":["frontend","idle","worker"]}\n',
                encoding="utf-8",
            )

            result = audit_source_registry(
                sources_path,
                candidates_path,
                "re2ob",
                expected_cases=1,
                workers=1,
            )

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["case_count"], 1)
            self.assertEqual(result["trace_file_count"], 1)
            self.assertEqual(result["metric_file_count"], 1)
            self.assertEqual(result["union_edges"], [["frontend", "worker"]])
            self.assertEqual(result["candidates_never_in_an_edge"], ["idle"])
            self.assertNotIn("root_service", str(result))
            self.assertNotIn("fault_type", str(result))

    def test_official_forward_fill_and_identical_duplicate_spans_are_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics_path, traces_path, inject_path = self._write_case(root)
            with metrics_path.open(encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            rows[12][2] = ""
            with metrics_path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(rows)
            with traces_path.open("a", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(
                    [903, "t1", "p1", "frontendservice", "", "", "", "", 1, 200, ""]
                )

            result = audit_case_source(
                {
                    "case_id": "case-1",
                    "simple_metrics_path": str(metrics_path),
                    "traces_path": str(traces_path),
                    "inject_time_path": str(inject_path),
                },
                ("frontend", "idle", "worker"),
                "re2ob",
            )

            self.assertEqual(result["missing_required_metric_samples"], 1)
            self.assertEqual(result["forward_fillable_metric_samples"], 1)
            self.assertEqual(result["unfillable_metric_samples"], 0)
            self.assertEqual(result["duplicate_span_key_count"], 1)
            self.assertEqual(result["ambiguous_span_key_count"], 0)

    def test_metric_tensor_and_graph_spec_follow_frozen_adapter_semantics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metrics_path, _, inject_path = self._write_case(root)
            with metrics_path.open(encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            rows[12][2] = ""
            with metrics_path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerows(rows)

            tensor = prepare_metric_tensor(
                {
                    "simple_metrics_path": str(metrics_path),
                    "inject_time_path": str(inject_path),
                },
                ("frontend", "idle", "worker"),
            )
            graph = build_graph_spec(
                ("frontend", "idle", "worker"),
                (("frontend", "worker"),),
            )

            self.assertEqual(tensor.shape, (3, 2, 20))
            self.assertEqual(str(tensor.dtype), "float32")
            self.assertAlmostEqual(float(tensor[:, :, :10].mean()), 0.0, places=6)
            self.assertAlmostEqual(float(tensor[1, 0, 11]), 0.0, places=6)
            self.assertEqual(
                graph,
                {
                    "node_count": 3,
                    "source_indices": [0],
                    "destination_indices": [2],
                },
            )


if __name__ == "__main__":
    unittest.main()
