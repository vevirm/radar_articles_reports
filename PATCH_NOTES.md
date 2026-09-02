# v17.19.32

- Full-repository upload hardening for scanner serialization.
- Correct `.github/workflows` still use one shared queue so Main and Historical never overlap and rescue rounds stay inside the owning cycle.
- Added a visible runtime fallback for GitHub web uploads that leave hidden workflow YAML unchanged: the later legacy scanner run exits cleanly before any source requests rather than overlapping the other scanner.
- The fallback also protects the short gap before a legacy separately-dispatched rescue round.
- Scanner research methodology, source rotation, admission logic, EU relevance, shock discovery and saved data are unchanged.
