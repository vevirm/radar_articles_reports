# v21.15

Compatibility repair for GitHub browser full-repository uploads.

- Main schedule remains every four hours at minute 17, written as `17 */4 * * *`.
- Historical remains two hours offset: `17 2,6,10,14,18,22 * * *`.
- Both workflows retain the shared `ri-radar-research-scanners` concurrency queue.
- Restores `tests/test_security_and_state_guards.py` as a normal file so an older copy left by GitHub is overwritten.
- The schedule test accepts both equivalent four-hour cron spellings.
- Main workflow may safely discover `test_*.py`; current and leftover legacy tests pass together.
- No scanner, data, admission, historical accumulation, or page logic changed.
