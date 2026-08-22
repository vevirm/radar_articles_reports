# R&I Geopolitics Radar — V17.5.9 R&I Foresight Method Transfer

This build preserves the existing radar corpus and scan state while hardening discovery.

- **No secrets or credentials are required.** The GitHub Actions workflow does not reference repository secrets.
- **OpenAlex runs keyless.** Queries are date-bounded, rotate into deeper pages, and stop immediately for the current run on HTTP 429/allowance exhaustion so other source families can continue.
- **Crossref discovery is hardened.** Keyword discovery uses relevance ranking, newest-result checking, deeper rotating offsets, an upper publication-date bound, and an additional future-date rejection at admission.
- **Strand B includes transferable R&I foresight methodology.** A substantive Delphi/horizon-scanning/scenario/weak-signal methodology paper about R&I, science/technology policy or the R&I system can qualify even without explicit EU/geopolitics wording; generic futures-method papers remain excluded.
- **Frontier rotation persists.** Sparse-cell query variants and specialist-source choices continue across scans rather than restarting from the first wording every run.
- **Diagnostics persist.** Source warning text is written into the generated radar state for later diagnosis.

Upload the repository files to GitHub and run the existing Radar Scan workflow. No GitHub Secrets setup is needed.
