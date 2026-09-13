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



def test_deep_pending_is_fifo_across_strands_and_new_discoveries_wait():
    legacy = _row("Legacy without first seen", "2026-08-01", "B")
    older = _row("Older discovered work", "2026-09-01", "C")
    older["headline"] = older.pop("title")
    older["first_seen"] = "2026-09-10T08:00Z"
    middle = _row("Middle discovered work", "2026-07-01", "A")
    middle["first_seen"] = "2026-09-11T08:00Z"
    newest = _row("New scanner discovery", "2025-01-01", "A")
    newest["first_seen"] = "2026-09-13T16:00Z"
    doc = {"strand_a": [newest, middle], "strand_b": [legacy], "strand_c": [older]}
    todo = pending(doc, {"records": {}})
    assert [x[3].get("title") or x[3].get("headline") for x in todo] == [
        "Legacy without first seen", "Older discovered work", "Middle discovered work", "New scanner discovery"
    ]

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


def test_legacy_completed_deep_read_is_requeued_once_for_v2_verification():
    row = _row("Paper", "2026-01-01")
    key = f"link:{row['link']}"
    old_hash = source_hash(row)
    sidecar = {"records": {key: {"profile": "deep-reader-offline-v1", "source_hash": old_hash, "reader_what": "Deep result."}}}
    row["relevance_note"] = "The fast scanner later changed its interpretation."
    assert source_hash(row) != old_hash
    todo = pending({"strand_a": [row], "strand_b": [], "strand_c": []}, sidecar)
    assert len(todo) == 1
    assert todo[0][-1] == "upgrade_legacy_deep_scan_to_v2"


def test_authoritative_v2_is_complete_and_not_requeued_after_scanner_change():
    row = _row("Paper", "2026-01-01")
    key = f"link:{row['link']}"
    sidecar = {"records": {key: {"profile": "deep-reader-v2-authoritative", "reader_what": "Verified."}}}
    row["relevance_note"] = "The fast scanner later changed its interpretation."
    assert pending({"strand_a": [row], "strand_b": [], "strand_c": []}, sidecar) == []


def test_frontier_matrix_evidence_also_waits_for_deep_scan_v2():
    frontier = _row("Older matrix recovery evidence", "2025-12-01", "A")
    doc = {"strand_a": [], "strand_b": [], "strand_c": [], "frontier_evidence": [frontier]}
    todo = pending(doc, {"records": {}})
    assert len(todo) == 1
    assert todo[0][0] == "frontier_evidence"
