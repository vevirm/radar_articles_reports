# v17.19.29

## Simpler navigation + broader downstream interpretation

This release changes the **analytical/representation layer only**. The mature scanner/research engine is preserved byte-for-byte.

### Navigation and visual hierarchy
- The Main Radar is now unmistakably the primary page: **Radar** is the first, active navigation item and the large multi-card landing map has been removed.
- The Main Radar hero is reduced to a short title and one-line scope statement; live totals, search and evidence follow immediately.
- Reader navigation is simplified around: Radar, Read, Matrix, Risks & opportunities, External shocks, Historical, Sources and Stuff.
- Redundant top-navigation links to the Weak Signals anchor are removed; Weak Signals remains a first-class section inside the Main Radar.
- The large grey orientation block is gone. Surfaces stay white with black structure and red emphasis.
- Risks/Opportunities and External Shocks headers and explanatory copy are substantially shortened. Detailed methodology remains available only when requested.
- Risk/opportunity card headlines are capped to a concise reader length; long retained source passages are hidden behind **More info**.

### Risks and opportunities
- Repository interpretation now reads the full retained evidence context (source summary, core message, signal note, relevance/bridge evidence and structured EU/R&I/geopolitical evidence) rather than relying on a small set of exact phrases.
- Risk interpretation recognises more concrete structural pathways such as bottleneck access, research-career precarity/brain drain, concentrated foreign technology supply, investment dependence, export-control exposure and critical-material constraints.
- Opportunity interpretation recognises live instruments more broadly (calls, programmes, access schemes, partnerships, association mechanisms and funding instruments), but still requires an identifiable actor, instrument, gain and current/open window.
- Matrix placement remains completely excluded from risk/opportunity classification.
- On the current saved corpus the analytical layer finds **14 risks, 12 opportunities and 1 strict external shock** before page display limits/diversification.

### External shocks
- The existing 20-family shock taxonomy is retained.
- A family match still does not file a shock: discreteness, externality, realised EU R&I effect and speed must all pass.
- The methodology/taxonomy is collapsed by default to keep the page visually quiet.

### Validation
- Main regression suite: 178/178 passing.
- Historical regression suite: 19/19 passing.
- Scanner/config/phrase-rule/workflow files verified byte-for-byte unchanged from v17.19.28.
