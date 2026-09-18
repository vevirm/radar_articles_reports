#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from reader_language_common import ROOT, clean, collect_candidates, fingerprint, load_approved, numeric_tokens

SCHEMA = 'radar-reader-language-results-v1'
UNCERTAINTY = re.compile(r"\b(?:may|might|could|potential(?:ly)?|possible|possibly|can sometimes)\b", re.I)
NEGATION = re.compile(r"\b(?:not|no|never|neither|nor|without|cannot|can't|won't|isn't|aren't|doesn't|don't|didn't)\b", re.I)
BANNED_NEW_META = re.compile(r"\b(?:inference engine|reasoning roles?|qualifying records?|denial/falsifier|cross-evidence inference)\b", re.I)


def load_result_documents(inbox: Path) -> list[tuple[Path, dict]]:
    docs: list[tuple[Path, dict]] = []
    for p in sorted(inbox.iterdir() if inbox.exists() else []):
        if p.name.startswith('.') or p.name.lower() == 'readme.md':
            continue
        if p.suffix.lower() == '.json':
            docs.append((p, json.loads(p.read_text(encoding='utf-8'))))
        elif p.suffix.lower() == '.zip':
            with zipfile.ZipFile(p) as zf:
                names = [n for n in zf.namelist() if n.rsplit('/', 1)[-1] == 'reader_language_results.json']
                if len(names) != 1:
                    raise ValueError(f'{p}: ZIP must contain exactly one reader_language_results.json')
                docs.append((p, json.loads(zf.read(names[0]).decode('utf-8'))))
        else:
            raise ValueError(f'{p}: unsupported inbox file; upload JSON or ZIP only')
    return docs


