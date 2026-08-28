from pathlib import Path
import json
import sys, types
import unittest

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules['feedparser'] = types.ModuleType('feedparser')

from scripts import scan_radar as scanner

ROOT = Path(__file__).resolve().parents[1]


class MethodAsSuchPrecisionTests(unittest.TestCase):
    def reject(self, title, abstract):
        ev = scanner.gate_scope(title, abstract, '', 2, source_kind='scholarly')
        self.assertFalse(ev['b_pass'], title)

    def test_rejects_domain_early_warning_and_method_use_from_current_state(self):
        cases = [
            ('Development of an Early-warning Method Incorporating Presupernova Neutrino Light Curves',
             'This study develops an early-warning method using presupernova neutrino light curves.'),
            ('Research on a Hybrid Prediction and Early Warning Model for Concrete Bridge Settlement Based on VMD–TCN–BiLSTM',
             'This study develops a settlement prediction and dynamic early warning framework for concrete bridges.'),
            ('Research on Enterprise Financial Risk Early Warning and Control Based on Big Data Analysis',
             'The paper develops an XGBoost financial-risk early warning model for firms.'),
            ('Design and Development of an Earthquake Early Warning System Based on IoT Using the Fuzzy Tsukamoto Method',
             'The paper develops an IoT earthquake early warning system for tall buildings.'),
            ('Developing and validating a digital literacy assessment framework for pre-service physical education teachers: a Delphi-AHP study',
             'The Delphi method was employed to validate an assessment framework for teachers.'),
            ('Morphological analysis in the context of grammatical homonymy research',
             'The article develops classroom assignments using morphological analysis of grammatical homonyms.'),
        ]
        for title, abstract in cases:
            self.reject(title, abstract)

    def test_rejects_domain_specific_futures_method_without_policy_ri_destination(self):
        ev = scanner.gate_scope(
            'Forest pests on the move: Adapting horizon scanning methodology to assess climate-driven range expansion',
            'We extend horizon scanning beyond its original scope by adapting the horizon-scanning framework to a new class of emerging risks.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['b_pass'])

    def test_accepts_new_delphi_only_when_it_is_a_foresight_method(self):
        ev = scanner.gate_scope(
            'A new Delphi methodology for R&I foresight',
            'We develop a Delphi method for research and innovation foresight, including weak-signal elicitation and bias controls.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['b_pass'])


class UIClarityTests(unittest.TestCase):
    def test_main_radar_is_message_first_and_bibliography_after(self):
        page = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertIn('function complete120', page)
        self.assertIn('function repairLetterSpacing', page)
        self.assertIn('function hasLetterSpacing', page)
        self.assertIn("m=>m.replace(/\\s+/g,'')", page)
        self.assertIn('function semanticMessage', page)
        self.assertNotIn("return cut.replace(/[,:;\\-–—]+$/,'')+'…'", page)
        self.assertIn('function coreMessage', page)
        self.assertIn('function claim80', page)
        self.assertNotIn('`This says that ${c}`', page)
        self.assertIn("return c||'Concise source claim unavailable'", page)
        self.assertNotIn('<strong>From:</strong>', page)
        self.assertIn('<strong>Why it matters:</strong>', page)
        self.assertIn('biblio-label', page)
        self.assertIn('Bibliography', page)

    def test_risks_opportunities_has_back_button_and_plain_language(self):
        page = (ROOT / 'priorities' / 'index.html').read_text(encoding='utf-8')
        js = (ROOT / 'priorities' / 'priorities.js').read_text(encoding='utf-8')
        self.assertIn('aria-label="Primary site sections"', page)
        self.assertIn('Main radar', page)
        self.assertIn('Matrix', page)
        self.assertIn('plain language', page)
        self.assertIn('simplePriorityText', js)
        self.assertIn('more dependent and less competitive', js)


if __name__ == '__main__':
    unittest.main()
