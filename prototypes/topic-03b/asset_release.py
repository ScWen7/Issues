"""A scoped Rule/Script publication and selection model for the order-export case."""
from dataclasses import dataclass
from hashlib import sha256


def digest(data):
    return sha256(data).hexdigest()


@dataclass(frozen=True)
class Release:
    scope: str
    version: str
    decision: str
    source: str
    published_by: str
    replaces: tuple[str, str] | None
    rule_sha: str
    script_sha: str


@dataclass(frozen=True)
class Selection:
    project: str
    instance: str
    release: Release
    reason: str


class Catalog:
    """Single-process fixture. The caller supplies the authenticated member."""
    def __init__(self, publishers, projects, project_readers):
        self.publishers = publishers
        self.projects = projects  # project -> team
        self.project_readers = project_readers
        self.releases = {}
        self.content = {}
        self.active = {}
        self.withdrawn = {}
        self.pins = {}

    def check_publisher(self, actor, scope):
        if scope not in set(self.projects) | set(self.projects.values()):
            raise ValueError("unknown scope")
        if actor not in self.publishers.get(scope, ()):
            raise PermissionError("publish scope")

    def publish(self, actor, scope, version, decision, source, rule, script, expected, replaces=None):
        self.check_publisher(actor, scope)
        release = Release(scope, version, decision, source, actor, replaces, digest(rule), digest(script))
        key = (scope, version)
        if key in self.releases:
            prior = self.releases[key]
            if (prior.decision, prior.source, prior.replaces, prior.rule_sha, prior.script_sha) != (
                    decision, source, replaces, release.rule_sha, release.script_sha):
                raise ValueError("version content or provenance changed")
            return prior  # replay returns the original publication, never reactivates it
        if scope in self.projects:
            team = self.projects[scope]
            if replaces is None or replaces != (team, self.active.get(team)) or replaces not in self.releases:
                raise ValueError("unresolved project replacement")
        if self.active.get(scope) != expected:
            raise ValueError("publication head changed")
        self.content[release.rule_sha], self.content[release.script_sha] = rule, script
        self.releases[key] = release
        self.active[scope] = version
        return release

    def withdraw(self, actor, scope, version):
        self.check_publisher(actor, scope)
        if (scope, version) not in self.releases:
            raise KeyError("unknown release")
        self.withdrawn.setdefault((scope, version), actor)

    def select(self, project, instance, decision, actor):
        if actor not in self.project_readers.get(project, ()):
            raise PermissionError("project access withdrawn")
        team = self.projects[project]
        key = (project, instance)
        if key in self.pins:
            selected = self.pins[key]
            if selected.release.decision != decision:
                raise ValueError("successor instance required")
            return selected
        # A project entry is the explicitly approved replacement in this fixture.
        scope = project if project in self.active else team
        version = self.active[scope]
        release = self.releases[scope, version]
        if scope == project and release.replaces != (team, self.active.get(team)):
            raise ValueError("project replacement needs review")
        if (scope, version) in self.withdrawn or release.decision != decision:
            raise ValueError("required release unavailable for this decision")
        result = Selection(project, instance, release, "project replacement" if scope == project else "team default")
        self.pins[key] = result
        return result

    def prepare(self, selected, actor):
        if actor not in self.project_readers.get(selected.project, ()):
            raise PermissionError("project access withdrawn")
        if self.pins.get((selected.project, selected.instance)) != selected:
            raise ValueError("unknown selection")
        r = selected.release
        if (r.scope, r.version) in self.withdrawn:
            raise PermissionError("withdrawn before execution")
        rule, script = self.content[r.rule_sha], self.content[r.script_sha]
        if digest(rule) != r.rule_sha or digest(script) != r.script_sha:
            raise ValueError("material digest mismatch")
        return rule, script
