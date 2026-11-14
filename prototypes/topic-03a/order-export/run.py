"""Prepare C1/C2 Git worktrees, execute a versioned verifier, and retain its evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from verify import write_json


HERE = Path(__file__).resolve().parent
ORDERS = [
    {"id": "A-101", "region": "east", "status": "paid", "cents": 12835,
     "created": "2026-11-14T14:00:00+00:00", "paid": "2026-11-14T16:15:00+00:00"},
    {"id": "A-102", "region": "east", "status": "unpaid", "cents": 0,
     "created": "2026-11-14T15:00:00+00:00", "paid": None},
    {"id": "B-201", "region": "west", "status": "paid", "cents": 608,
     "created": "2026-11-14T16:00:00+00:00", "paid": "2026-11-14T17:30:00+00:00"},
]
SCOPE_C1 = {"east": ["east", "west"], "west": ["west"], "cross": ["east", "west"]}
SCOPE_C2 = {**SCOPE_C1, "east": ["east"]}


def git(directory, *args):
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}
    proc = subprocess.run(["git", "-c", "user.name=Export fixture", "-c", "user.email=fixture@example.test",
                           "-c", "core.autocrlf=false", *args], cwd=directory, env=env,
                          capture_output=True, text=True, check=True)
    return proc.stdout.strip()


def run(directory, *args):
    return subprocess.run([sys.executable, *args], cwd=directory, capture_output=True,
                          text=True, timeout=30, check=False)


def exercise(checkout, out, candidate, number):
    out.mkdir()
    binding = {"issue": "order-export-verification", "run": f"verify-{candidate}",
               "node": "verify-order-export", "attempt": number, "candidate": candidate,
               "rule": "D2", "commit": git(checkout, "rev-parse", "HEAD")}
    write_json(out / "binding.json", binding)
    exits = {}
    for role in ("east", "west", "cross", "viewer"):
        proc = run(checkout, "exporter.py", role, str(out / f"{role}.xlsx"))
        exits[role] = proc.returncode
        if proc.returncode not in (0, 3):
            raise RuntimeError(proc.stderr)
    write_json(out / "export-exits.json", exits)
    # The verifier is a versioned, out-of-worktree script shared by both candidates.
    checked = run(checkout, HERE / "verify.py", out)
    if checked.returncode:
        raise RuntimeError(checked.stderr)
    report = json.loads((out / "report.json").read_text())
    assert report["A2"] == (candidate == "C2") and report["A3"]
    assert report["verdict"] == ("rework" if candidate == "C1" else "pass")
    assert not git(checkout, "status", "--porcelain")
    return {"verify_exit": checked.returncode, "report_sha256": hashlib.sha256((out / "report.json").read_bytes()).hexdigest(),
            "verdict": report["verdict"], "commit": binding["commit"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for worktrees, workbooks and reports")
    args = parser.parse_args()
    target = args.output.resolve()
    target.mkdir(parents=True)
    source = target / "source"
    source.mkdir()
    git(source, "init", "-q", "--object-format=sha1", "-b", "main")
    shutil.copyfile(HERE / "exporter.py", source / "exporter.py")
    write_json(source / "orders.json", ORDERS)
    write_json(source / "scope.json", SCOPE_C1)
    git(source, "add", ".")
    git(source, "commit", "-qm", "C1: export fixture")
    first = git(source, "rev-parse", "HEAD")
    git(source, "worktree", "add", "-q", "--detach", str(target / "worktree-C1"), first)
    write_json(source / "scope.json", SCOPE_C2)
    git(source, "add", "scope.json")
    git(source, "commit", "-qm", "C2: correct eastern role scope")
    second = git(source, "rev-parse", "HEAD")
    git(source, "worktree", "add", "-q", "--detach", str(target / "worktree-C2"), second)
    assert git(source, "rev-parse", "HEAD^") == first
    summary = {}
    for number, candidate in enumerate(("C1", "C2"), start=1):
        summary[candidate] = exercise(target / f"worktree-{candidate}", target / candidate, candidate, number)

    # Read fresh copies for each negative control so neither accepted workbook nor report is altered.
    from openpyxl import load_workbook
    with TemporaryDirectory() as temporary:
        for case in ("malformed", "missing-column", "wrong-amount", "wrong-zone", "unpaid-filled"):
            directory = Path(temporary) / case
            shutil.copytree(target / "C2", directory)
            (directory / "report.json").unlink()
            path = directory / "east.xlsx"
            if case == "malformed":
                path.write_bytes(b"fixture: truncated workbook")
            else:
                book = load_workbook(path)
                sheet = book["Orders"]
                if case == "missing-column":
                    sheet.delete_cols(5)
                elif case == "wrong-amount":
                    sheet["D2"] = 128.34
                elif case == "wrong-zone":
                    sheet["E2"] = sheet["E2"].value.replace(day=14, hour=16)
                else:
                    sheet["E3"] = sheet["E2"].value
                book.save(path)
                book.close()
            check = run(target / "worktree-C2", HERE / "verify.py", directory)
            assert check.returncode == 0, check.stderr
            finding = json.loads((directory / "report.json").read_text())
            assert not finding["A3"] and finding["verdict"] == "rework"
            summary[case] = {"verify_exit": check.returncode, "A3": finding["A3"], "verdict": finding["verdict"]}
        absent = Path(temporary) / "missing-input"
        absent.mkdir()
        failure = run(target / "worktree-C2", HERE / "verify.py", absent)
        assert failure.returncode != 0 and not (absent / "report.json").exists()
        summary["missing-input"] = {"verify_exit": failure.returncode, "report_present": False}
    write_json(target / "summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
