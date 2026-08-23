import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("scan_radar_v1753", ROOT / "scripts" / "scan_radar.py")
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)


def test_current_post_v1751_corpus_gets_one_corrective_cleanup():
    current = {"inherited_corpus_audit_complete": True}
    assert scan.needs_inherited_corpus_audit(current) is False
    assert scan.needs_precision_corpus_cleanup(current) is True
    assert scan.needs_precision_signal_cleanup(current) is True


def test_corrective_cleanup_never_repeats_after_markers():
    current = {
        "inherited_corpus_audit_complete": True,
        "precision_corpus_cleanup_complete": True,
        "precision_signal_cleanup_complete": True,
        "quality_profile_version": scan.QUALITY_PROFILE_VERSION,
    }
    assert scan.needs_inherited_corpus_audit(current) is False
    assert scan.needs_precision_corpus_cleanup(current) is False
    assert scan.needs_precision_signal_cleanup(current) is False


def test_saved_signal_cleanup_rejects_job_and_unconnected_global_tech_news():
    bad = [
        {"headline": "Doctoral researcher in Learning AI Agents job with University of Luxembourg | 12862814"},
        {"headline": "China’s solar expansion policy reduces bird diversity - Science | AAAS"},
        {"headline": "Chinese flash-memory chipmaker YMTC parent targets $4.9 billion in Shanghai IPO"},
        {"headline": "Brazil launches AI supercomputer push, splits projects between Chinese, US firms"},
    ]
    for item in bad:
        assert scan._saved_signal_passes(item) is False


def test_saved_signal_cleanup_keeps_eu_strategic_ri_developments():
    good = [
        {"headline": "EU-China research cooperation limited to ‘targeted areas’"},
        {"headline": "Europe commits €5 billion to fund seven AI megafactories and catch up with the US and China"},
        {"headline": "Japan formally joins Horizon Europe as associated country"},
        {"headline": "Research security in Europe: Building resilience without creating barriers"},
    ]
    for item in good:
        assert scan._saved_signal_passes(item) is True
