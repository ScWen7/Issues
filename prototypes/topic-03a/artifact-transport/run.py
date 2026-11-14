"""Send the C2 fixture workbook through a pinned upstream's real artifact path."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

UPSTREAM = {
    "loopforge": ("97b3cdc2f29a88e8767a8dc6c03bfb8865622653", ".", "internal/runner", "TestOrderWorkbookRunnerTransport"),
    "multica": ("fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc", "server", "phase4artifactprobe", "TestOrderWorkbookIssueAttachment"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", choices=UPSTREAM)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--go", default="go")
    args = parser.parse_args()
    revision, module, package, name = UPSTREAM[args.upstream]
    root = args.checkout.resolve()
    if subprocess.check_output(["git", "-C", root, "rev-parse", "HEAD"], text=True).strip() != revision:
        parser.error(f"{args.upstream} checkout must be at {revision}")
    if not args.workbook.is_file():
        parser.error("pass the C2 east.xlsx produced by order-export/run.py")
    if args.upstream == "multica" and not os.environ.get("DATABASE_URL"):
        parser.error("set DATABASE_URL to a disposable migrated Multica database")
    base = root / module
    suite = base / package
    source = Path(__file__).resolve().parent / args.upstream / "workbook_test.go"
    with tempfile.TemporaryDirectory() as scratch:
        temp = Path(scratch)
        mapping = {str(suite / "phase4artifact_test.go"): str(source)}
        # Compile the real runner with this single transport test. The upstream
        # package's other tests also import a large unrelated HTTP API suite.
        if args.upstream == "loopforge":
            for existing in suite.glob("*_test.go"):
                pkg = re.search(r"^package (\w+)", existing.read_text(), re.MULTILINE).group(1)
                stub = temp / (pkg + ".go")
                stub.write_text("package " + pkg + "\n")
                mapping[str(existing)] = str(stub)
        overlay = temp / "overlay.json"
        overlay.write_text(json.dumps({"Replace": mapping}))
        env = {**os.environ, "AP_ORDER_WORKBOOK": str(args.workbook.resolve())}
        binary = temp / "artifact.test"
        subprocess.run([args.go, "test", "-c", "-p=1", "-vet=off", "-ldflags=-s -w",
                        "-o", str(binary), "-overlay", str(overlay), "./" + package],
                       cwd=base, env=env, check=True)
        subprocess.run([str(binary), "-test.v", "-test.run", "^" + name + "$"],
                       cwd=base, env=env, check=True)


if __name__ == "__main__":
    main()
