RADAR INSIGHTS — SIMPLE TOPIC BULLETS V7
========================================

The main radar and its scanner remain the source of truth.

INSIGHTS PAGE
-------------
Path: /briefing/

The page reads the existing ../radar.json directly in the browser.
There is no briefing.json and no separate briefing workflow.

For every admitted radar item the page:
1. deduplicates items that appear in more than one strand,
2. assigns the item to one primary topic,
3. extracts one concise substantive point,
4. shows that point as one bullet under the topic heading.

VISIBLE OUTPUT
--------------
Only:
- topic heading
- bullet
- bullet

There are no source labels, dates, Strand badges, evidence panels, topic counts,
"also touches" tags, relevance notes, or methodology boxes on the Insights page.

TOPICS
------
Raw materials
Research
AI
Semiconductors & quantum
Energy
Security & defence
Trade & industry
Digital & cyber
Space
Health & biotech
Talent & skills
International partnerships
Foresight
Other strategic R&I

SAFETY
------
radar.json is intentionally NOT included in this package.
Do not delete the existing live radar.json when uploading the repository.

The original scanner, scanner configuration, and radar-scan workflow are kept
unchanged. Insights only reads their output.
