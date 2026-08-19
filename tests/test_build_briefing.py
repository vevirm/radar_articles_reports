import unittest

from scripts.build_briefing import make_briefing, render_page


class BriefingTests(unittest.TestCase):
    def sample_radar(self):
        return {
            "last_updated": "2026-08-19T08:00Z",
            "scan_health": "ok",
            "strand_a": [
                {
                    "title": "Research security and European critical technology partnerships",
                    "summary": "The report examines EU research security, dual-use screening and international partnerships in critical technologies, with specific implications for Horizon Europe.",
                    "relevance_note": "Direct EU relevance through Horizon Europe and research-security policy.",
                    "source": "Example Institute",
                    "date": "2026-08-18",
                    "link": "https://example.org/report",
                    "new_this_scan": True,
                },
                {
                    "title": "European semiconductor dependencies and innovation capacity",
                    "summary": "The study maps semiconductor supply-chain dependencies and the industrial capacity needed to reduce strategic vulnerability in Europe.",
                    "source": "Example Journal",
                    "date": "2026-08-10",
                    "link": "https://example.org/chips",
                    "new_this_scan": False,
                },
            ],
            "strand_b": [
                {
                    "title": "Evaluating horizon scanning for technology policy",
                    "summary": "The paper compares horizon scanning, scenario design, bias controls and evaluation methods for public technology policy.",
                    "source": "Methods Review",
                    "date": "2026-08-17",
                    "link": "https://example.org/foresight",
                    "new_this_scan": True,
                }
            ],
            "strand_c": [
                {
                    "headline": "EU announces new screening guidance for sensitive research cooperation",
                    "signal_note": "The guidance introduces a new screening step for sensitive international research cooperation. This instantiates the research-security anchor with a current policy development.",
                    "anchor": "Research security and European critical technology partnerships (Strand A)",
                    "signal_type": "instantiates",
                    "source": "Example Newswire",
                    "date": "2026-08-19T06:00Z",
                    "link": "https://example.org/news",
                }
            ],
        }

    def test_briefing_contains_specific_developments_and_action_fields(self):
        briefing = make_briefing(self.sample_radar())
        self.assertTrue(briefing["issues"])
        self.assertTrue(briefing["priority_developments"])
        self.assertIn("strongest evidence concentrations", briefing["big_picture"])

        security = next(x for x in briefing["issues"] if x["name"] == "Research security, economic security & dual use")
        self.assertGreaterEqual(len(security["evidence"]), 2)
        self.assertEqual(len(security["implications"]), 3)
        self.assertEqual(len(security["watch"]), 3)
        self.assertIn("current weak signal", security["current_read"])
        notes = " ".join(e["note"] for e in security["evidence"])
        self.assertIn("screening step", notes)

    def test_render_page_exposes_detail_without_hiding_big_picture(self):
        page = render_page(make_briefing(self.sample_radar()))
        self.assertIn("Where the radar is concentrating now", page)
        self.assertIn("Priority developments in the current radar", page)
        self.assertIn("Specific developments in the admitted radar", page)
        self.assertIn("Implications for R&I decisions", page)
        self.assertIn("What to watch next", page)
        self.assertIn("Decision question", page)
        self.assertIn("EU announces new screening guidance", page)


if __name__ == "__main__":
    unittest.main()
