"""Observe TeamAI's project Rule selection and follow one review into two host delivery channels."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from tempfile import TemporaryDirectory


REV = "1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956"
RULE = "export-policy.md"
D1 = "ORDER-CHECK-D1-REGIONAL"
D2 = "ORDER-CHECK-D2-PAID-AT"
TEAM = "ORDER-CHECK-TEAM-DEFAULT"


def write(file, content):
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")


def probe(upstream, root):
    cli = upstream / "dist" / "index.js"
    version = subprocess.check_output(["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
    if version != REV or not cli.is_file():
        raise SystemExit(f"Build the TeamAI CLI at {REV} before running")
    home, seed, project = (root / name for name in ("home", "seed", "business"))
    for directory in (home, seed, project):
        directory.mkdir()
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()
    common = {"HOME": str(home), "USERPROFILE": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
              "PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
              "GIT_AUTHOR_NAME": "Order fixture", "GIT_COMMITTER_NAME": "Order fixture",
              "GIT_AUTHOR_EMAIL": "fixture@example.test", "GIT_COMMITTER_EMAIL": "fixture@example.test",
              "FORCE_COLOR": "0", "LC_ALL": "C.UTF-8"}
    def run(command, cwd, stdin=""):
        result = subprocess.run(command, cwd=cwd, env=common, text=True, input=stdin,
                                capture_output=True, timeout=40)
        if result.returncode:
            raise RuntimeError(f"{command[:3]}: {result.stdout[-1000:]} {result.stderr[-1000:]}")
        return result.stdout + (result.stderr if command[0] == "node" and "hook-dispatch" not in command else "")
    def git(cwd, *args):
        return run(["git", *args], cwd).strip()
    def team(*args):
        return run(["node", str(cli), *args], project)
    contended = 0
    def pull():
        nonlocal contended
        # SessionStart can schedule a detached sync. A manual pull can return 0
        # after reporting lock contention; wait for that owner and then retry.
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            if "sync in progress elsewhere" not in team("pull"):
                return
            contended += 1
            time.sleep(0.25)
        raise TimeoutError("TeamAI sync was still held")
    def hook(source):
        event = {"hook_event_name": "SessionStart", "source": source, "cwd": str(project), "session_id": "order-fixture"}
        raw = run(["node", str(cli), "hook-dispatch", "session-start", "--tool", "codex"], project, json.dumps(event))
        data = json.loads(raw) if raw.strip() else {}
        return data.get("hookSpecificOutput", {}).get("additionalContext", "")

    remote = root / "shared.git"
    url = "https://git.example.test/team/order-fixture.git"
    git(seed, "init", "-q", "-b", "main")
    write(seed / "teamai.yaml", f"team: order-fixture\nrepo: {url}\nprovider: git\nreviewers: []\n")
    write(seed / "manifest/projects.yaml", "version: 1\nprojects:\n  - id: orders\n    resources: { knowledge: [orders] }\n")
    write(seed / "rules" / RULE, TEAM + "\n")
    write(seed / "rules" / "orders" / RULE, D1 + "\n")
    git(seed, "add", "-A")
    git(seed, "commit", "-qm", "D1")
    first = git(seed, "rev-parse", "HEAD")
    git(root, "clone", "-q", "--bare", str(seed), str(remote))
    git(root, "config", "--global", f"url.{remote}.insteadOf", url)
    git(project, "init", "-q", "-b", "main")
    write(project / "README.md", "# Order fixture\n")
    git(project, "add", "README.md")
    git(project, "commit", "-qm", "business")
    team("init", url, "--provider", "git", "--agent", "claude,codex", "--scope", "project", "--force")
    team("projects", "set", "orders")
    pull()
    root_copy = project / ".claude" / "rules" / RULE
    copy = project / ".claude" / "rules" / "orders" / RULE
    def assert_delivery(marker, other):
        assert copy.read_text().strip() == marker and not root_copy.exists()
        text = hook("startup")
        assert marker in text and other not in text and TEAM not in text

    assert_delivery(D1, D2)
    git(seed, "checkout", "-qb", "review-D2")
    write(seed / "rules" / "orders" / RULE, D2 + "\n")
    git(seed, "commit", "-qam", "D2 review")
    second = git(seed, "rev-parse", "HEAD")
    git(seed, "push", "-q", str(remote), "review-D2")
    pull()
    assert_delivery(D1, D2)
    git(seed, "checkout", "-q", "main")
    git(seed, "merge", "-q", "--ff-only", "review-D2")
    git(seed, "push", "-q", str(remote), "main")
    pull()
    assert_delivery(D2, D1)
    resume = hook("resume")
    assert D1 not in resume and D2 not in resume
    print(json.dumps({"project": "orders", "D1": first, "D2": second, "review_only": "D1",
                      "after_merge": "D2", "claude_file": True, "codex_startup": "D2",
                      "codex_resume_rule_markers": [], "contended_pulls": contended, "host_model_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("teamai_checkout", type=Path)
    with TemporaryDirectory(prefix="order-rule-") as scratch:
        probe(parser.parse_args().teamai_checkout.resolve(), Path(scratch))
