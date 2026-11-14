"""Compile the fixed Multica checkout's context writer using a Go overlay."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

REVISION = "fdfbfcd5e5d30c135255e63ab9af4c52672b7bbc"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="Multica checkout at the research revision")
    parser.add_argument("binary", type=Path, help="output executable for the host probes")
    parser.add_argument("--go", default="go", help="Go 1.26.9 executable")
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    head = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if head != REVISION:
        parser.error(f"Multica revision {head}; expected {REVISION}")
    server = checkout / "server"
    package = Path("cmd/agentplatform_context_probe")
    source = Path(__file__).with_name("materialize.go").resolve()
    with tempfile.TemporaryDirectory(prefix="multica-context-build-") as temp:
        overlay = Path(temp) / "overlay.json"
        overlay.write_text(json.dumps({"Replace": {str(server / package / "main.go"): str(source)}}))
        subprocess.run([args.go, "build", "-p", "1", "-overlay", str(overlay),
                        "-o", str(args.binary.resolve()), "./" + str(package)], cwd=server, check=True)


if __name__ == "__main__":
    main()
