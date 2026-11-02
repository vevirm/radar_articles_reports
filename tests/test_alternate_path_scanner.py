import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('alternate',Path(__file__).resolve().parents[1]/'scripts'/'alternate_path_scanner.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_url_normalization_removes_trackers():
    assert m.normalize('http://www.example.org/Reports/test.pdf?utm_source=x') == 'https://example.org/Reports/test.pdf'

def test_domain_boundaries():
    assert m.domain_match('https://eupinions.bertelsmann-stiftung.de/thing','bertelsmann-stiftung.de')
    assert not m.domain_match('https://bertelsmann-stiftung.de.attacker.org','bertelsmann-stiftung.de')

def test_html_discovery():
    x=m.extract_links('<a href="/fileadmin/report-2026.pdf">Digital sovereignty in Europe report</a>', 'https://example.org','text/html')
    assert x[0][0]=='https://example.org/fileadmin/report-2026.pdf'
    assert m.relevance(*x[0][::-1])>=2

def test_existing_urls_and_titles():
    keys=m.existing_keys({'strand_a':[{'link':'http://www.example.org/a.pdf','title':'A Report'}]}, {'candidates':[]})
    assert 'url:https://example.org/a.pdf' in keys
    assert 'title:a report' in keys

def test_reject_homepages_and_generic_hubs():
    assert not m.publication_shape({'title':'Publications','link':'https://example.org/publications'})
    assert not m.publication_shape({'title':'Digital innovation','link':'https://example.org/'})
    assert not m.publication_shape({'title':'Europe research','link':'https://example.org/en/research'})

def test_keep_strong_document_shape():
    assert m.publication_shape({'title':'Digital sovereignty in Europe policy brief 2026', 'link':'https://example.org/files/digital-sovereignty-2026.pdf'})

def test_verification_rejects_unreachable(monkeypatch):
    monkeypatch.setattr(m,'fetch',lambda *a,**k: ('','',''))
    import time
    assert m.verify_publication({'title':'European technology policy report','link':'https://example.org/files/report.pdf','source_domain':'example.org'}, time.monotonic()+30) is None
