"""Check repository Markdown links and the path from the homepage to each design."""
from collections import defaultdict
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r'\]\((?:<([^>]+)>|([^\s)]+))(?:\s+"[^"]*")?\)')
HEADING = re.compile(r'^#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$')


def headings_and_links(path):
    anchors = set()
    targets = []
    fence = None
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token.startswith(fence) and not line[marker.end():].strip():
                fence = None
            continue
        if fence is not None:
            continue
        heading = HEADING.match(line)
        if heading:
            title = heading.group(1).lower()
            slug = ''.join(c for c in title if c in ' -_' or unicodedata.category(c)[0] in 'LNM').replace(' ', '-')
            anchor = slug
            suffix = 0
            while anchor in anchors:
                suffix += 1
                anchor = f"{slug}-{suffix}"
            anchors.add(anchor)
        targets.extend((number, m.group(1) or m.group(2)) for m in LINK.finditer(line))
    return anchors, targets


def main():
    pages = {p: headings_and_links(p) for p in ROOT.rglob("*.md") if ".git" not in p.parts}
    edges = defaultdict(set)
    errors = []
    checked = 0
    for page, (_, targets) in pages.items():
        for number, target in targets:
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            checked += 1
            path = unquote(url.path)
            dest = (page.parent / path).resolve() if path else page
            if not dest.is_relative_to(ROOT) or not dest.exists():
                errors.append(f"{page.relative_to(ROOT)}:{number}: missing {target}")
            elif dest in pages:
                edges[page].add(dest)
                if url.fragment and unquote(url.fragment) not in pages[dest][0]:
                    errors.append(f"{page.relative_to(ROOT)}:{number}: missing heading {target}")
    seen = set()
    pending = [ROOT / "README.md"]
    while pending:
        page = pending.pop()
        if page in seen:
            continue
        seen.add(page)
        if page.is_relative_to(ROOT / "docs/architecture") or page == ROOT / "README.md":
            pending.extend(edges[page] - seen)
    for page in sorted((ROOT / "docs/architecture").glob("*.md")):
        if page not in seen:
            errors.append(f"{page.relative_to(ROOT)}: unreachable from README through the design documents")
    for error in errors:
        print(error, file=sys.stderr)
    print(f"{len(pages)} Markdown files, {checked} internal links, {len(errors)} errors")
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
