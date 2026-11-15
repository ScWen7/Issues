"""Synthetic, paginated subset of the Feishu Docx block shape and source permissions."""
from copy import deepcopy


class Origin:
    def __init__(self):
        self.versions = {}
        self.current = {}
        self.readers = {}
        self.unknown = set()
        self.fail_page = None
        self.on_page = None
        self.calls = []

    def publish(self, source, revision, sections):
        if revision <= self.current.get(source, 0):
            raise ValueError("fixture revisions must increase")
        children = []
        blocks = {source: {"block_id": source, "block_type": 1, "children": children}}
        for heading, title, text in sections:
            for key, kind, prop, body in (
                    (heading, 4, "heading2", title), (heading + "-p", 2, "text", text)):
                if key in blocks:
                    raise ValueError("duplicate fixture block")
                children.append(key)
                blocks[key] = {"block_id": key, "parent_id": source, "block_type": kind,
                               prop: {"elements": [{"text_run": {"content": body}}]}}
        self.versions[source, revision] = tuple(blocks.values())
        self.current[source] = revision

    def head(self, source):
        if source in self.unknown:
            raise ConnectionError("mock source temporarily unreachable")
        if source not in self.current:
            raise FileNotFoundError(source)
        return self.current[source]

    def can_read(self, actor, source):
        if source in self.unknown:
            raise ConnectionError("read right unknown")
        return actor in self.readers.get(source, ())

    def page(self, source, revision, token):
        offset = int(token or 0)
        self.calls.append((source, revision, offset))
        if self.fail_page == (source, offset):
            raise ConnectionError("interrupted before next page")
        rows = self.versions[source, revision]
        next_offset = offset + 2
        data = {"items": deepcopy(rows[offset:next_offset]), "has_more": next_offset < len(rows)}
        if data["has_more"]:
            data["page_token"] = str(next_offset)
        if self.on_page:
            self.on_page(source, revision, offset)
        return data
