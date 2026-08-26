from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SiteArchitectureV17123Tests(unittest.TestCase):
    def pages(self):
        return {
            'main': (ROOT / 'index.html').read_text(encoding='utf-8'),
            'read': (ROOT / 'read' / 'index.html').read_text(encoding='utf-8'),
            'matrix': (ROOT / 'frontier' / 'index.html').read_text(encoding='utf-8'),
            'priorities': (ROOT / 'priorities' / 'index.html').read_text(encoding='utf-8'),
        }

    def test_four_primary_components_are_named_consistently(self):
        for name, page in self.pages().items():
            with self.subTest(page=name):
                self.assertIn('Read at least this', page)
                self.assertIn('Main radar', page)
                self.assertIn('Matrix', page)
                self.assertIn('Risks &amp; opportunities', page)
                self.assertIn('aria-label="Primary site sections"', page)

    def test_secondary_evidence_browser_is_not_a_primary_component(self):
        main = self.pages()['main']
        briefing = (ROOT / 'briefing' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Secondary evidence browser', main)
        self.assertIn('not a fifth component', briefing)
        nav = main.split('aria-label="Primary site sections"', 1)[1].split('</nav>', 1)[0]
        self.assertNotIn('briefing/', nav)
        self.assertNotIn('Latest weak signals', nav)

    def test_read_at_least_this_pattern_is_reused(self):
        pages = self.pages()
        self.assertIn('class="minimum-read"', pages['main'])
        self.assertIn('Read at least this · matrix', pages['matrix'])
        self.assertIn('Read at least this · decision view', pages['priorities'])
        self.assertIn('What the live radar adds right now', pages['read'])
        self.assertIn('RadarPriorities.buildPriorityView', pages['read'])

    def test_scanner_status_matches_manual_workflow(self):
        main = self.pages()['main']
        workflow = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        self.assertIn('Scanner · manual run only', main)
        self.assertNotIn('Automatic scan · every 12 hours', main)
        self.assertIn('workflow_dispatch', workflow)
        self.assertNotIn('schedule:', workflow)


if __name__ == '__main__':
    unittest.main()
