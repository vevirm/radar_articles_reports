# v17.19.30

## Clearer Matrix + quieter reader presentation

This release changes the **analytical/editorial representation layer only**. The mature scanner/research engine, source rotation, admission logic, phrase rules and GitHub Actions workflows are unchanged.

### Matrix
- Quick Matrix points are rewritten as plain reader statements capped at **80 characters**.
- The Quick Matrix shows at most four distinct points per cell; repeated equivalent points are grouped and the remainder links to the Full Matrix.
- Long publication titles are no longer used as the default Matrix summary when a clearer evidence statement can be made.
- The Full Matrix removes the repeated **Why this cell** paragraph from every item.
- Full Matrix cards lead with the same concise point, followed only by compact source/date/type metadata; deeper placement methodology is collapsed below the Matrix.
- Matrix placement remains independent from Risks & Opportunities and External Shocks.

### Read + Main Radar
- **Read** is now a short issue view of established Radar evidence only. The separate weak-signal/Strand C module has been removed from this page.
- Main Radar Strand B is presented as **Ways to look ahead**, with a concise method insight and a practical **Use** line rather than dry source metadata first.
- Main Radar Strand C is presented as **Early moves to watch**, with a concise point and one short **Why watch** line; details stay behind More info.
- Reader navigation keeps **Radar** first and removes the old weak-signal navigation entry.

### Visual cleanup
- Reader surfaces use a restrained **white / black / red** system. Blue-toned and pastel interface colors were removed from reader HTML/CSS.
- Large gray orientation blocks and decorative reader panels remain removed.
- Reader assets use the v17.19.30 cache-buster and no-cache metadata so GitHub Pages does not keep serving old presentation assets after upload.

### Validation
- Main regression suite: **181/181 passing**.
- Historical regression suite: **19/19 passing**.
- Runtime regression checks every current Matrix point and fails if any exceeds 80 characters.
- JavaScript syntax, inline page scripts, Python compilation, release validation and ZIP integrity pass.
- `scan_radar.py`, scanner config, phrase rules and both workflow files are verified byte-for-byte unchanged from the uploaded v17.19.29 source of truth.
