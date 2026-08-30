"""Preloaded method server that forks exactly one isolated case worker at a time."""

from __future__ import annotations

import argparse
import json
import multiprocessing
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

from src.baseline_eval.confirmatory import CASE_TIMEOUT_SECONDS, METHOD_ORDER, atomic_write_json
from src.baseline_eval.worker import _module_callable, execute_case


def _child(request: Mapping[str, Any]) -> None:
    namespace = argparse.Namespace(**request)
    output = Path(namespace.output)
    if output.exists():
        raise RuntimeError("case child refuses to overwrite a terminal record")
    atomic_write_json(output, execute_case(namespace))


def serve(method: str) -> int:
    # Preload the exact selected method once.  Every actual invocation still
    # runs in a fresh forked subprocess and reseeds all controlled RNGs.
    _module_callable(method)
    context = multiprocessing.get_context("fork")
    print(json.dumps({"status": "READY", "method": method}), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        if request.get("command") == "stop":
            print(json.dumps({"status": "STOPPED"}), flush=True)
            return 0
        if request.get("method") != method:
            print(json.dumps({"status": "FRAMEWORK_ERROR", "case_id": request.get("case_id")}), flush=True)
            return 2
        process = context.Process(target=_child, args=(request,))
        process.start()
        process.join(CASE_TIMEOUT_SECONDS)
        if process.is_alive():
            process.terminate()
            process.join(10)
            if process.is_alive():
                process.kill()
                process.join(10)
            print(json.dumps({"status": "TIMEOUT", "case_id": request["case_id"]}), flush=True)
            continue
        if process.exitcode != 0 or not Path(request["output"]).is_file():
            print(json.dumps({"status": "FRAMEWORK_ERROR", "case_id": request["case_id"]}), flush=True)
            return 3
        print(json.dumps({"status": "RECORDED", "case_id": request["case_id"]}), flush=True)
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--method", choices=METHOD_ORDER, required=True)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return serve(args.method)


if __name__ == "__main__":
    raise SystemExit(main())
