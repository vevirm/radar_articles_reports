RADAR VISUAL REBUILD v25 — PRESENTATION ONLY

Upload location: repository ROOT (the main Code page).

1. Extract this ZIP.
2. On GitHub open the main radar_articles_reports Code page (repository root).
3. Choose Add file -> Upload files.
4. Drag EVERYTHING inside the extracted RADAR_VISUAL_REBUILD_V25 folder onto the upload page.
5. Commit directly to main.

There are fewer than 100 files. No .github folder is included.

This patch does NOT contain radar.json, radar_config.json, scanner scripts, scanner workflows,
historical data, tests, scan state, citation-snowball state, or admission/scoring code.

If GitHub starts a Radar scan because this is a push, the workflow's upload guard should treat
presentation-only uploads as deployment-only according to the repository's current workflow logic.
