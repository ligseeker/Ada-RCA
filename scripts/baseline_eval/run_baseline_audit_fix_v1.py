#!/usr/bin/env python3
"""Generate the post-lock baseline audit evidence exactly once.

The generator only reads already locked records after the existing provenance
gates pass.  It never invokes a baseline method, including CausalRCA.
"""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.baseline_eval.audit_fix_v1 import generate_audit  # noqa: E402


def main() -> None:
    payload = generate_audit(PROJECT_ROOT)
    print(
        {
            "audit_root": payload["audit_root"],
            "report_path": payload["report_path"],
            "method_dataset_rows": len(payload["dual_result_rows"]),
            "protocol_difference_cases": len(payload["protocol_difference_rows"]),
            "causalrca_runs_executed_by_codex": payload["provenance"][
                "causalrca_runs_executed_by_codex"
            ],
        }
    )


if __name__ == "__main__":
    main()
