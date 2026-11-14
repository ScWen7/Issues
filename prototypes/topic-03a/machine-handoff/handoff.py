"""Rehearse A loss, B takeover and A recovery using the real order-export fixture."""
import argparse
from contextlib import closing
from hashlib import sha256
import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import signal
import socket
import shutil
import subprocess
import sys
from tempfile import NamedTemporaryFile
import time
from zipfile import ZipFile

from identity_read import namespaces


def fingerprint():
    return {**namespaces(), "boot": sha256(Path("/proc/sys/kernel/random/boot_id").read_bytes()).hexdigest(),
            "host": sha256(socket.gethostname().encode()).hexdigest()}


def git(*arguments, cwd=None):
    return subprocess.run(["git", *map(str, arguments)], cwd=cwd, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()


def write(path, payload):
    # A waiting reader can open the final name as soon as it exists.
    with NamedTemporaryFile(dir=path.parent) as staged:
        staged.write(payload)
        staged.flush()
        os.fsync(staged.fileno())
        os.link(staged.name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def initialize(state, order):
    state.mkdir(mode=0o700)
    for name in ("A", "B", "center", "publication", "submitted-A", "submitted-B", "evidence"):
        (state / name).mkdir(mode=0o700)
    for candidate in ("C1", "C2"):
        raw = (order / candidate / "report.json").read_bytes()
        (state / "center" / (candidate + ".json")).write_bytes(raw)
    (state / "A" / "unsent.json").write_bytes((order / "C1" / "report.json").read_bytes())
    center = state / "center"
    publication = state / "publication"
    shutil.copyfile(center / "C2.json", publication / "C2.json")
    # The produced bundle is an immutable transfer artifact. The receiver's Git
    # database is initialized exclusively from the published bundle.
    commit = json.loads((center / "C2.json").read_bytes())["commit"]
    git("clone", "-q", "--no-local", order / "source", center / "staging")
    git("branch", "checkpoint", commit, cwd=center / "staging")
    git("bundle", "create", publication / "code.bundle", "checkpoint", cwd=center / "staging")
    for item in json.loads((center / "C2.json").read_bytes())["artifacts"]:
        (publication / item["name"]).write_bytes((order / "C2" / item["name"]).read_bytes())


def phase4_module(path):
    spec = importlib.util.spec_from_file_location("admission", path)
    if not spec or not spec.loader:
        raise RuntimeError("missing result admission module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def await_file(path, timeout=120):
    deadline = time.monotonic() + timeout
    while not path.is_file():
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for {path.name}")
        time.sleep(0.1)


def reconcile(state, upstream, distinct, coordinated):
    database = state / "center" / "results.sqlite"
    admission = phase4_module(upstream)
    with closing(admission.connect(database)) as db, db:
        db.executescript(admission.SCHEMA)
        for attempt, candidate in enumerate(("C1", "C2"), 1):
            record = json.loads((state / "center" / (candidate + ".json")).read_bytes())
            run = "verify-" + candidate
            db.execute("INSERT INTO dispatch VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (run, admission.ISSUE, admission.NODE, attempt, candidate, "D2",
                        admission.COMMITS[attempt - 1], "A" if candidate == "C1" else "B",
                        1, 1, 1, 3, admission.VERIFIER))
            for name in admission.FILES:
                db.execute("INSERT INTO required_artifact VALUES(?,?)", (run, name))
                if candidate == "C2":
                    admission.supply_file(db, run, name, state / "publication" / name)
            assert record["commit"] == admission.COMMITS[attempt - 1]
        db.execute("INSERT INTO delegation VALUES(?,?,?,?,?)", (admission.ISSUE, admission.NODE, 3, 1, "submit-report"))
        db.execute("INSERT INTO current_node VALUES(?,?,?)", (admission.ISSUE, admission.NODE, "verify-C2"))

    # Two dispatch-specific inboxes stand in for the authenticated ingress
    # already exercised by the Multica identity test. These paths are not ACLs.
    admission_log = []
    for role, name in (("B", "current.json"), ("A", "late.json"), ("A", "retry.json")):
        path = state / ("submitted-" + role) / name
        await_file(path)
        raw = path.read_bytes()
        run = "verify-C1" if role == "A" else "verify-C2"
        admission_log.append(admission.admit(database, role, run, raw, sha256(raw).hexdigest()))
        if name == "current.json":
            assert admission_log == ["current"]
            write(state / "evidence" / "B-accepted", b"pass")
    identities = {name: json.loads((state / "evidence" / name).read_bytes())
                  for name in ("A-before", "B-receiving", "A-after")}
    if coordinated:
        assert (state / "evidence" / "A-stopped").read_text().strip() == "137"
        assert (state / "evidence" / "B-accepted").read_bytes() == b"pass"
    identities["center"] = fingerprint()
    assert admission_log == ["current", "historical", "duplicate"], admission_log
    with closing(admission.connect(database)) as db:
        consumed = [tuple(x) for x in db.execute("SELECT run, verdict FROM consumed")]
        history = [tuple(x) for x in db.execute("SELECT run, placement FROM receipt ORDER BY run")]
    assert consumed == [("verify-C2", "pass")]
    assert history == [("verify-C1", "historical"), ("verify-C2", "current")]
    draws = {name: len({row[name] for row in identities.values()}) for name in ("boot", "host", "net", "mnt", "pid")}
    if distinct:
        assert all(draws[name] == 4 for name in ("net", "pid", "mnt")), draws
    print(json.dumps({"observed_execution_contexts": len(identities), "distinct_identifiers": draws,
                      "admission_order": admission_log, "node_consumption": consumed, "receipts": history},
                     indent=2), flush=True)


def start_a(state, coordinated):
    # Model a committed local outbox before its first network send.
    local = state / "A"
    assert json.loads((local / "unsent.json").read_bytes())["run"] == "verify-C1"
    write(local / "outbox.json", (local / "unsent.json").read_bytes())
    write(local / "uncommitted.txt", b"local work")
    write(local / "session-only.json", b'{"draft":true}')
    write(state / "evidence" / "A-before", json.dumps(fingerprint()).encode())
    print("A is alive with its local outbox; stopping worker before first send.", flush=True)
    # Kill this disposable fixture process only, without an exit handler.
    if coordinated:
        await_file(state / "evidence" / "B-available")
    os.kill(os.getpid(), signal.SIGKILL)


def take_over(state, coordinated):
    local = state / "B"
    write(state / "evidence" / "B-receiving", json.dumps(fingerprint()).encode())
    published = state / "publication"
    if coordinated:
        write(state / "evidence" / "B-available", b"ready")
        await_file(state / "evidence" / "A-stopped")
    raw = (published / "C2.json").read_bytes()
    contract = json.loads(raw)
    write(local / "source.bundle", (published / "code.bundle").read_bytes())
    git("init", "-q", local / "checkout")
    checkout = local / "checkout"
    git("fetch", "-q", local / "source.bundle", "refs/heads/checkpoint", cwd=checkout)
    git("checkout", "-q", "--detach", contract["commit"], cwd=checkout)
    assert git("rev-parse", "HEAD", cwd=checkout) == contract["commit"]
    assert not (checkout / ".git" / "objects" / "info" / "alternates").exists()
    assert not (checkout / "uncommitted.txt").exists() and not (checkout / "session-only.json").exists()
    assert not (local / "outbox.json").exists()
    for artifact in contract["artifacts"]:
        assert artifact["name"] in ("east.xlsx", "west.xlsx", "cross.xlsx")
        body = (published / artifact["name"]).read_bytes()
        assert sha256(body).hexdigest() == artifact["sha256"] and len(body) == artifact["bytes"]
        with ZipFile(BytesIO(body)) as obj:
            assert obj.testzip() is None and "xl/workbook.xml" in obj.namelist()
        write(local / artifact["name"], body)
    regenerated = local / "regenerated.xlsx"
    subprocess.run([sys.executable, "exporter.py", "east", str(regenerated)], cwd=checkout, check=True)
    assert regenerated.read_bytes() == (local / "east.xlsx").read_bytes()
    assert not git("status", "--porcelain", cwd=checkout)
    write(state / "submitted-B" / "current.json", raw)
    print("B fetched the fixed commit, verified three XLSX files and regenerated east.xlsx byte-for-byte.", flush=True)


def reconnect(state, coordinated):
    if coordinated:
        await_file(state / "evidence" / "B-accepted")
    write(state / "evidence" / "A-after", json.dumps(fingerprint()).encode())
    local = state / "A"
    assert (local / "uncommitted.txt").read_bytes() == b"local work"
    assert (local / "session-only.json").is_file()
    assert (state / "submitted-B" / "current.json").is_file()
    # Model a lost acknowledgement by submitting the identical original twice.
    data = (local / "outbox.json").read_bytes()
    write(state / "submitted-A" / "late.json", data)
    write(state / "submitted-A" / "retry.json", data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "reconcile", "A-stop", "B-resume", "A-reconnect"))
    parser.add_argument("state", type=Path)
    parser.add_argument("--order-run", type=Path)
    parser.add_argument("--admission", type=Path,
                        default=Path(__file__).resolve().parents[1] / "result-admission/test_admission.py")
    parser.add_argument("--distinct-namespaces", action="store_true")
    parser.add_argument("--coordinated", action="store_true", help="wait for concurrent role handshakes")
    args = parser.parse_args()
    state = args.state.resolve()
    if args.command == "setup":
        if not args.order_run:
            parser.error("setup requires --order-run from the order-export fixture")
        initialize(state, args.order_run.resolve())
    elif args.command == "reconcile":
        reconcile(state, args.admission.resolve(), args.distinct_namespaces, args.coordinated)
    else:
        {"A-stop": start_a, "B-resume": take_over, "A-reconnect": reconnect}[args.command](state, args.coordinated)


if __name__ == "__main__":
    main()
