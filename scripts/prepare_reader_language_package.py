#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from reader_language_common import ROOT, collect_candidates, lint_reasons, load_approved

INSTRUCTIONS = r'''# RADAR Reader Language review

You are reviewing **presentation wording only** for a research-and-innovation geopolitics website.
The analytical system has already decided what the text means. Your job is to make that meaning
clear to an intelligent general reader without changing it.

## Your output

Return **one file named `reader_language_results.json`**. Use the provided template and keep the
schema, package_id, item ids, source text and source_sha256 values unchanged.

Each item includes `display_text`: that is the wording a reader is expected to see. Review that wording, but keep the `display_text`, `source` and fingerprint fields unchanged in the returned JSON. If you choose REWRITE, put the new wording only in `replacement`.

For every item choose exactly one decision:

- `KEEP` — the wording is already clear, natural and suitable.
- `REWRITE` — supply a clearer `replacement`.

Do not skip items. KEEP is a good and common answer. Do not rewrite merely to sound different.

## Style contract

- Use plain, natural English for an intelligent non-specialist.
- Prefer concrete actors and verbs over strings of abstract nouns.
- Keep sentences fairly short when that can be done without losing meaning.
- A light, slightly playful touch is welcome in headings or short labels when it fits. Do not joke
  about serious subjects and do not force wit into every item.
- Avoid bureaucratic, academic and consultancy-style phrasing.
- Do not explain the website's internal machinery in normal reader prose. Avoid phrases about
  candidates, qualifying records, reasoning roles, retained evidence, inference engines, scoring,
  denial/falsifier checks, or how a conclusion was computed. State the substantive point instead.
- If a specialist term is genuinely necessary, make its meaning clear from the sentence.

## Meaning must not move

You MUST preserve the substantive claim exactly:

- do not add facts, examples, actors, causes or consequences that are not already in the source;
- do not remove a material qualification;
- do not change direction (increase/decrease, opening/closing, risk/opportunity, etc.);
- do not change certainty or time horizon;
- do not change names, dates, numbers, percentages, currencies or counts;
- do not turn correlation into causation;
- do not strengthen a possibility into a fact or weaken a fact into a possibility.

If a clean rewrite would require guessing what the author meant, choose KEEP.

## Important boundaries

These items come only from approved reader-facing analytical pages. Main Radar evidence, Earlier
Findings evidence, source records, Deep Scan decisions and Excel/Stuff are outside this language
layer. Never propose edits to those systems.

## Good examples

Heavy: "Partnership, association or cross-border cooperation is widening around research security."
Clearer: "Cross-border cooperation on research security is increasing."

Heavy: "Forward-looking pathways to loss that are supported by the source."
Clearer: "Ways current developments could create problems for European research and innovation."

But if the original is already clear, return KEEP.
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--output-dir', default='reader_language_out')
    ap.add_argument('--max-items', type=int, default=40)
    ap.add_argument('--mode', choices=('flagged', 'all-unreviewed'), default='flagged')
    args = ap.parse_args()
    if args.max_items < 1 or args.max_items > 120:
        raise SystemExit('--max-items must be between 1 and 120')

    out = ROOT / args.output_dir
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    approved = load_approved()
    reviewed = set(approved.get('items', {}).keys())
    queue = []
    for c in collect_candidates():
        if c['id'] in reviewed:
            continue
        review_text = c.get('display_text') or c['source']
        reasons = lint_reasons(review_text)
        if args.mode == 'flagged' and not reasons:
            continue
        queue.append({**c, 'reasons': reasons or ['new reader-facing text'], 'word_count': len(review_text.split())})

    # Put the strongest language warnings first; ties remain deterministic.
    queue.sort(key=lambda x: (-len(x['reasons']), -x['word_count'], x['source'].lower()))
    selected = queue[: args.max_items]
    package_stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    package_id = f"reader-language-{package_stamp}"

    items_doc = {
        'schema': 'radar-reader-language-package-v1',
        'package_id': package_id,
        'mode': args.mode,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'queue_total': len(queue),
        'package_count': len(selected),
        'items': selected,
    }
    results_doc = {
        'schema': 'radar-reader-language-results-v1',
        'package_id': package_id,
        'items': [
            {
                'id': x['id'],
                'source': x['source'],
                'display_text': x.get('display_text') or x['source'],
                'source_sha256': x['source_sha256'],
                'routes': x['routes'],
                'decision': 'KEEP',
                'replacement': '',
            }
            for x in selected
        ],
    }

    (out / 'START_HERE.txt').write_text(
        'Give this ZIP to the LLM you use manually and say:\n\n'
        'Process this RADAR Reader Language package strictly according to INSTRUCTIONS.md '
        'and return reader_language_results.json.\n\n'
        'When it comes back, upload reader_language_results.json to the repository folder '
        'reader_language_inbox and commit it to main.\n',
        encoding='utf-8',
    )
    (out / 'INSTRUCTIONS.md').write_text(INSTRUCTIONS, encoding='utf-8')
    (out / 'reader_language_items.json').write_text(json.dumps(items_doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'reader_language_results.json').write_text(json.dumps(results_doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'QUEUE_STATUS.txt').write_text(
        f"Unreviewed items eligible in this mode: {len(queue)}\n"
        f"Items in this package: {len(selected)}\n"
        f"Already-reviewed exact texts: {len(reviewed)}\n",
        encoding='utf-8',
    )

    zip_path = out / 'reader_language_package.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in ('START_HERE.txt', 'INSTRUCTIONS.md', 'reader_language_items.json', 'reader_language_results.json', 'QUEUE_STATUS.txt'):
            zf.write(out / name, arcname=name)

    print(f"Reader Language queue: {len(queue)} unreviewed item(s); packaged {len(selected)}.")
    print(zip_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
