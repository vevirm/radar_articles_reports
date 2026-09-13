from scripts.deep_read_works import pending, source_hash, validate


def _row(title, date, strand="A"):
    return {
        "title": title,
        "date": date,
        "link": f"https://example.test/{title.replace(' ', '-')}",
        "summary": "A stored scanner summary with enough context for a provisional interpretation.",
        "source": "Example",
        "type": "peer-reviewed article",
        "strand": strand,
    }


def test_deep_pending_prioritises_never_read_research_works_before_current_signals():
    a = _row("Paper", "2026-01-01", "A")
    c = _row("Signal", "2026-09-01", "C")
    c["headline"] = c.pop("title")
    doc = {"strand_a": [a], "strand_b": [], "strand_c": [c]}
    todo = pending(doc, {"records": {}})
    assert [x[0] for x in todo] == ["strand_a", "strand_c"]


def test_deep_validation_withholds_unsupported_why():
    accepted, _ = validate(
        {
            "reader_title": "A clearer paper title",
            "what": "The study compares how two research systems fund shared infrastructure.",
            "why": "This changes Europe's strategic position in research.",
            "more": "The study compares two funding systems. It does not directly establish a European strategic consequence.",
            "work_kind": "comparative study",
            "research_question": "How do the systems fund shared infrastructure?",
            "main_finding": "They use different funding structures.",
            "method_or_basis": "Comparative analysis",
            "qualification": "The strategic consequence is not directly tested.",
            "radar_relevance": "Research infrastructure funding",
            "why_supported": False,
            "confidence": "medium",
        },
        [],
    )
    assert accepted["reader_what"]
    assert "reader_why" not in accepted
    assert accepted["deep_analysis"]["why_supported"] is False


def test_source_hash_changes_when_semantic_scanner_material_changes():
    row = _row("Paper", "2026-01-01")
    before = source_hash(row)
    row["relevance_note"] = "A materially different relevance interpretation."
    assert source_hash(row) != before


def test_completed_deep_read_is_not_requeued_when_scanner_material_changes():
    row = _row("Paper", "2026-01-01")
    key = f"link:{row['link']}"
    old_hash = source_hash(row)
    sidecar = {"records": {key: {"profile": "deep-reader-offline-v1", "source_hash": old_hash, "reader_what": "Deep result."}}}
    row["relevance_note"] = "The fast scanner later changed its interpretation."
    assert source_hash(row) != old_hash
    assert pending({"strand_a": [row], "strand_b": [], "strand_c": []}, sidecar) == []
