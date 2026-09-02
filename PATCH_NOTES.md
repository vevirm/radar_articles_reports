# v17.19.31

## Serialized scanners + active external-shock recall

### Main / Historical queueing
- Main and Historical now share the workflow-level concurrency group `ri-research-scanners`.
- `queue: max` keeps waiting manual/scheduled runs queued rather than replacing an already pending scan.
- `cancel-in-progress: false` means neither scanner kills the other.
- Main automatic runs use the fixed four-hour UTC schedule: `00:17, 04:17, 08:17, 12:17, 16:17, 20:17`.
- Historical runs daily at `06:53 UTC`, between Main's 04:17 and 08:17 slots.
- Low-yield rescue scans no longer dispatch a second workflow run. The rescue is a second job inside the same workflow run, so the shared scanner lock remains held from the normal round through the rescue round.
- Rescue jobs explicitly check out the latest `main` after the normal round has committed, preserving cumulative scanner state.
- Manually running Main still starts Main only; Historical starts only from its own schedule/push/manual trigger and waits if Main is active.

### External shocks
- Active strategic-news discovery now includes the full shock-family range rather than primarily policy/trade shocks: natural disasters, extreme heat/heatwaves, pandemics, conflict, terrorism, financial/commodity/energy/food shocks, trade/supply-chain/currency disruptions, sanctions, migration surges, cyber/technology incidents, political instability, investment withdrawal, demand shocks and infrastructure failures.
- Strict shock filing still requires all core tests: discrete, external, realised effect and speed (plus a realised event marker).
- The source-text classifier now recognises exogenous event language such as heatwaves striking, earthquakes/floods/wildfires, cyberattacks, outages and forced research-facility shutdowns.
- A separate `external_shock_watch` stores short-lived **possible shocks** when trusted direct-EU R&I evidence identifies a recognised realised event but one strict filing test is still missing. These records are parked, not counted as filed shocks.
- External Shocks now shows `filed · possible` and a concise Possible shocks section.
- Possible-shock retention is 30 days.

### Validation
- Main regression suite: 185 tests passing.
- Historical regression suite: 19 tests passing.
- Workflow contract validates the shared lock, queueing, separated schedule and in-workflow rescue behavior.
