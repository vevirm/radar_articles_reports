import unittest

from scripts.build_briefing import make_briefing, render_page


class BriefingTests(unittest.TestCase):
    def sample_radar(self):
        return {
            "last_updated": "2026-08-19T08:00Z",
            "scan_health": "ok",
            "strand_a": [
                {
                    "title": "EU critical raw materials partnerships and rare-earth refining",
                    "summary": "The report examines critical raw materials partnerships, rare-earth refining capacity and European supply-chain exposure.",
                    "relevance_note": "Direct relevance to EU strategic dependencies and industrial resilience.",
                    "source": "Example Institute",
                    "date": "2026-08-18",
                    "link": "https://example.org/materials",
                    "new_this_scan": True,
                },
                {
                    "title": "European AI factories expand sovereign compute capacity",
                    "summary": "The study reviews AI factories, GPU access and European compute capacity for artificial intelligence research and deployment.",
                    "source": "Example Journal",
                    "date": "2026-08-10",
                    "link": "https://example.org/ai",
                    "new_this_scan": False,
                },
                {
                    "title": "Horizon Europe research-security guidance for universities",
                    "summary": "The paper covers Horizon Europe, research security and university collaboration rules.",
                    "source": "Research Policy Centre",
                    "date": "2026-08-11",
                    "link": "https://example.org/research",
                    "new_this_scan": False,
                },
            ],
            "strand_b": [
                {
                    "title": "Evaluating horizon scanning for technology policy",
                    "summary": "The paper compares horizon scanning, scenarios, bias controls and evaluation methods.",
                    "source": "Methods Review",
                    "date": "2026-08-17",
                    "link": "https://example.org/foresight",
                    "new_this_scan": True,
                }
            ],
            "strand_c": [
                {
                    "headline": "EU announces new export controls on advanced semiconductors",
                    "signal_note": "The measure changes export-control conditions for advanced semiconductor equipment.",
                    "anchor": "European semiconductor dependencies (Strand A)",
                    "signal_type": "instantiates",
                    "source": "Example Newswire",
                    "date": "2026-08-19T06:00Z",
                    "link": "https://example.org/news",
                }
            ],
        }

    def test_items_are_grouped_under_subject_headings_once(self):
        briefing = make_briefing(self.sample_radar())
        names = [x["name"] for x in briefing["topics"]]
        self.assertIn("Raw materials & supply chains", names)
        self.assertIn("AI & compute", names)
        self.assertIn("Research & science", names)
        self.assertIn("Foresight & methods", names)

        all_titles = [item["title"] for topic in briefing["topics"] for item in topic["items"]]
        self.assertEqual(len(all_titles), 5)
        self.assertEqual(len(all_titles), len(set(all_titles)))

    def test_raw_material_item_uses_radar_wording(self):
        briefing = make_briefing(self.sample_radar())
        topic = next(x for x in briefing["topics"] if x["name"] == "Raw materials & supply chains")
        item = topic["items"][0]
        self.assertIn("rare-earth refining capacity", item["note"])
        self.assertEqual(item["source"], "Example Institute")
        self.assertEqual(item["strand"], "A")

    def test_render_page_is_topic_digest_not_analysis_briefing(self):
        page = render_page(make_briefing(self.sample_radar()))
        self.assertIn("The radar, sorted by subject", page)
        self.assertIn("Raw materials &amp; supply chains", page)
        self.assertIn("AI &amp; compute", page)
        self.assertIn("Research &amp; science", page)
        self.assertIn("EU critical raw materials partnerships", page)
        self.assertNotIn("Decision question", page)
        self.assertNotIn("Implications for R&amp;I decisions", page)
        self.assertNotIn("What to watch next", page)


if __name__ == "__main__":
    unittest.main()
