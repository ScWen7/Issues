"""Research model for versioned document sections, role selection and input delivery."""
from dataclasses import dataclass
from hashlib import sha256


def digest(text):
    return sha256(text.encode()).hexdigest()


class Pending(Exception):
    """Caller gets a generic missing-input reason, not hidden document metadata."""


@dataclass(frozen=True)
class Section:
    source: str
    revision: int
    heading: str
    title: str
    blocks: tuple
    body: str

    @property
    def sha(self):
        return digest(self.body)

    def cite(self):
        return {"source": self.source, "revision": self.revision, "heading": self.heading,
                "blocks": self.blocks, "sha256": self.sha}


@dataclass(frozen=True)
class Binding:
    member: str
    project: str
    role: str
    issue: str
    node: str
    run: str
    attempt: int


def block_text(block, key):
    elements = block[key]["elements"]
    if not all("text_run" in item for item in elements):
        raise ValueError("unsupported element in the selected document profile")
    return "".join(item["text_run"]["content"] for item in elements)


def parse_sections(source, revision, blocks):
    """Flat Docx fixture profile: root page, heading2 and rich text paragraphs."""
    by_id = {b["block_id"]: b for b in blocks}
    if len(by_id) != len(blocks):
        raise ValueError("duplicate block")
    page = by_id[source]
    if page["block_type"] != 1 or set(page["children"]) != set(by_id) - {source}:
        raise ValueError("incomplete or unsupported document tree")
    heading = None
    groups = {}
    ordered = page["children"]
    if len(set(ordered)) != len(ordered):
        raise ValueError("duplicate child")
    for key in ordered:
        block = by_id[key]
        if block["parent_id"] != source:
            raise ValueError("invalid parent")
        if block["block_type"] == 4:
            heading = key
            groups[heading] = (block_text(block, "heading2"), [])
        elif block["block_type"] == 2 and heading is not None:
            groups[heading][1].append((key, block_text(block, "text")))
        else:
            raise ValueError("unsupported block; retain last complete snapshot")
    return {h: Section(source, revision, h, title, tuple(key for key, _ in rows),
                       "\n".join(body for _, body in rows))
            for h, (title, rows) in groups.items() if rows}


class Index:
    def __init__(self):
        self.snapshots = {}
        self.revisions = {}
        self.checked = {}
        self.state = {}

    def refresh(self, source, origin, checked_at):
        """Fetch one exact revision into staging, then replace the visible snapshot."""
        try:
            revision = origin.head(source)
            if revision < self.revisions.get(source, 0):
                raise ValueError("old revision")
            blocks, visited, token = [], set(), None
            while True:
                if token in visited:
                    raise ValueError("repeated page cursor")
                visited.add(token)
                page = origin.page(source, revision, token)
                blocks.extend(page["items"])
                if not page["has_more"]:
                    break
                token = page["page_token"]
            sections = parse_sections(source, revision, blocks)
            if origin.head(source) != revision:
                raise ValueError("source advanced while reading")
            if revision == self.revisions.get(source) and self.snapshots[source] != sections:
                raise ValueError("immutable revision returned different content")
        except FileNotFoundError:
            # The fixture emits this only for a confirmed source tombstone.
            self.state[source] = "withdrawn"
            raise
        except (OSError, ValueError, KeyError, TypeError):
            self.state[source] = "unconfirmed"
            raise
        self.snapshots[source] = sections
        self.revisions[source] = revision
        self.checked[source] = checked_at
        self.state[source] = "current"

    def require_current(self, source, origin):
        if self.state.get(source) != "current":
            raise Pending("required input unavailable")
        try:
            current = origin.head(source)
        except FileNotFoundError:
            self.state[source] = "withdrawn"
            raise Pending("required input unavailable") from None
        except OSError:
            self.state[source] = "unconfirmed"
            raise Pending("required input unavailable") from None
        if current != self.revisions[source]:
            self.state[source] = "unconfirmed"
            raise Pending("required input unavailable")


class Assembly:
    def __init__(self, index, origin, bindings, members, plans):
        self.index = index
        self.origin = origin
        self.bindings = bindings  # issued dispatches keyed by Run
        self.members = members    # project -> current members
        self.plans = plans        # role within project -> ordered required source/heading refs
        self.receipts = {}

    def references(self, actor, run):
        binding = self.bindings.get(run)
        if binding is None or actor != binding.member or actor not in self.members.get(binding.project, ()):
            raise Pending("required input unavailable")
        return self.plans[binding.project, binding.role]

    def readable_section(self, actor, source, heading):
        try:
            allowed = self.origin.can_read(actor, source)
        except OSError:
            allowed = False
        if not allowed:
            raise Pending("required input unavailable")
        self.index.require_current(source, self.origin)
        section = self.index.snapshots[source].get(heading)
        if section is None:
            raise Pending("required input unavailable")
        return section

    def lookup(self, actor, run, query):
        refs = self.references(actor, run)
        term = query.strip().casefold()
        hits = []
        if not term:
            return hits
        for source, heading in refs:
            try:
                section = self.readable_section(actor, source, heading)
            except Pending:
                continue
            if term in section.title.casefold() or term in section.body.casefold():
                hits.append({"title": section.title, "excerpt": section.body, "citation": section.cite()})
        return hits

    def select(self, actor, run):
        refs = self.references(actor, run)
        # The host experiment uses a short alias per excerpt. Reject ambiguous plans.
        if len({heading for _, heading in refs}) != len(refs):
            raise Pending("ambiguous section alias")
        return tuple(self.readable_section(actor, source, heading) for source, heading in refs)

    def queue(self, actor, run):
        # Queued receipts contain references only. The host handoff re-reads authority.
        return tuple(s.cite() for s in self.select(actor, run))

    def deliver(self, actor, run, queued, turn):
        sections = self.select(actor, run)
        if tuple(s.cite() for s in sections) != queued:
            raise Pending("selected source changed")
        key = (run, turn)
        if key in self.receipts and self.receipts[key] != queued:
            raise Pending("turn already bound")
        self.receipts[key] = queued
        return {s.heading: s.body for s in sections}

    def affected(self, source, heading, old_sha):
        # Restricted internal audit: references only, no re-delivery of historical text.
        return sorted([run, turn] for (run, turn), refs in self.receipts.items()
                      if any(r["source"] == source and r["heading"] == heading
                             and r["sha256"] == old_sha for r in refs))
