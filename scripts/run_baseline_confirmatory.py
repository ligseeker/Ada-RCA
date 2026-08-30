#!/usr/bin/env python3
"""CLI entry point for the frozen RCAEval confirmatory execution."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.baseline_eval.confirmatory import main


if __name__ == "__main__":
    raise SystemExit(main())
