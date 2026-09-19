"""Heading-aware Markdown chunking.

Sections are split on headings, so a chunk never straddles two topics, and every chunk is prefixed with its
heading path ("Page > Section > Subsection") so it still makes sense when retrieved on its own. Within a
section, blank-line-separated blocks are packed up to `max_chars`; fenced code blocks and tables stay whole
unless a single block is itself larger than the limit, in which case it is split on line/sentence boundaries.
"""
import re

MAX_CHARS = 1000
MIN_CHARS = 80
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _sections(markdown: str, title: str) -> list[tuple[str, str]]:
    """[(heading_path, body)] in document order. Headings inside code fences are not headings."""
    path: list[tuple[int, str]] = [(0, title)]
    out: list[tuple[str, list[str]]] = [(title, [])]
    in_fence = False
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m and len(m.group(1)) == 1 and m.group(2).strip().lower() == title.strip().lower():
            continue  # the page's own H1 just repeats the title we already prefix
        if m:
            level, text = len(m.group(1)), m.group(2)
            while path and path[-1][0] >= level:
                path.pop()
            path.append((level, text))
            out.append((" > ".join(t for _, t in path), []))
        else:
            out[-1][1].append(line)
    return [(h, "\n".join(body).strip()) for h, body in out if "\n".join(body).strip()]


def _blocks(body: str) -> list[str]:
    """Blank-line separated blocks, keeping fenced code intact."""
    blocks, cur, in_fence = [], [], False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not line.strip() and not in_fence:
            if cur:
                blocks.append("\n".join(cur))
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def _split_oversized(block: str, max_chars: int) -> list[str]:
    pieces, cur = [], ""
    for unit in re.split(r"(?<=[.!?])\s+|\n", block):
        while len(unit) > max_chars:  # e.g. a minified line: hard split as a last resort
            pieces.append(unit[:max_chars])
            unit = unit[max_chars:]
        if cur and len(cur) + len(unit) + 1 > max_chars:
            pieces.append(cur)
            cur = unit
        else:
            cur = f"{cur} {unit}".strip() if cur else unit
    if cur:
        pieces.append(cur)
    return pieces


def chunk_markdown(markdown: str, title: str, max_chars: int = MAX_CHARS) -> list[str]:
    chunks = []
    for heading, body in _sections(markdown, title):
        prefix = f"{heading}\n"
        budget = max_chars - len(prefix)
        cur = ""
        for block in _blocks(body):
            for piece in ([block] if len(block) <= budget else _split_oversized(block, budget)):
                if cur and len(cur) + len(piece) + 2 > budget:
                    chunks.append(prefix + cur)
                    cur = piece
                else:
                    cur = f"{cur}\n\n{piece}" if cur else piece
        if cur:
            chunks.append(prefix + cur)
    return [c for c in chunks if len(c) >= MIN_CHARS]
