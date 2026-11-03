import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import global_blind_spots_auto as x

LONG = 'International research investment in institutional laboratories rose steadily over multiple years and changed access to the research infrastructure. ' * 12


def row(i, region='China', theme='Research funding, institutions and talent', url=None):
    return dict(document_key=f'key{i}', candidate_id=f'cand{i}', region=region, theme=theme,
                title=f'National research investment and laboratories {i} overview',
                url=url or ('https://www.oecd.org/en/data/testing-' + str(i)),
                source_kind='institutional_statistics', main_radar_links=[], provenance='curated_high_quality_source')


def document(url, unique):
    return {'url': url, 'title': unique, 'text': LONG + unique,
            'sha256': unique, 'length': len(LONG)}


class TestAutomaticDeepScan(unittest.TestCase):
    def test_source_gate_denies_untrusted_domains_and_bad_schemes(self):
        self.assertFalse(x.host_allowed('https://example.net/source'))
        self.assertFalse(x.host_allowed('http://nature.com/article'))
        self.assertFalse(x.host_allowed('https://nature.com.evil.net/article'))
        self.assertTrue(x.host_allowed('https://www.nature.com/articles/test'))

    def test_read_source_and_block_redirects(self):
        with self.assertRaises(ValueError):
            x.download_document('https://www.nature.com/a', lambda u: (b'x'*1000, 'text/html', 'https://evil.net/x'))
        html = '<html><title>Report</title><article>' + '<p>'+LONG+'</p>' + '</article></html>'
        d = x.download_document('https://www.nature.com/a', lambda u: (html.encode(), 'text/html', u))
        self.assertGreater(d['length'], 850)
        self.assertIn('research investment', d['text'])

    def test_verbatim_quotes_required(self):
        a = row(1, url='https://www.nature.com/a')
        b = row(2, url='https://www.oecd.org/b')
        p = document(a['url'], 'primary')
        s = document(b['url'], 'secondary')
        q = LONG[:92]
        ans = {'decision': 'KEEP', 'finding': 'A specific R&I development was independently documented across recent international research studies.',
               'what_changed': 'Research laboratories received sustained additional institutional support.',
               'why_it_matters': 'Changes in international research financing affect research talent and competitive capacity.',
               'limitations': 'The source text does not establish a causal relationship or a countrywide effect.',
               'radar_comparison': 'The global context extends the EU-focused Radar discussion of institutional research funding.',
               'primary_quote': q, 'corroboration_quote': q, 'overlap': 'not_identified', 'confidence': 'medium'}
        self.assertTrue(x.verify_answer(ans, a, b, p, s)[0])
        ans['primary_quote'] = 'This is a fake quote that does not appear in the actual primary source text document.'
        self.assertFalse(x.verify_answer(ans, a, b, p, s)[0])

    def test_existing_radar_cannot_be_claimed_new(self):
        a = row(1)
        a['main_radar_links'] = [{'title': 'Matching report', 'url': a['url']}]
        b = row(2, url='https://www.wipo.int/a')
        p, s = document(a['url'], 'p'), document(b['url'], 's')
        ans = {'decision': 'KEEP', 'finding': 'A specific R&I development was independently documented across recent international research studies.',
               'what_changed': 'Research laboratories received sustained additional institutional support.',
               'why_it_matters': 'Changes in international research financing affect research talent and competitive capacity.',
               'limitations': 'The source text does not establish a causal relationship or a countrywide effect.',
               'radar_comparison': 'Earlier Radar report is directly connected to the same finding in the primary source.',
               'primary_quote': LONG[:92], 'corroboration_quote': LONG[:92],
               'overlap': 'not_identified', 'confidence': 'high'}
        self.assertFalse(x.verify_answer(ans, a, b, p, s)[0])

    def test_pairing_requires_different_sources_and_shared_issue(self):
        a = row(1, url='https://www.nature.com/a')
        b = row(2, url='https://www.oecd.org/b')
        c = row(3, url='https://www.nature.com/c')
        docs = {r['candidate_id']: document(r['url'], r['candidate_id']) for r in [a,b,c]}
        selected = x.pick_pairs([a,b,c], docs, 6)
        self.assertTrue(selected)
        self.assertTrue(all(x.family(docs[p['candidate_id']]['url']) != x.family(docs[q['candidate_id']]['url']) for p,q in selected))

    def test_bare_model_error_never_promotes_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)/'deep'
            base = Path(tmp)/'global'
            rad = Path(tmp)/'radar.json'
            rad.write_text('{}')
            records = [row(1, url='https://www.nature.com/a'), row(2, url='https://www.oecd.org/b')]
            def fetch(u): return document(u, 'x' + u)
            with patch.object(x, 'auto_candidates', return_value=(records, {'selected': 2})), \
                 patch.dict(os.environ, {'GITHUB_MODELS_TOKEN': 'fake'}, clear=False):
                res = x.run(base=base, deep=dest, radar_file=rad, max_docs=2, max_pairs=2,
                            get_document=fetch, infer=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('No access')), pause=0)
            self.assertEqual(res['items'], [])
            self.assertTrue((dest/'AUTO_FINDINGS.md').exists())
            self.assertIn('No findings passed', (dest/'AUTO_FINDINGS.md').read_text())


if __name__ == '__main__':
    unittest.main()
