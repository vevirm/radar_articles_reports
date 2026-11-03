import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import global_blind_spots as g


class BlindSpotTests(unittest.TestCase):
    def setUp(self):
        self.config = g.load_json(ROOT / 'global_blind_spots_config.json')
        self.config['_journal_allowlist'] = ['Research Policy']
        self.radar = {'strand_a': [{'title': 'Research funding and European science policy',
                                    'date': '2026-10-18', 'link': 'https://doi.org/10.1/a'}],
                      'strand_b': [{'title': 'Quantum technology and industrial policy', 'date': '2026-10-15'}],
                      'strand_c': [{'title': 'Research security and scientific collaboration', 'date': '2026-10-10'}]}
        self.anchors = g.extract_radar_anchors(self.radar, self.config)

    def test_global_coverage_and_anchors(self):
        self.assertTrue(all(self.anchors.get(t) for t in list(self.config['themes'])[:3]))
        self.assertGreaterEqual(len(self.config['regions']), 20)
        self.assertGreaterEqual(len(self.config['themes']), 6)
        self.assertEqual(len(g.existing_coverage(self.radar, self.config)),
                         len(self.config['regions']) * len(self.config['themes']))

    def test_never_leak_eu_region_without_non_eu_subject(self):
        x = self.oa('EU quantum computing research priorities', 'European Union research and innovation')
        self.assertIsNone(g.candidate_from_openalex(x, 'China', list(self.config['themes'])[1],
                                                     self.config, self.anchors[list(self.config['themes'])[1]], 'test'))

    def oa(self, title, abstract, journal='Research Policy', worktype='article'):
        return {'type': worktype, 'display_name': title, 'doi': 'https://doi.org/10.1234/example',
                'publication_date': '2026-10-15', 'primary_location': {'source': {'display_name': journal}},
                'abstract_inverted_index': {w: [n] for n, w in enumerate(abstract.split())}}

    def test_trusted_journal_and_region_issue_required(self):
        theme = list(self.config['themes'])[1]
        obj = self.oa('China quantum technology innovation policy',
                      'Chinese semiconductor research infrastructure requires investment')
        found = g.candidate_from_openalex(obj, 'China', theme, self.config, self.anchors[theme], 'query')
        self.assertIsNotNone(found)
        self.assertEqual(found['review_status'], 'needs_review')
        self.assertEqual(found['evidence_status'], 'candidate_not_peer_review_verified')
        self.assertIsNone(g.candidate_from_openalex(self.oa('China quantum policy',
                          'Chinese quantum industrial policy', 'Unknown Journal'), 'China', theme,
                          self.config, self.anchors[theme], 'query'))

    def test_official_claim_is_not_marked_independent(self):
        e = {'title': 'NIH announces research funding for university research',
             'description': 'American research funding for university research',
             'link': 'https://www.nih.gov/news-events/article'}
        feed = {'name': 'NIH', 'kind': 'official_primary', 'region_scope': 'United States',
                'allowed_domain': 'nih.gov'}
        found = g.classify_feed_entry(e, feed, self.config, self.anchors)
        self.assertGreater(len(found), 0)
        self.assertTrue(all(x['evidence_status'] == 'official_claim_unverified' for x in found))
        e['link'] = 'https://nih.gov.evil.example/fake'
        self.assertEqual(g.classify_feed_entry(e, feed, self.config, self.anchors), [])

    def test_rss_atom_and_rss_supported(self):
        rss = b'<rss><channel><item><title>China research funding</title><link>https://nature.com/article</link><description>Chinese R&amp;D</description></item></channel></rss>'
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>China research funding</title><link href="https://nature.com/a"/><summary>Chinese innovation</summary></entry></feed>'
        self.assertEqual(g.parse_feed(rss)[0]['title'], 'China research funding')
        self.assertEqual(g.parse_feed(atom)[0]['link'], 'https://nature.com/a')

    def test_live_queries_come_from_active_radar_issues(self):
        from datetime import datetime, timezone
        from collections import Counter
        urls = []
        def fake_get(url, timeout):
            urls.append(url)
            return b'{"results": []}'
        chosen = ['United States', 'China', 'Russia', 'Brazil']
        g.discover_openalex(self.config, self.anchors, Counter(),
                            datetime(2026, 11, 3, tzinfo=timezone.utc), http_get=fake_get,
                            selected_countries=chosen)
        self.assertEqual(len(urls), 4 * len(self.config['themes']) * 2)
        self.assertTrue(any('authorships.countries' in url for url in urls))
        self.assertTrue(any('United+States' in url for url in urls))

    def test_global_rotation_coverage_not_fixed_to_examples(self):
        groups = set(self.config['country_groups'].values())
        runs = [g.select_rotating_countries(self.config, i) for i in range(14)]
        self.assertTrue(all(len(x) == 12 for x in runs))
        self.assertTrue(all({self.config['country_groups'][country] for country in x} == groups for x in runs))
        self.assertEqual(set(country for x in runs for country in x), set(self.config['regions']))

    def test_affiliation_only_item_is_explicitly_labeled(self):
        theme = 'Technology leadership and industrial capacity'
        work = self.oa('Novel quantum computing architecture improves error correction',
                       'quantum research semiconductor hardware investigation')
        work['authorships'] = [{'countries': ['JP']}]
        found = g.candidate_from_openalex(work, 'Japan', theme, self.config, [], 'test', allow_affiliation=True)
        self.assertIsNotNone(found)
        self.assertEqual(found['geographic_evidence'], 'affiliation_only_not_country_policy_evidence')
        self.assertIsNone(g.candidate_from_openalex(work, 'Japan', theme, self.config, [], 'test'))

    def test_date_filter_drops_stale_feed_and_keeps_unknown_for_review(self):
        from datetime import datetime, timezone
        now = datetime(2026, 11, 3, tzinfo=timezone.utc)
        self.assertFalse(g.recent_feed_date('Mon, 01 Jan 2024 11:00:00 GMT', now, 365))
        self.assertTrue(g.recent_feed_date('2026-10-31T10:00:00Z', now, 365))
        self.assertTrue(g.recent_feed_date('', now, 365))

    def test_dedupe_is_by_url_region_theme_and_preserves_case(self):
        self.assertNotEqual(g.stable_key({'url': 'https://nature.com/CaseA', 'region': 'China', 'theme': 'x'}),
                            g.stable_key({'url': 'https://nature.com/casea', 'region': 'China', 'theme': 'x'}))
        self.assertFalse(g.valid_domain('http://nature.com/a', 'nature.com'))


if __name__ == '__main__':
    unittest.main()
