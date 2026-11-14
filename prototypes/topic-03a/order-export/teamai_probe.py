"""Re-run the two real verification reports through TeamAI's native command driver."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from run import HERE, git


PIN = "556b5246f2c13ad28b8b79b5b513a78ed8ab9dae"


def probe(checkout, source):
    if git(checkout, "rev-parse", "HEAD") != PIN:
        raise ValueError(f"expected TeamAI revision {PIN}")
    with TemporaryDirectory(prefix="export-teamai-") as temp:
        root = Path(temp)
        home = root / "member"
        home.mkdir()
        app = root / "app"
        app.mkdir()
        git(app, "init", "-q", "-b", "main")
        (app / "README.md").write_text("# Export validation workspace\n")
        git(app, "add", "README.md")
        git(app, "commit", "-qm", "Prepare verification")
        # The native CLI needs a repository identity even for a local-only command run.
        git(app, "remote", "add", "origin", "http://127.0.0.1:9/team/export.git")
        env = {"PATH": os.environ["PATH"], "HOME": str(home), "FORCE_COLOR": "0",
               "GIT_AUTHOR_NAME": "Export fixture", "GIT_AUTHOR_EMAIL": "fixture@example.test",
               "GIT_COMMITTER_NAME": "Export fixture", "GIT_COMMITTER_EMAIL": "fixture@example.test"}

        def cli(*args):
            result = subprocess.run(["node", checkout / "dist/index.js", *args], cwd=app,
                                    env=env, text=True, capture_output=True, timeout=60)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout

        cli("init", "--self", "--agent", "claude", "--force")
        config = app / ".teamai/workflows"
        config.mkdir(parents=True, exist_ok=True)
        steps = ["schemaVersion: v1alpha1", "name: verify-orders", "description: Verify two candidate workbooks.", "steps:"]
        for candidate in ("C1", "C2"):
            evidence = root / candidate
            shutil.copytree(source / candidate, evidence)
            (evidence / "report.json").unlink()
            command = shlex.join([sys.executable, str(HERE / "verify.py"), str(evidence)])
            # Publish the verdict in stdout as the driver's declared output. Keep detailed evidence in the named report.
            read_verdict = "import json,sys; print(json.dumps({'verdict':json.load(open(sys.argv[1]))['verdict']}))"
            command += " && " + shlex.join([sys.executable, "-c", read_verdict, str(evidence / "report.json")])
            step = candidate.lower()
            steps.extend(["  - id: " + step, "    needs: []", "    command: " + json.dumps(command),
                          "    output: { verdict: string }"])
        for step, verdict in (("c1", "rework"), ("c2", "pass")):
            marker = root / (step + "-route")
            command = shlex.join([sys.executable, "-c", "import pathlib,sys; pathlib.Path(sys.argv[1]).touch()", str(marker)])
            steps.extend(["  - id: route-" + step, "    needs: [" + step + "]",
                          f"    if: steps.{step}.outputs.verdict == '{verdict}'", "    command: " + json.dumps(command)])
        (config / "verify-orders.yaml").write_text("\n".join(steps) + "\n")
        cli("pull")
        output = cli("workflow", "start", "verify-orders", "--driver", "local")
        result = json.loads(next(line for line in reversed(output.strip().splitlines()) if line.startswith("{")))
        assert result["data"]["done"]["outcome"] == "succeeded", result
        for candidate in ("C1", "C2"):
            actual = (root / candidate / "report.json").read_bytes()
            assert actual == (source / candidate / "report.json").read_bytes()
            assert (root / (candidate.lower() + "-route")).is_file()
            print(candidate, json.loads(actual)["verdict"], hashlib.sha256(actual).hexdigest())
        print("TeamAI workflow outcome:", result["data"]["done"]["outcome"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="built TeamAI checkout at the pinned commit")
    parser.add_argument("reports", type=Path, help="output directory from run.py")
    args = parser.parse_args()
    probe(args.checkout.resolve(), args.reports.resolve())
