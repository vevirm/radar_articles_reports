from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_trends_is_its_own_page_and_public_copy_is_result_not_method():
    page = (ROOT / "trends/index.html").read_text(encoding="utf-8")
    assert "When we look across the Radar evidence" in page
    assert "How the evidence is read" not in page
    assert "Distinct claims count" not in page
    assert "hostile witness" not in page.lower()
    assert "actor-reporting" not in page.lower()
    assert "observer-reporting" not in page.lower()
    assert "weight ${esc(e.quality)}/100" not in page
    assert "../shocks/" in page  # separate destination in the reader path


def test_shock_page_does_not_embed_trend_countertrend_pairs():
    shock = (ROOT / "shocks/index.html").read_text(encoding="utf-8")
    assert "RadarTrends.build" not in shock
    assert "trends.js" not in shock
    # Shock-specific directional evidence remains on the shock page.
    assert "What points toward it" in shock
    assert "What pushes against it" in shock
