import sys
import types
import unittest

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules["feedparser"] = types.ModuleType("feedparser")

import scripts.scan_radar as sr


class V1765RotationRescueFixTests(unittest.TestCase):
    def test_no_warning_is_not_failure(self):
        self.assertFalse(sr.source_stage_failed([], "openalex"))

    def test_crossref_budget_warning_is_crossref_failure_only(self):
        warnings = ["Crossref scan budget reached; remaining queued scholarly queries skipped"]
        self.assertTrue(sr.source_stage_failed(warnings, "crossref"))
        self.assertFalse(sr.source_stage_failed(warnings, "openalex"))

    def test_fatal_openalex_warning_is_failure(self):
        self.assertTrue(sr.source_stage_failed(
            ["OpenAlex fatal stage error: RuntimeError: example"], "openalex"
        ))


if __name__ == "__main__":
    unittest.main()
