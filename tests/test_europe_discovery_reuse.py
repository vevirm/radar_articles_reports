"""Offline regressions for safe, budget-neutral European publication discovery."""
from __future__ import annotations
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
MODULES={}
for key in ('scan_radar','scan_radar_deep_a'):
    spec=importlib.util.spec_from_file_location('test_europe_'+key, ROOT/'scripts'/f'{key}.py')
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    MODULES[key]=mod


class _Response:
    status_code=200
    def __init__(self, body, url='https://example.org'):
        self.text=body
        self.content=body.encode()
        self.url=url
        self.headers={'content-type':'application/rss+xml' if '<rss' in body else 'text/html'}
    def __bool__(self): return True


class EuropeDiscoveryReuseTests(unittest.TestCase):
    def test_configs_enrich_existing_sources_without_downgrading(self):
        cfg=json.loads((ROOT/'radar_config.json').read_text())
        src={x['domain']:x for x in cfg['institution_sources']}
        for domain in ('cordis.europa.eu','epo.org','consilium.europa.eu','oecd.org','chathamhouse.org'):
            self.assertIn(domain,src)
        self.assertEqual(src['cordis.europa.eu']['tier'],1)
        self.assertEqual(src['epo.org']['tier'],1)
        self.assertEqual(len(src['consilium.europa.eu']['feeds']),2)
        self.assertIn('https://www.epo.org/en/news-events/news/feed',src['epo.org']['feeds'])
        for domain in ('cordis.europa.eu','epo.org','chathamhouse.org'):
            self.assertIn(domain,cfg['institution_source_adapters'])
        self.assertEqual(cfg['institution_source_adapter_pages_per_domain'],36)
        self.assertEqual(cfg['institution_source_adapter_max_hub_fetches'],10)

    def test_empty_real_rss_healthy_but_html_block_fails(self):
        valid=types.SimpleNamespace(entries=[],bozo=False)
        for scan in MODULES.values():
            self.assertTrue(scan._valid_institution_feed_response(b'<rss version="2.0"><channel/></rss>',valid))
            self.assertFalse(scan._valid_institution_feed_response(b'<html><title>blocked</title></html>',valid,'text/html'))
            self.assertFalse(scan._valid_institution_feed_response(b'<html><title>blocked</title></html>',types.SimpleNamespace(entries=[1]),'text/html'))
            self.assertFalse(scan._valid_institution_feed_response(b'<broken',types.SimpleNamespace(entries=[],bozo=True)))

    def test_live_html_error_does_not_pass_as_quiet_feed(self):
        for scan in MODULES.values():
            source={'domain':'test.example','name':'Test','tier':1,'feeds':['https://test.example/rss.xml']}
            with patch.object(scan,'get',return_value=_Response('<html>access denied</html>')), \
                 patch.object(scan,'discover_sitemaps',return_value=[]), \
                 patch.object(scan,'_source_adapter_domain_jobs',return_value=[]), \
                 patch.object(scan,'_rule_fix_fallback_domain_jobs',return_value=[]):
                jobs, warning=scan._discover_domain(source,dt.date.today()-dt.timedelta(days=7))
            self.assertEqual(jobs,[])
            self.assertIn('No usable sitemap',warning)

    def test_valid_empty_feed_prevents_false_failure(self):
        for scan in MODULES.values():
            source={'domain':'test.example','name':'Test','tier':1,'feeds':['https://test.example/rss.xml']}
            with patch.object(scan,'get',return_value=_Response('<rss version="2.0"><channel/></rss>')), \
                 patch.object(scan,'discover_sitemaps',return_value=[]), \
                 patch.object(scan,'_source_adapter_domain_jobs',return_value=[]):
                jobs, warning=scan._discover_domain(source,dt.date.today()-dt.timedelta(days=7))
            self.assertEqual(jobs,[])
            self.assertIsNone(warning)

    def test_valid_empty_publication_hub_prevents_false_transport_failure(self):
        for scan in MODULES.values():
            source={'domain':'test.example','name':'Test','tier':1}
            listing=_Response('<html><body><main>No new publications</main></body></html>',
                              url='https://test.example/reports')
            with patch.dict(scan.CONFIG['institution_source_adapters'],
                            {'test.example': {'hub_paths': ['/reports'], 'path_hints': ['report']}}), \
                 patch.object(scan,'get',return_value=listing), \
                 patch.object(scan,'discover_sitemaps',return_value=[]):
                jobs, warning=scan._discover_domain(source,dt.date.today()-dt.timedelta(days=7))
            self.assertEqual(jobs,[])
            self.assertIsNone(warning)

    def test_visible_abstract_from_same_doi_response(self):
        paragraph=' '.join(['This study evaluates European research infrastructure innovation policy and cross-border collaboration.']*8)
        html=f'<html><body><section id="abstract">{paragraph}</section></body></html>'
        for scan in MODULES.values():
            r=_Response(html)
            r.headers['content-type']='text/html'
            with patch.object(scan.SESSION,'get',return_value=r) as request, patch.object(scan,'deadline_reached',return_value=False):
                abstract=scan.doi_landing_abstract('10.1234/example')
            self.assertIn('cross-border collaboration',abstract)
            self.assertEqual(request.call_count,1)

    def test_stale_or_whole_article_does_not_become_abstract(self):
        words=' '.join(['word']*1600)
        for scan in MODULES.values():
            r=_Response(f'<section id="abstract">{words}</section>')
            r.headers['content-type']='text/html'
            with patch.object(scan.SESSION,'get',return_value=r), patch.object(scan,'deadline_reached',return_value=False):
                self.assertEqual(scan.doi_landing_abstract('10.1234/example'),'')

    def test_audit_separates_config_from_observation(self):
        spec=importlib.util.spec_from_file_location('test_source_coverage_audit',ROOT/'scripts/audit_source_coverage.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report=module.audit({'institution_sources':[{'name':'Example','domain':'example.org','tier':1}]}, {'scan_state':{'institution_cursor':4}})
        self.assertEqual(report['configured_institutional_domains'],1)
        self.assertEqual(report['domains_reported_in_latest_scan'],0)
        self.assertEqual(report['domains']['example.org']['latest_status'],'never_reported')


if __name__=='__main__': unittest.main()
