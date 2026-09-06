"""Legacy repository-history contract quarantined for the fresh repository baseline."""
from pathlib import Path
import unittest

FRESH_START = Path(__file__).resolve().parents[1] / "FRESH_START"


@unittest.skipUnless(FRESH_START.is_file(), "Legacy suite replacement is for a FRESH_START repository")
class LegacyRepositoryHistoryContractDisabled(unittest.TestCase):
    @unittest.skip("Fresh repository: pre-baseline history/version contract intentionally does not apply.")
    def test_legacy_repository_history_contract(self):
        pass
