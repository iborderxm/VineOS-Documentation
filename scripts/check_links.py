#!/usr/bin/env python3
"""Check relative links and heading anchors in every Markdown file."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules"}
FENCE = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.S | re.M)
INLINE_CODE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$", re.M)


def strip_code(text):
    return INLINE_CODE.sub("", FENCE.sub("", text))


def slug(heading):
    heading = re.sub(r"<[^>]+>|[*_`]", "", heading.strip().lower())
    heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    heading = re.sub(r"[^\w\- ]", "", heading, flags=re.UNICODE)
    return heading.replace(" ", "-")


def anchors_of(path):
    seen = {}
    found = set()
    for _, title in HEADING.findall(strip_code(path.read_text(encoding="utf-8"))):
        base = slug(title)
        count = seen.get(base, 0)
        found.add(base if count == 0 else f"{base}-{count}")
        seen[base] = count + 1
    return found


def markdown_files():
    for path in sorted(ROOT.rglob("*.md")):
        if not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            yield path


def main():
    errors = []
    anchor_cache = {}
    for md in markdown_files():
        for target in LINK.findall(strip_code(md.read_text(encoding="utf-8"))):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("//"):
                continue
            raw_path, _, fragment = target.partition("#")
            dest = md if not raw_path else (md.parent / raw_path).resolve()
            rel = md.relative_to(ROOT)
            if not dest.exists():
                errors.append(f"{rel}: missing file {target}")
                continue
            if fragment and dest.suffix == ".md":
                if dest not in anchor_cache:
                    anchor_cache[dest] = anchors_of(dest)
                if fragment.lower() not in anchor_cache[dest]:
                    errors.append(f"{rel}: missing anchor {target}")
    for error in errors:
        print(error)
    print(f"checked {sum(1 for _ in markdown_files())} files, {len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
