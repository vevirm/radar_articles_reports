#!/usr/bin/env python3
"""Build the lean deployable EU R&I radar release.

The release is intentionally allowlist-based. Historical audits, superseded
validation/changelog files, manual input documents, migration artifacts,
previews, and temporary build data are *not* copied merely because they exist
in the repository.

When a future page or scanner genuinely gains a new runtime dependency, add it
to the appropriate allowlist below and validate it before release.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files required by the public GitHub Pages site.
SITE_FILES = [
    "index.html",
    "source_merit.js",
    "radar.json",
    "robots.txt",
    "read/index.html",
    "read/issues.js",
    "glossary/index.html",
    "glossary/glossary.js",
    "briefing/index.html",
    "briefing/insights.js",
    "frontier/index.html",
    "frontier/quick/index.html",
    "frontier/frontier.js",
    "priorities/index.html",
    "priorities/priorities.js",
    "literature/index.html",
    "stuff/index.html",
    "stuff/source_merit_ranking.xlsx",
]

# Files required for the recurring scanner and its GitHub Actions schedule.
SCANNER_FILES = [
    ".github/workflows/radar-scan.yml",
    "radar_config.json",
    "priority_people.json",
    "requirements.txt",
    "scripts/scan_radar.py",
    "scripts/frontier_coverage.js",
]

# Tiny operational files retained to make future releases reproducible.
MAINTENANCE_FILES = [
    "VERSION.txt",
    "scripts/build_release.py",
]

RELEASE_FILES = SITE_FILES + SCANNER_FILES + MAINTENANCE_FILES


def _validate_json(path: Path) -> None:
    with path.open("r", encoding="utf-8") as fh:
        json.load(fh)


def validate(root: Path) -> None:
    missing = [rel for rel in RELEASE_FILES if not (root / rel).is_file()]
    if missing:
        raise SystemExit("Missing required release file(s):\n  " + "\n  ".join(missing))

    # Basic structural checks for the data/config files the scanner depends on.
    for rel in ("radar.json", "radar_config.json", "priority_people.json"):
        _validate_json(root / rel)

    radar = json.loads((root / "radar.json").read_text(encoding="utf-8"))
    for key in ("strand_a", "strand_b", "strand_c"):
        if not isinstance(radar.get(key), list):
            raise SystemExit(f"radar.json missing list field: {key}")

    # Guard the central local JS dependencies needed by both browser Matrix and scanner.
    bridge = (root / "scripts/frontier_coverage.js").read_text(encoding="utf-8")
    for required in ("../briefing/insights.js", "../frontier/frontier.js"):
        if required not in bridge:
            raise SystemExit(f"frontier_coverage.js no longer references expected dependency {required!r}; review release manifest")


def stage(root: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for rel in RELEASE_FILES:
        src = root / rel
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)


def make_zip(stage_dir: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in stage_dir.rglob("*") if p.is_file()):
            zf.write(path, path.relative_to(stage_dir).as_posix())


def main() -> int:
    ap = argparse.ArgumentParser(description="Build allowlist-only deployable radar release")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--stage", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()

    root = args.root.resolve()
    validate(root)
    version = (root / "VERSION.txt").read_text(encoding="utf-8").strip().replace(".", "_") or "UNVERSIONED"
    stage_dir = (args.stage or root.parent / f"radar_release_v{version}").resolve()
    output = (args.output or root.parent / f"RI_Geopolitics_Radar_V{version}_LEAN_RELEASE.zip").resolve()

    stage(root, stage_dir)
    validate(stage_dir)
    make_zip(stage_dir, output)
    print(f"Lean release: {output}")
    print(f"Included files: {len(RELEASE_FILES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
