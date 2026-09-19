from app.rag.chunking import MAX_CHARS, chunk_markdown

DOC = """# Page

Intro paragraph that is long enough to survive the minimum size filter for chunks, really.

## Setup

Step one is to configure things properly and carefully before doing anything else at all.

```
# not a heading, inside a fence
run --this
```

### Advanced

Advanced details that belong only under the advanced heading, and are long enough to keep.
"""


def test_chunks_carry_their_heading_path():
    chunks = chunk_markdown(DOC, "Page")
    assert any(c.startswith("Page > Setup > Advanced\n") for c in chunks)
    assert any(c.startswith("Page > Setup\n") for c in chunks)


def test_sections_are_not_mixed():
    advanced = [c for c in chunk_markdown(DOC, "Page") if c.startswith("Page > Setup > Advanced")]
    assert len(advanced) == 1 and "Step one" not in advanced[0]


def test_heading_inside_code_fence_is_not_a_heading_and_fence_stays_whole():
    setup = next(c for c in chunk_markdown(DOC, "Page") if c.startswith("Page > Setup\n"))
    assert "# not a heading, inside a fence\nrun --this" in setup
    assert not any(c.startswith("Page > not a heading") for c in chunk_markdown(DOC, "Page"))


def test_oversized_block_is_split_within_limit():
    long = "This is a sentence about tokens. " * 200
    chunks = chunk_markdown(f"# T\n\n{long}", "T")
    assert len(chunks) > 1 and all(len(c) <= MAX_CHARS for c in chunks)


def test_unbroken_giant_line_is_hard_split():
    chunks = chunk_markdown("# T\n\n" + "x" * 5000, "T")
    assert len(chunks) > 1 and all(len(c) <= MAX_CHARS for c in chunks)


def test_tiny_fragments_are_dropped():
    assert chunk_markdown("# T\n\nhi", "T") == []
