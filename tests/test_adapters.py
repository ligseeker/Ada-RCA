from pathlib import Path
import tempfile
import unittest

from src.rca.rcaeval import RE2OB, RE2TT, load_cases, opaque_case_id


class AdapterTest(unittest.TestCase):
    def make_case(self, root: Path, condition: str):
        case = root / condition / "1"
        case.mkdir(parents=True)
        for name in ("metrics.csv", "logs.csv", "traces.csv"):
            (case / name).write_text("time,value\n1,0\n", encoding="utf-8")
        (case / "simple_metrics.csv").write_text(
            "time,ts-auth-service_cpu,ts-auth-service_mem,ts-auth-mongo_cpu,istio-init_cpu\n1,0,0,0,0\n",
            encoding="utf-8",
        )
        for name in ("logts.csv", "tracets_err.csv", "tracets_lat.csv"):
            (case / name).write_text("time,ts-auth-service_x\n1,0\n", encoding="utf-8")
        (case / "inject_time.txt").write_text("1700000000", encoding="utf-8")

    def test_opaque_namespaces_do_not_collide(self):
        relative = "same_cpu/1"
        self.assertNotEqual(opaque_case_id(RE2OB, relative), opaque_case_id(RE2TT, relative))

    def test_hyphenated_tt_root_and_label_free_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_case(root, "ts-auth-service_cpu")
            result = load_cases(RE2TT, str(root))
            self.assertEqual(len(result.inputs), 1)
            self.assertEqual(result.inputs[0].services, ("ts-auth-mongo", "ts-auth-service"))
            self.assertEqual(result.labels[0].root_service, "ts-auth-service")
            self.assertNotIn("ts-auth-service_cpu", result.inputs[0].case_id)
            self.assertNotIn("root", result.inputs[0].metadata)


if __name__ == "__main__":
    unittest.main()
