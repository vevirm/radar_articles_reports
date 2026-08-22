#!/usr/bin/env node
'use strict';

// Small bridge used by the Python scanner so discovery can target the exact
// empty/sparse cells produced by the browser's Sovereignty-Frontier classifier.
// It reads a cumulative radar snapshot from stdin and writes counts only.
const fs = require('fs');
const Insights = require('../briefing/insights.js');
global.RadarInsights = Insights;
const Frontier = require('../frontier/frontier.js');

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', () => {
  try {
    const data = raw.trim() ? JSON.parse(raw) : {};
    const view = Frontier.buildFrontier(data);
    const counts = {};
    for (const row of view.rows) {
      for (const column of view.columns) {
        counts[`${row.id}-${column.id}`] = view.cells[row.id][column.id].length;
      }
    }
    process.stdout.write(JSON.stringify({ counts, qualifying: view.signals.length }));
  } catch (err) {
    process.stderr.write(String(err && err.stack ? err.stack : err));
    process.exitCode = 2;
  }
});
