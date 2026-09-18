from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import reader_language_common  # noqa: E402
from reader_language_common import collect_candidates, lint_reasons, numeric_tokens  # noqa: E402


class ReaderLanguagePipelineTests(unittest.TestCase):
    def test_reader_language_never_targets_protected_pages(self):
        candidates = collect_candidates()
        routes = {route for item in candidates for route in item.get('routes', [])}
        self.assertNotIn('radar', routes)
        self.assertNotIn('stuff', routes)
        self.assertNotIn('historical', routes)
        self.assertNotIn('literature', routes)

    def test_known_awkward_trend_sentence_is_flagged(self):
        text = 'Partnership, association or cross-border cooperation is widening around research security.'
        reasons = lint_reasons(text)
        self.assertIn('awkward phrase', reasons)
        self.assertIn('stacked abstractions', reasons)

        fixture = {
            'high_order_inference': {
                'candidates': [
                    {
                        'id': 'trend-reader-language-fixture',
                        'reader_summary': text,
                    }
                ],
                'publications': {
                    'trend': ['trend-reader-language-fixture']
                },
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / 'radar.json').write_text(
                json.dumps(fixture),
                encoding='utf-8',
            )

            with patch.object(reader_language_common, 'ROOT', root):
                by_source = {
                    x['source']: x
                    for x in collect_candidates()
                }

        self.assertIn(text, by_source)
        self.assertEqual(by_source[text]['routes'], ['trends'])


    def test_reader_language_prefers_live_active_reasoning_snapshot(self):
        active_text = 'Active snapshot wording shown to readers.'
        raw_text = 'Raw radar wording that is not currently shown.'
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            active = {
                'active_corpus_snapshot': True,
                'high_order_inference': {
                    'candidates': [{'id': 'live', 'reader_summary': active_text}],
                    'publications': {'risk': ['live']},
                },
            }
            raw = {
                'high_order_inference': {
                    'candidates': [{'id': 'raw', 'reader_summary': raw_text}],
                    'publications': {'risk': ['raw']},
                },
            }
            (root / 'radar_active.json').write_text(json.dumps(active), encoding='utf-8')
            (root / 'radar.json').write_text(json.dumps(raw), encoding='utf-8')
            with patch.object(reader_language_common, 'ROOT', root):
                sources = {x['source'] for x in collect_candidates()}
        self.assertIn(active_text, sources)
        self.assertNotIn(raw_text, sources)

    def test_reader_language_falls_back_to_raw_when_active_snapshot_is_not_authoritative(self):
        raw_text = 'Raw radar wording used when no active snapshot is available.'
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / 'radar_active.json').write_text(json.dumps({'active_corpus_snapshot': False}), encoding='utf-8')
            (root / 'radar.json').write_text(json.dumps({
                'high_order_inference': {
                    'candidates': [{'id': 'raw', 'reader_summary': raw_text}],
                    'publications': {'risk': ['raw']},
                },
            }), encoding='utf-8')
            with patch.object(reader_language_common, 'ROOT', root):
                sources = {x['source'] for x in collect_candidates()}
        self.assertIn(raw_text, sources)

    def test_numeric_guard_preserves_factual_numbers(self):
        a = 'The balance is 46–54 and 12 sources are represented.'
        b = 'The balance is 46–54, with 12 sources represented.'
        c = 'The balance is 45–55, with 12 sources represented.'
        self.assertEqual(numeric_tokens(a), numeric_tokens(b))
        self.assertNotEqual(numeric_tokens(a), numeric_tokens(c))

    def test_workflows_are_manual_and_no_ai_api_is_present(self):
        prepare = (ROOT / '.github/workflows/reader-language.yml').read_text(encoding='utf-8')
        imp = (ROOT / '.github/workflows/reader-language-import.yml').read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch', prepare)
        self.assertIn('reader_language_inbox/**', imp)
        self.assertNotIn('OPENAI_API_KEY', prepare + imp)
        self.assertNotIn('ANTHROPIC_API_KEY', prepare + imp)

    def test_approved_ledger_starts_as_presentation_only(self):
        data = json.loads((ROOT / 'reader_language/approved.json').read_text(encoding='utf-8'))
        self.assertEqual(data['schema'], 'radar-reader-language-approved-v1')
        self.assertIsInstance(data['items'], dict)


if __name__ == '__main__':
    unittest.main()
