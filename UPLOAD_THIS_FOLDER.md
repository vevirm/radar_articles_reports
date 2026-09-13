# Upload this complete repository to GitHub

This is the full **Deep Scan V2 authoritative** repository, not a small patch.

The safest intention is to replace the repository files with this complete set while preserving the repository itself (GitHub Pages/settings/secrets/history remain on GitHub).

After upload, run **Actions → Radar V2 — Initialise, Validate & Prepare Deep Scan → Run workflow**. That validates the new active-corpus architecture, regenerates active outputs and gives you the first 12-work Deep Scan package.

Then the normal cycle is only:

**download package → give ZIP to browsing LLM → upload returned result to `deep_scan_inbox` → download the automatically generated next package**.

No AI API key is required. See `DEEP_SCAN_SETUP.md` for exact browser-level instructions.
