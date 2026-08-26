# Scanning is paused

This repository snapshot is intentionally in **display-only / hold mode**.

- There are **no active GitHub Actions workflow files** under `.github/workflows/`.
- Uploading or committing this repository cannot start the radar scanner through GitHub Actions.
- The scanner implementation remains in `scripts/` and related project files.
- The previous workflow definition is preserved at `.github/disabled-workflows/radar-scan.yml.disabled`.

When scanning is wanted again, restore that workflow to `.github/workflows/radar-scan.yml` and choose the desired trigger (manual-only or scheduled).