def validate_rewrite(source: str, replacement: str) -> None:
    source, replacement = clean(source), clean(replacement)
    if not replacement:
        raise ValueError('REWRITE requires a non-empty replacement')
    if replacement == source:
        raise ValueError('REWRITE replacement is identical to source; use KEEP')
    if '<' in replacement or '>' in replacement:
        raise ValueError('replacement must be plain text, not HTML')
    if len(replacement) > max(240, int(len(source) * 1.9) + 30):
        raise ValueError('replacement is unexpectedly longer than the source')
    if numeric_tokens(source) != numeric_tokens(replacement):
        raise ValueError('numbers/dates/counts changed; Reader Language may not alter factual numbers')
    # A meaning flip is adding or removing negation altogether.  Rephrasing that
    # uses a different number of negative words ("not yet ... not as proof") is fine.
    if bool(NEGATION.search(source)) != bool(NEGATION.search(replacement)):
        raise ValueError('negation added or removed; this could reverse the meaning')
    if UNCERTAINTY.search(source) and not UNCERTAINTY.search(replacement):
        raise ValueError('uncertainty was removed; may/might/could/potential language must remain qualified')
    if not UNCERTAINTY.search(source) and re.search(r"\b(?:may|might|could|potentially|possibly)\b", replacement, re.I):
        raise ValueError('new uncertainty was introduced')
    if BANNED_NEW_META.search(replacement) and not BANNED_NEW_META.search(source):
        raise ValueError('replacement introduced internal analysis machinery language')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--inbox', default='reader_language_inbox')
    ap.add_argument('--keep-files', action='store_true', help='do not delete processed inbox files')
    args = ap.parse_args()

    inbox = ROOT / args.inbox
    docs = load_result_documents(inbox)
    if not docs:
        print('Reader Language inbox is empty; nothing to import.')
        return 0

    current = {x['id']: x for x in collect_candidates()}
    approved = load_approved()
    approved.setdefault('schema', 'radar-reader-language-approved-v1')
    approved.setdefault('items', {})
    now = datetime.now(timezone.utc).isoformat()
    imported = kept = rewritten = 0

    # Structural problems (wrong schema, unreadable file) stop the run.  Individual
    # items are judged one by one: good items are saved, outdated or unsafe ones are
    # reported and simply come back in a later package.  One doubtful rewrite never
    # throws away a whole review.
    staged: list[tuple[Path, str, dict, dict]] = []
    skipped: list[tuple[str, str, str]] = []  # (id, reason, source excerpt)
    for path, doc in docs:
        if not isinstance(doc, dict) or doc.get('schema') != SCHEMA:
            raise ValueError(f'{path}: expected schema {SCHEMA}')
        package_id = clean(doc.get('package_id'))
        items = doc.get('items')
        if not package_id or not isinstance(items, list) or not items:
            raise ValueError(f'{path}: missing package_id or items')
        seen = set()
        for item in items:
            if not isinstance(item, dict):
                skipped.append(('?', 'item is not an object', ''))
                continue
            iid = clean(item.get('id'))
            excerpt = clean(item.get('source'))[:90]
            if not iid or iid in seen:
                skipped.append((iid or '?', 'missing or duplicate item id', excerpt))
                continue
            seen.add(iid)
            cur = current.get(iid)
            if not cur:
                skipped.append((iid, 'text is no longer on the site (the finding changed since the package was made)', excerpt))
                continue
            source = clean(item.get('source'))
            display_text = clean(item.get('display_text'))
            sha = clean(item.get('source_sha256'))
            if source != cur['source'] or sha != cur['source_sha256'] or fingerprint(source) != sha:
                skipped.append((iid, 'source text was edited in the returned file', excerpt))
                continue
            if display_text and display_text != clean(cur.get('display_text') or cur['source']):
                skipped.append((iid, 'display_text was edited; rewrites belong only in replacement', excerpt))
                continue
            decision = clean(item.get('decision')).upper()
            if decision not in {'KEEP', 'REWRITE'}:
                skipped.append((iid, 'decision must be KEEP or REWRITE', excerpt))
                continue
            replacement = clean(item.get('replacement'))
            if decision == 'KEEP':
                if replacement and replacement != source:
                    skipped.append((iid, 'KEEP must leave replacement empty', excerpt))
                    continue
            else:
                try:
                    validate_rewrite(source, replacement)
                except ValueError as exc:
                    skipped.append((iid, f'rewrite rejected: {exc}', excerpt))
                    continue
            staged.append((path, package_id, item, cur))

    for path, package_id, item, cur in staged:
        iid = cur['id']
        decision = clean(item.get('decision')).upper()
        replacement = clean(item.get('replacement')) if decision == 'REWRITE' else cur['source']
        approved['items'][iid] = {
            'id': iid,
            'source': cur['source'],
            'source_sha256': cur['source_sha256'],
            'replacement': replacement,
            'status': 'rewrite' if decision == 'REWRITE' else 'keep',
            'routes': cur['routes'],
            'origins': cur['origins'],
            'matches': cur.get('match_variants') or [cur['source']],
            'reviewed_at': now,
            'package_id': package_id,
        }
        imported += 1
        if decision == 'REWRITE': rewritten += 1
        else: kept += 1

    approved['updated_at'] = now
    out = ROOT / 'reader_language' / 'approved.json'
    out.write_text(json.dumps(approved, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    if not args.keep_files:
        for path, _ in docs:
            path.unlink(missing_ok=True)

    print(f'Imported {imported} Reader Language review item(s): {rewritten} rewrite(s), {kept} keep(s); {len(skipped)} not imported.')
    for iid, reason, excerpt in skipped:
        # GitHub shows ::warning:: lines as yellow notes on the run page.
        print(f'::warning title=Reader Language item not imported::{iid}: {reason} | "{excerpt}"')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        lines = [
            '## Reader Language import',
            '',
            f'- Saved: **{imported}** ({rewritten} rewrites, {kept} keeps)',
            f'- Not imported: **{len(skipped)}** (they will come back in a later package)',
            '',
        ]
        if skipped:
            lines += ['| Item | Why not imported | Text |', '|---|---|---|']
            lines += [f'| {iid} | {reason} | {excerpt.replace("|", "/")} |' for iid, reason, excerpt in skipped]
        with open(summary, 'a', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
