#!/usr/bin/env python3
"""CLI entry point for the V2 five-baseline rescue coordinator."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.baseline_eval.rescue_v2 import main


if __name__ == "__main__":
    raise SystemExit(main())
