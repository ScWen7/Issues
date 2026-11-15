"""Exercise real TeamAI skill delivery with an on-disk control for each pull."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

REVISION = "1bc2ce18e0b3666f512ee7d0d94f6a5e0c9fc956"


def put(directory, filename, content):
    path = directory / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def skill(remote, name, instruction):
    put(remote, f"skills/{name}/SKILL.md",
        f"---\nname: {Path(name).name}\ndescription: Order export check\n---\n\n{instruction}\n")


def run_probe(upstream, tmp):
    cli = upstream / "dist/index.js"
    if subprocess.check_output(["git", "-C", upstream, "rev-parse", "HEAD"], text=True).strip() != REVISION:
        raise ValueError(f"build TeamAI at {REVISION}")
    home, remote, project = (tmp / name for name in ("home", "source", "orders"))
    for directory in (home, remote, project):
        directory.mkdir()
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), NO_COLOR="1",
               GIT_AUTHOR_NAME="Research", GIT_AUTHOR_EMAIL="case@example.invalid",
               GIT_COMMITTER_NAME="Research", GIT_COMMITTER_EMAIL="case@example.invalid")

    def git(directory, *args):
        subprocess.run(["git", *args], cwd=directory, env=env, check=True, capture_output=True)

    def teamai(*args):
        return subprocess.run(["node", cli, *args], cwd=project, env=env, capture_output=True, text=True)

    put(remote, "teamai.yaml", f"""team: composition-study
repo: {remote}
provider: tgit
toolPaths:
  claude:
    skills: .claude/skills
""")
    put(remote, "manifest/roles.yaml", """version: 1
roles:
  - id: developer
    resources: {knowledge: [dev], skills: [dev]}
  - id: verifier
    resources: {knowledge: [qa], skills: [qa]}
""")
    skill(remote, "order-check", "SHARED: Check the recorded result.")
    skill(remote, "dev/order-check", "DEV: Include the payment time column.")
    skill(remote, "qa/order-check", "QA: Compare the exported visible order sets.")
    # Different resource names with opposing directions on the very same column.
    skill(remote, "dev/fast-export", "LEGACY: Omit the payment time column.")
    put(remote, "teamwiki/router.md", "# Order router\nordercheck ROUTE_MARK\n")
    put(remote, "teamwiki/evidence/code/orders/overview.md", "---\ntitle: ordercheck verifier\n---\n"
        + "ordercheck START_MARK " + ("column sample " * 100) + " TAIL_MARK\n")
    git(remote, "init", "-q", "-b", "main")
    git(remote, "add", ".")
    git(remote, "commit", "-qm", "order skills")
    repo = project / ".teamai/team-repo"
    git(project, "clone", "-q", str(remote), str(repo))
    installed = project / ".claude/skills"
    installed.mkdir(parents=True)

    def select(roles):
        put(project, ".teamai/config.yaml", f"""repo:
  localPath: {repo}
  remote: {remote}
username: order-member
scope: project
projectRoot: {project}
updatePolicy: auto
enabledAgents: [claude]
{roles}
""")

    def body(name):
        return (installed / name / "SKILL.md").read_bytes()

    def assert_next(roles, expected):
        select(roles)
        pull = teamai("pull", "--force")
        assert pull.returncode == 0, (pull.stdout, pull.stderr)
        raw = body("order-check")
        assert expected.encode() in raw, raw
        return hashlib.sha256(raw).hexdigest()

    shared = assert_next("", "SHARED:")
    developer = assert_next("primaryRole: developer", "DEV:")
    assert b"Omit the payment time column." in body("fast-export")
    select("primaryRole: developer\nadditionalRoles: [verifier]")
    clash = teamai("pull", "--force")
    message = clash.stdout + clash.stderr
    assert "Skills were not updated" in message and "skills/dev/order-check" in message and "skills/qa/order-check" in message, message
    retained = hashlib.sha256(body("order-check")).hexdigest()
    assert retained == developer and b"LEGACY:" in body("fast-export")
    verifier = assert_next("primaryRole: verifier", "QA:")
    assert not (installed / "fast-export").exists()
    assert len({shared, developer, verifier}) == 3
    plain, expanded = teamai("skill", "get", "wiki"), teamai("skill", "get", "wiki", "--full")
    assert plain.returncode == expanded.returncode == 0
    assert expanded.stdout.startswith(plain.stdout) and "--- references/" in expanded.stdout[len(plain.stdout):]
    recalls = {}
    for depth in ("route", "context", "lookup"):
        result = teamai("recall", "ordercheck", "--depth", depth)
        assert result.returncode == 0, result.stderr
        recalls[depth] = [mark for mark in ("ROUTE_MARK", "START_MARK", "TAIL_MARK") if mark in result.stdout]
    assert recalls == {"route": ["ROUTE_MARK"], "context": ["START_MARK"], "lookup": ["START_MARK", "TAIL_MARK"]}, recalls
    return {"recall_depths": recalls, "shared": shared, "developer": developer, "different_name_conflict_delivered": True,
            "same_name_conflict_exit": clash.returncode, "retained": retained, "verifier": verifier,
            "wiki_default_bytes": len(plain.stdout.encode()), "wiki_full_bytes": len(expanded.stdout.encode())}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path, help="built TeamAI source checkout")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        print(json.dumps(run_probe(args.upstream.resolve(), Path(tmp)), indent=2))
