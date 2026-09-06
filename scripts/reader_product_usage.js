#!/usr/bin/env node
'use strict';

// Small bridge used by the Python scanner's fresh-start corpus reset. It reads a
// cumulative radar snapshot from stdin and reports, per saved A/B item, how the
// browser reader products already use it: the shared reader ranking score, whether
// it backs a risk/opportunity on the Priorities page, whether it is evidence for an
// inferred or direct external-shock scenario, and whether it feeds a briefing
// insight or trend. The reset uses this only to rank importance; it never changes
// admission and it does not alter any page.
const fs = require('fs');

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  try {
    const data = raw.trim() ? JSON.parse(raw) : {};
    const usage = {};
    const norm = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    const keyOf = row => {
      if (!row || typeof row !== 'object') return '';
      const link = String(row.link || row.url || '').trim().toLowerCase().replace(/\/+$/, '');
      return link ? 'link:' + link : 'title:' + norm(row.title || row.headline);
    };
    const mark = (row, field, value) => {
      const k = keyOf(row);
      if (!k) return;
      usage[k] = usage[k] || {};
      if (value === undefined) usage[k][field] = (usage[k][field] || 0) + 1;
      else usage[k][field] = value;
    };

    let Rank = null;
    try { Rank = require('../reader_rank.js'); } catch (e) { Rank = null; }
    const rows = [].concat(data.strand_a || [], data.strand_b || []).filter(x => x && typeof x === 'object');
    if (Rank && typeof Rank.scoreFor === 'function') {
      for (const row of rows) {
        try {
          const s = Rank.scoreFor(row);
          const n = typeof s === 'number' ? s : (s && typeof s.total === 'number' ? s.total : Number(s));
          if (Number.isFinite(n)) mark(row, 'reader_rank', n);
        } catch (e) { /* ranking is optional */ }
      }
    }

    try {
      const P = require('../priorities/priorities.js');
      const v = P.buildPriorityView(data, { limit: 200 });
      for (const kind of ['risks', 'opportunities']) {
        for (const entry of (v[kind] || [])) mark(entry.raw || entry, 'priority_' + kind);
      }
    } catch (e) { /* optional */ }

    try {
      const S = require('../shocks/scenarios.js');
      const seen = new Set();
      const absorb = (list, field) => {
        for (const sc of (list || [])) {
          for (const ev of (sc.evidence || [])) {
            const row = ev && ev.row ? ev.row : ev;
            const k = keyOf(row);
            if (!k || seen.has(field + '|' + k + '|' + sc.id)) continue;
            seen.add(field + '|' + k + '|' + sc.id);
            mark(row, field);
          }
        }
      };
      const inferred = S.build(data);
      const direct = typeof S.buildDirect === 'function' ? S.buildDirect(data) : [];
      absorb(inferred, 'shock_scenario');
      absorb(direct, 'shock_direct');
      // The Shocks variants page shows for/against radar evidence per scenario; those
      // rows must also survive or a scenario loses its counter-evidence.
      try {
        const V = require('../shocks/variants.js');
        for (const sc of [].concat(direct, inferred)) {
          const v = V.build(data, sc.id);
          if (!v) continue;
          for (const ev of [].concat(v.forEvidence || [], v.againstEvidence || [])) {
            const row = ev && ev.row ? ev.row : ev;
            const k = keyOf(row);
            if (!k || seen.has('variant|' + k + '|' + sc.id)) continue;
            seen.add('variant|' + k + '|' + sc.id);
            mark(row, 'shock_variant');
          }
        }
      } catch (e) { /* optional */ }
    } catch (e) { /* optional */ }

    try {
      const Insights = require('../briefing/insights.js');
      global.RadarInsights = Insights;
      const groups = Insights.buildInsights(data) || [];
      for (const g of groups) for (const it of (g.items || [])) mark(it.raw || it.item || it, 'insight');
    } catch (e) { /* optional */ }

    try {
      const T = require('../trends/trends.js');
      const trends = T.build(data) || [];
      for (const t of trends) {
        for (const it of (t.items || t.rows || t.evidence || [])) mark(it.raw || it.row || it, 'trend');
      }
    } catch (e) { /* optional */ }

    process.stdout.write(JSON.stringify({ usage }));
  } catch (err) {
    process.stderr.write(String(err && err.stack ? err.stack : err));
    process.exitCode = 2;
  }
});
