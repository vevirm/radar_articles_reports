# Visual rebuild v26

Presentation-only rebuild. No scanner, data, config, workflow, scan-state or test files are included in the upload package.

## What changed

- `radar.css` — one shared visual system for all pages: black/white base, restrained semantic red, serif reading face, bold sans navigation, three weights only, spacing hierarchy, matrix/trend/tree treatments and responsive rules.
- `site-shell.js` — one shared persistent sidebar/menu for all reader pages, with grouped navigation and active-page red block.
- `radar-shell.js` — loads the shared shell without changing the protected Radar application block; also suppresses generic source-title artefacts such as “Download” when a real finding sentence is available.
- `index.html` — professional home menu, fact strip and word-cloud composition.
- `radar/index.html` — presentation shell and dense evidence-row structure; protected application logic retained.
- `read/index.html` — rebuilt three-column labelled box trees with measured grey connectors.
- `frontier/index.html`, `frontier/quick/index.html` — contained Matrix with solid evidence cells and deliberate horizontal scrolling when needed.
- `trends/index.html` — black trend / red counter-trend evidence-pull bar and obviousness ordering.
- `phenomena/index.html`, `priorities/index.html`, `shocks/index.html` — sparse conclusion layouts, evidence counts and obviousness ordering.
- `historical/index.html`, `history/index.html` — Earlier Findings presentation, consistent dates and incremental loading.
- `literature/index.html`, `briefing/index.html`, `glossary/index.html`, `stuff/index.html`, `explore/index.html`, `shocks/variants.html` — unified typography, spacing, menu and colour treatment.

## Verification

- `!important` in `radar.css`: **0**
- inline `<style>` blocks across HTML: **0**
- inline `style=` attributes across HTML: **0**
- HTML pages checked: **17**
- pages linking `radar.css?v=26`: **17**
- other loaded stylesheets: **0**
- CSS font weights: **400, 600, 800**
- CSS colours: **#111111, #6b6b6b, #c40018, #d9d9d9, #ffffff**
- CSS font sizes below 14px: **0**
- non-zero letter spacing declarations: **0**
- full regression suite: **168 tests, 0 failures (66 skipped)**

The legacy CSS files may remain physically in the repository because a basic GitHub upload cannot delete files. None of the 17 pages loads them; they are inert.
