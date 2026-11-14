"""Publish or receive the C2 order fixture on two runners with independent disks."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import uuid
import zipfile


ROOT = Path(__file__).resolve().parents[3]
EXPECTED = ROOT / "docs/research/topic-03a/fixtures/order-export-c2.json"


def host_signature(challenge):
    # Only a run-scoped digest leaves this machine. Never include native IDs.
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    return hashlib.sha256((challenge + ":" + boot).encode()).hexdigest()


def git(*args, cwd):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def publish(target):
    challenge = uuid.uuid4().hex
    work = target.parent / ("sender-" + challenge)
    subprocess.run([sys.executable, str(ROOT / "prototypes/topic-03a/order-export/run.py"), str(work)], check=True)
    expected = json.loads(EXPECTED.read_bytes())
    if (work / "C2/report.json").read_bytes() != EXPECTED.read_bytes():
        raise ValueError("C2 report differs from the committed fixture")
    target.mkdir()
    git("bundle", "create", str(target / "candidate.bundle"), "refs/heads/main", cwd=work / "source")
    shutil.copyfile(work / "C2/east.xlsx", target / "east.xlsx")
    shutil.copyfile(work / "C2/report.json", target / "report.json")
    (work / "only-on-sender").write_text(challenge)
    (target / "sender.json").write_text(json.dumps({"challenge": challenge, "sender": host_signature(challenge)}))
    print("published", expected["commit"], "with the verified east workbook")


def receive(target, require_distinct_boot):
    receipt = json.loads((target / "sender.json").read_text())
    same_boot = receipt["sender"] == host_signature(receipt["challenge"])
    if require_distinct_boot and same_boot:
        raise ValueError("sender and receiver report the same kernel boot")
    allowed = {"candidate.bundle", "east.xlsx", "report.json", "sender.json"}
    if {p.name for p in target.iterdir()} != allowed:
        raise ValueError("delivered files differ from the handoff manifest")
    report = json.loads(EXPECTED.read_bytes())
    if (target / "report.json").read_bytes() != EXPECTED.read_bytes():
        raise ValueError("report differs from the independently checked-out baseline")
    clone = target.parent / ("receiver-" + uuid.uuid4().hex)
    git("clone", "--quiet", "--no-checkout", str(target / "candidate.bundle"), str(clone), cwd=target)
    git("checkout", "--quiet", "--detach", report["commit"], cwd=clone)
    if git("rev-parse", "HEAD", cwd=clone) != report["commit"]:
        raise ValueError("candidate commit mismatch")
    binary = (target / "east.xlsx").read_bytes()
    spec = next(x for x in report["artifacts"] if x["name"] == "east.xlsx")
    if len(binary) != spec["bytes"] or hashlib.sha256(binary).hexdigest() != spec["sha256"]:
        raise ValueError("workbook bytes differ from the verified C2 file")
    with zipfile.ZipFile(target / "east.xlsx") as book:
        if book.testzip() or "xl/workbook.xml" not in book.namelist():
            raise ValueError("invalid workbook")
    print(json.dumps({"kernel_boots_differ": not same_boot, "system": platform.system(),
                      "commit": report["commit"], "bytes": len(binary), "sha256": spec["sha256"],
                      "report": report["verdict"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=["publish", "receive"])
    parser.add_argument("handoff", type=Path)
    parser.add_argument("--require-distinct-boot", action="store_true")
    args = parser.parse_args()
    if args.role == "publish":
        publish(args.handoff.resolve())
    else:
        receive(args.handoff.resolve(), args.require_distinct_boot)
