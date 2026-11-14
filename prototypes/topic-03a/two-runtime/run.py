"""Run the two-runtime integration against a pinned Multica checkout and disposable migrated database."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


REVISION = "fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc"
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="Multica checkout")
    parser.add_argument("orders", type=Path, help="output directory from order-export/run.py")
    parser.add_argument("--go", default="go", help="Go executable")
    parser.add_argument("--receiver", type=Path,
                        default=HERE.parent / "machine-handoff" / "identity_read.py",
                        help="independent Python receiver")
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    revision = subprocess.check_output(["git", "-C", checkout, "rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION:
        parser.error(f"require checkout at {REVISION}")
    if not os.environ.get("DATABASE_URL"):
        parser.error("set DATABASE_URL to a disposable migrated Multica database")
    orders = args.orders.resolve()
    fixture = {
        "AP_C1_REPORT": orders / "C1" / "report.json",
        "AP_C2_REPORT": orders / "C2" / "report.json",
        "AP_ORDER_WORKBOOK": orders / "C2" / "east.xlsx",
        "AP5_RECEIVER_SCRIPT": args.receiver.resolve(),
    }
    for path in fixture.values():
        if not path.is_file():
            parser.error(f"missing {path}")
    # Each run compiles the daemon production package plus our integration test.
    # Removing other upstream test units from the overlay avoids bootstrapping
    # unrelated suites. No production source files are substituted.
    base = checkout / "server"
    package = base / "internal" / "daemon"
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        mapping = {str(package / "ap5_two_runtime_test.go"): str(HERE / "handoff_test.go")}
        for upstream_test in package.glob("*_test.go"):
            name = re.search(r"^package (\w+)", upstream_test.read_text(), re.MULTILINE).group(1)
            stub = scratch / f"empty-{name}.go"
            if not stub.exists():
                stub.write_text(f"package {name}\n")
            mapping[str(upstream_test)] = str(stub)
        overlay = scratch / "overlay.json"
        overlay.write_text(json.dumps({"Replace": mapping}))
        binary = scratch / "two-runtime.test"
        env = {**os.environ, **{name: str(path) for name, path in fixture.items()}}
        subprocess.run([args.go, "test", "-c", "-p=1", "-vet=off", "-ldflags=-s -w",
                        "-gcflags=github.com/multica-ai/multica/server/internal/daemon=-c=1 -l",
                        "-o", str(binary), "-overlay", str(overlay), "./internal/daemon"],
                       env=env, cwd=base, check=True)
        subprocess.run([str(binary), "-test.run", "^TestTwoRuntimeOrderHandoff$", "-test.v",
                        "-test.timeout=11m"], cwd=base, env=env, check=True)


if __name__ == "__main__":
    main()
