#!/usr/bin/env python3
"""Run one frozen Trajectory-TCN outer fold or the designated smoke run."""

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.supervised_baselines.common import run_fold
from src.rca.supervised_baselines.tcn import TCN_CONFIG, fit_score_and_save


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, choices=("re2ob", "re2tt"))
    parser.add_argument("--fold", required=True, type=int, choices=(0, 1, 2))
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-root", default="artifacts/supervised_baselines")
    args = parser.parse_args()
    if args.smoke and (args.dataset != "re2ob" or args.fold != 0):
        raise ValueError("the frozen smoke target is re2ob fold 0")
    import torch

    method = "tcn_smoke" if args.smoke else "tcn"
    config = dict(TCN_CONFIG)
    config["run_role"] = "SMOKE_NOT_FORMAL" if args.smoke else "FORMAL_OOF_FOLD"
    result = run_fold(
        PROJECT_ROOT,
        args.dataset,
        args.fold,
        method,
        PROJECT_ROOT / args.output_root,
        config,
        fit_score_and_save,
        {"torch": torch.__version__, "cuda_available": torch.cuda.is_available()},
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
