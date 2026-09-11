#!/usr/bin/env python3
"""Run one frozen Z1-logistic outer fold."""

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.supervised_baselines.common import run_fold
from src.rca.supervised_baselines.logistic import LOGISTIC_CONFIG, fit_score_and_save


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=("re2ob", "re2tt"))
    parser.add_argument("--fold", required=True, type=int, choices=(0, 1, 2))
    parser.add_argument("--output-root", default="artifacts/supervised_baselines")
    args = parser.parse_args()
    result = run_fold(
        PROJECT_ROOT,
        args.dataset,
        args.fold,
        "logistic",
        PROJECT_ROOT / args.output_root,
        LOGISTIC_CONFIG,
        fit_score_and_save,
        {},
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
