# Stage 6 hotfix — retrace support identity compatibility

The claim-native detector stores support references using the same canonical evidence identity spelling as `scripts/downstream_retrace.py` (`url:https://...` when a URL exists).

This fixes the quick-scan regression failure where live claim candidates used internal `link:https://...` record keys that the downstream integrity checker could not resolve, producing orphan-reference failures before the scan itself ran.

No scanner, Deep Scan, public reader, publication selection, or protected core file is changed.
