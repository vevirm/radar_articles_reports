# Scanner security hardening

This package is designed to make accidental or malicious modification harder without changing the scanner's research logic.

## What the workflow now does

1. Checks out the private repository **without saving a GitHub write credential** in the working copy.
2. Uses exact, fixed GitHub Action commits rather than movable version labels.
3. Runs the scanner with its normal source/API access, but without a stored repository credential.
4. Stops before any save if the scanner changed a file other than `radar.json`.
5. Checks that `radar.json` is valid JSON and has not been catastrophically truncated or inflated.
6. Only after those checks, temporarily adds the GitHub credential needed to commit/push `radar.json`.
7. Removes that credential after the push step.
8. Publishes GitHub Pages in a separate job with separate permission.

## What this does not change

- inclusion/exclusion logic
- scoring or Matrix logic
- source lists or source evaluation
- fast-reader wording rules
- glossary/data structure
- the 6-hour scan schedule
- GitHub account ownership or login settings

## Recovery

Keep V17.13.16 as the known-working rollback package. If this hardened workflow ever fails because GitHub changes its platform behavior, replacing the workflow files with the V17.13.16 versions restores the previous run setup; it does not affect ownership of the repository or GitHub account access.

Two-factor authentication/passkeys remain the most important protection against somebody taking over the GitHub account itself. No workflow can reliably defend against an attacker who has full owner-level access to the repository.
