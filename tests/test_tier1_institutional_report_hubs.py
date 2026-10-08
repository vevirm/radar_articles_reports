"""Regression coverage: Tier-1 European R&I report publication hubs (discovery only)."""
import datetime as dt
import importlib.util
from pathlib import Path
from unittest import TestCase, mock
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('test_tier1_scan', ROOT / 'scripts/scan_radar.py')
scan = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)

class FakePage:
    def __init__(self, url, html):
        self.url = url
        self.text = html
        self.headers = {'content-type': 'text/html'}
    def __bool__(self):
        return True

class ReportHubs(TestCase):
    def test_tier1_targets_configured_on_publisher_host(self):
        conf = json.loads((ROOT / 'radar_config.json').read_text())
        adapter = conf['institution_source_adapters']
        wanted = {
            'esfri.eu': ['/publications/', '/publications/policy-documents'],
            'espas.eu': ['/general.html'],
            'europarl.europa.eu': ['/stoa/en/publications/search'],
            'bruegel.org': ['/publications/working-papers'],
            'oecd.org': ['/en/publications.html'],
        }
        present = {s['domain'] for s in conf['institution_sources']}
        for domain, urls in wanted.items():
            with self.subTest(domain=domain):
                self.assertIn(domain, present)
                self.assertEqual(len(adapter[domain]['hub_paths']), len(set(adapter[domain]['hub_paths'])))
                for path in urls:
                    self.assertIn(path, adapter[domain]['hub_paths'])
                    self.assertLess(adapter[domain]['hub_paths'].index(path), conf['institution_source_adapter_max_hub_fetches'])

    def test_stoa_publication_search_enqueues_real_studies_but_not_cross_domain_noise(self):
        config = json.loads((ROOT / 'radar_config.json').read_text())
        src = next(s for s in config['institution_sources'] if s['domain'] == 'europarl.europa.eu')
        pub = 'https://www.europarl.europa.eu/stoa/en/document/EPRS_STU(2026)123456'
        html = f'''<html lang="en"><main>
          <a href="{pub}">Study on European research and technology assessment</a>
          <a href="https://example.net/advertising/">Research news</a>
        </main></html>'''
        def fake_get(url, **kwargs):
            if 'stoa/en/publications/search' in url:
                return FakePage(url, html)
            return None
        with mock.patch.object(scan, 'CONFIG', config), \
             mock.patch.object(scan, 'get', side_effect=fake_get), \
             mock.patch.object(scan, '_known_institution_url_should_skip', return_value=False), \
             mock.patch.object(scan, 'INSTITUTION_SEEN_FINGERPRINTS', set()), \
             mock.patch.object(scan, '_op_publications_catalogue_jobs', return_value=[]):
            jobs = scan._source_adapter_domain_jobs(src, dt.date(2026, 8, 1))
        urls = [job[0] for job in jobs]
        self.assertIn(pub, urls)
        self.assertNotIn('https://example.net/advertising/', urls)
        self.assertTrue(all(job[1] == src['name'] for job in jobs))

    def test_source_hubs_are_not_automatic_admission(self):
        source = (ROOT / 'scripts/scan_radar.py').read_text()
        start = source.index('def _discover_domain(')
        end = source.index('\ndef _primary_page_publication_date(', start)
        self.assertNotIn('build_item(', source[start:end])
        self.assertIn('adapter_jobs', source[start:end])
        self.assertIn('institution_url_score', source[start:end])
