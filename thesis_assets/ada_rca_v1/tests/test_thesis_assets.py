#!/usr/bin/env python3
"""Smoke tests for the generated Ada-RCA V1 thesis asset package."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
PACKAGE = REPO / "thesis_assets/ada_rca_v1"
VALIDATOR = PACKAGE / "scripts/validate_thesis_assets.py"


class ThesisAssetPackageTest(unittest.TestCase):
    def test_package_entrypoints_exist(self) -> None:
        self.assertTrue((PACKAGE / "README.md").is_file())
        self.assertTrue((PACKAGE / "MANIFEST.csv").is_file())
        self.assertTrue((PACKAGE / "PROVENANCE.json").is_file())
        self.assertTrue(VALIDATOR.is_file())

    def test_fail_closed_validator_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--repo-root", str(REPO), "--json"],
            cwd=REPO,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "THESIS_ASSET_PACKAGE_READY_WITH_LIMITATION")
        self.assertEqual(report["failure_count"], 0)


if __name__ == "__main__":
    unittest.main()
