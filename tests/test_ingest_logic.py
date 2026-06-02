from plugins.core.ingest import build_wiki_note


def test_build_wiki_note_has_frontmatter_and_source_link():
    note = build_wiki_note(
        body="A compiled concept body.",
        source_rel="Raw/Sources/example.md",
        tag="concept",
        today="2026-05-29",
    )
    assert note.startswith("---")
    assert 'tags:\n  - "concept"' in note
    assert "sources:\n  - \"Raw/Sources/example.md\"" in note
    assert "source_count: 1" in note
    assert "A compiled concept body." in note
