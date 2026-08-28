# Validation V17.13.19

This release changes only the GitHub post-scan safety guard and version/documentation notes.

Expected behavior:
- ordinary scan output saves normally;
- substantial but plausible changes generate warnings and still save;
- clearly broken/extreme output stops before the GitHub write credential is introduced;
- scanner research logic and current radar data remain unchanged.
