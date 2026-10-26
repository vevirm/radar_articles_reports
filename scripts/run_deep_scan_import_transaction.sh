#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
git config user.name 'radar-deep-scan-importer'
git config user.email 'actions@github.com'
for attempt in 1 2 3 4 5; do
  echo "Deep Scan transactional import attempt $attempt/5"
  git fetch origin main
  git checkout -B deep-scan-transaction origin/main
  git clean -fd -- .deep_scan_combined.json deep_scan_workers
  echo '::group::Import and validate'
  set -euo pipefail
  python scripts/build_deep_scan_corpus.py --output .deep_scan_combined.json
  python scripts/import_deep_scan_results.py \
    --corpus .deep_scan_combined.json \
    --work-state deep_scan_work_state.json
  python scripts/promote_deep_a_candidates.py
  python scripts/check_reader_text.py
  python scripts/rebuild_active_radar.py --report migration-reports/latest-deep-scan-active-rebuild.json
  python scripts/check_active_corpus.py
  node scripts/generate_stuff_workbook.js
  # Existing raw evidence is immutable. The sole exception is append-only promotion
  # of authoritative Deep Scan KEEP results from the private Deep-A pool into A/B.
python3 - <<'PY'
import json, re, subprocess
from pathlib import Path
def clean(v):
    return re.sub(r'\s+', ' ', str(v or '')).strip()
def key(row):
    link=clean(row.get('link') or row.get('url'))
    if link: return 'link:'+link
    doi=clean(row.get('doi') or row.get('_doi')).lower()
    if doi:
        doi=re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi).removeprefix('doi:')
        return 'doi:'+doi
    rid=clean(row.get('id') or row.get('record_id') or row.get('fingerprint'))
    return 'id:'+rid if rid else ''
before=json.loads(subprocess.check_output(['git','show','HEAD:radar.json']).decode('utf-8'))
after=json.loads(Path('radar.json').read_text(encoding='utf-8'))
report_path=Path('migration-reports/latest-deep-a-promotion.json')
report=json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {'promoted': []}
allowed={(x.get('record_key'), x.get('target_strand')) for x in report.get('promoted',[]) if isinstance(x,dict)}
for collection in ('strand_c','frontier_evidence','ab_archive','signal_archive'):
    if before.get(collection) != after.get(collection):
        raise SystemExit(f'Deep Scan unexpectedly modified protected raw collection {collection}')
for collection, strand in (('strand_a','A'),('strand_b','B')):
    old=before.get(collection,[]) if isinstance(before.get(collection),list) else []
    new=after.get(collection,[]) if isinstance(after.get(collection),list) else []
    if new[:len(old)] != old:
        raise SystemExit(f'Deep Scan changed existing raw records in {collection}; only append-only promotion is allowed')
    extras=new[len(old):]
    extra_pairs={(key(x), strand) for x in extras if isinstance(x,dict)}
    expected={(k,t) for (k,t) in allowed if t == strand}
    if extra_pairs != expected:
        raise SystemExit(f'Unexpected Deep-A promotion set in {collection}: {extra_pairs!r} vs {expected!r}')
print(f'Raw evidence safety check passed; verified private promotions: {len(allowed)}.')
PY
  echo '::endgroup::'
  echo '::group::Refresh worker packages'
  set -euo pipefail
  rm -rf deep_scan_workers
  rm -f .deep_scan_combined.json
  python scripts/build_deep_scan_corpus.py --output .deep_scan_combined.json
  python scripts/prepare_deep_scan_package.py \
    --corpus .deep_scan_combined.json \
    --output-dir deep_scan_workers/worker-A \
    --lane A --lane-size 36 --batch-size 12 \
    --work-state deep_scan_work_state.json \
    --status-file DEEP_SCAN_STATUS.md --write-work-state
  python scripts/prepare_deep_scan_package.py \
    --corpus .deep_scan_combined.json \
    --output-dir deep_scan_workers/worker-B \
    --lane B --lane-size 36 --batch-size 12 \
    --work-state deep_scan_work_state.json \
    --status-file DEEP_SCAN_STATUS.md --write-work-state
  rm -f .deep_scan_combined.json
  unexpected="$(git diff --name-only -- . \
    ':!reader_text.json' ':!admission_state.json' ':!record_corrections.json' \
    ':!radar.json' ':!radar_active.json' ':!stuff/source_merit_ranking.xlsx' ':!stuff/main_radar_stuff.xlsx' \
    ':!migration-reports/latest-deep-scan-active-rebuild.json' \
    ':!migration-reports/latest-deep-a-promotion.json' ':!deep_scan_inbox/**' ':!deep_scan_review/**' \
    ':!deep_scan_work_state.json' ':!DEEP_SCAN_STATUS.md' \
    ':!deep_a_candidates.json' ':!deep_a_candidate_archive.json' || true)"
  if [[ -n "$unexpected" ]]; then
    echo '::error::Deep Scan import changed an unexpected tracked file. Refusing to save.'
    printf '%s\n' "$unexpected"
    exit 1
  fi
  echo '::endgroup::'
  git add \
    reader_text.json admission_state.json record_corrections.json \
    radar.json radar_active.json stuff/source_merit_ranking.xlsx stuff/main_radar_stuff.xlsx \
    migration-reports/latest-deep-scan-active-rebuild.json \
    migration-reports/latest-deep-a-promotion.json deep_scan_inbox deep_scan_review \
    deep_scan_work_state.json DEEP_SCAN_STATUS.md \
    deep_a_candidates.json deep_a_candidate_archive.json
  if git diff --cached --quiet; then
    echo 'No persistent Deep Scan state changes to publish.'
    exit 0
  fi
  git commit -m 'Deep Scan V2: verify evidence and refresh parallel queue'
  if git push origin HEAD:main; then
    echo 'Deep Scan state published successfully.'
    exit 0
  fi
  echo "::warning::Concurrent main update; rebuilding entire transaction on fresh main."
done
echo '::error::Deep Scan could not publish after 5 fresh-state attempts; inbox on main remains available for retry.'
exit 1
