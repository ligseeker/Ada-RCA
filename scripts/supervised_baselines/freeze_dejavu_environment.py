#!/usr/bin/env python3
"""Validate and freeze the isolated DejaVu adapter runtime environment."""

import argparse
import importlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rca.supervised_baselines.common import sha256_file, write_json


OFFICIAL_COMMIT = "d1f082b086cef5597f5301a7b02882b5d0238ebe"
EXPECTED = {
    "dgl": "0.8.2",
    "networkx": "2.6.3",
    "numpy": "1.21.6",
    "pandas": "1.4.4",
    "pytorch_lightning": "1.6.5",
    "scipy": "1.6.3",
    "sklearn": "1.0.2",
    "torch": "1.12.0",
    "torchmetrics": "0.9.3",
}


def _command(*args, cwd=None):
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dejavu-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/supervised_baselines/dejavu/environment/environment.json"),
    )
    args = parser.parse_args()
    upstream = args.dejavu_root.resolve()
    if _command("git", "rev-parse", "HEAD", cwd=upstream) != OFFICIAL_COMMIT:
        raise ValueError("DejaVu checkout commit mismatch")
    if _command("git", "status", "--porcelain", cwd=upstream):
        raise ValueError("DejaVu checkout must be clean")

    os.environ["DGLBACKEND"] = "pytorch"
    sys.path.insert(0, str(upstream))
    versions = {}
    for name, expected in EXPECTED.items():
        module = importlib.import_module(name)
        actual = str(getattr(module, "__version__"))
        if actual != expected:
            raise ValueError("{} version {} != {}".format(name, actual, expected))
        versions[name] = actual
    from DejaVu.models.GAT import GAT  # noqa: F401
    import dgl
    import torch

    graph = dgl.heterograph(
        {("service", "service-calls-service", "service"): (
            torch.tensor([0]), torch.tensor([1])
        )},
        num_nodes_dict={"service": 3},
    )
    if graph.num_nodes("service") != 3 or graph.num_edges() != 1:
        raise ValueError("explicit candidate node preservation smoke failed")

    requirements = PROJECT_ROOT / "envs" / "dejavu-adapter-requirements.txt"
    result = {
        "schema_version": "dejavu_environment_v1",
        "status": "PASS",
        "python": platform.python_version(),
        "python_executable": str(Path(sys.executable).absolute()),
        "python_executable_target": str(Path(sys.executable).resolve()),
        "platform": platform.platform(),
        "official_checkout": str(upstream),
        "official_commit": OFFICIAL_COMMIT,
        "official_checkout_clean": True,
        "requirements_path": str(requirements.relative_to(PROJECT_ROOT)),
        "requirements_sha256": sha256_file(requirements),
        "versions": versions,
        "pip_check": _command(sys.executable, "-m", "pip", "check"),
        "pip_freeze": _command(sys.executable, "-m", "pip", "freeze").splitlines(),
        "import_smoke": "PASS",
        "isolated_node_graph_smoke": {
            "status": "PASS",
            "nodes": graph.num_nodes("service"),
            "edges": graph.num_edges(),
        },
    }
    output = args.output if args.output.is_absolute() else PROJECT_ROOT / args.output
    write_json(output, result)
    print(json.dumps({
        "status": result["status"],
        "official_commit": OFFICIAL_COMMIT,
        "output": str(output),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
