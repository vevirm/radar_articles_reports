"""SQLite graph, provenance ledger, hypothesis assessments and snapshots."""
import sqlite3
import json
from pathlib import Path

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS snapshots (
  snapshot_id TEXT PRIMARY KEY, generated_utc TEXT NOT NULL, workbook_sha256 TEXT,
  workbook_name TEXT NOT NULL, notes TEXT
);
CREATE TABLE IF NOT EXISTS raw_records (
  raw_id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
  sheet TEXT NOT NULL, row_num INTEGER NOT NULL, raw_json TEXT NOT NULL,
  UNIQUE(snapshot_id,sheet,row_num)
);
CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
  primary_raw_id TEXT NOT NULL REFERENCES raw_records(raw_id), publication_id TEXT,
  event_group_id TEXT, origin_sheet TEXT, title TEXT, source_url TEXT,
  publication_date TEXT, event_date TEXT, ingested_utc TEXT, source_family TEXT,
  subject TEXT, evidence_type TEXT, classification_basis TEXT,
  source_quality TEXT, verification TEXT, claim_text TEXT, actors TEXT, area TEXT,
  mechanism TEXT, outcome TEXT, qualifications TEXT, metadata_json TEXT
);
CREATE TABLE IF NOT EXISTS evidence_occurrences (
  evidence_id TEXT REFERENCES evidence(evidence_id), raw_id TEXT REFERENCES raw_records(raw_id),
  PRIMARY KEY (evidence_id,raw_id)
);
CREATE TABLE IF NOT EXISTS relations (
  relation_id TEXT PRIMARY KEY, snapshot_id TEXT, from_id TEXT REFERENCES evidence(evidence_id),
  to_id TEXT REFERENCES evidence(evidence_id), relation_type TEXT,
  strength TEXT CHECK(strength IN ('documented','plausible','weak')),
  justification TEXT, evidence_json TEXT
);
CREATE TABLE IF NOT EXISTS chains (
  chain_id TEXT PRIMARY KEY, snapshot_id TEXT, subject TEXT, evidence_ids_json TEXT,
  period_start TEXT, period_end TEXT, description TEXT, warnings_json TEXT
);
CREATE TABLE IF NOT EXISTS hypotheses (
  hypothesis_id TEXT PRIMARY KEY, snapshot_id TEXT, chain_id TEXT REFERENCES chains(chain_id),
  claim TEXT, alternative TEXT, support_json TEXT, against_json TEXT,
  expected_json TEXT, falsifier_json TEXT, missing_json TEXT,
  status TEXT, evaluation_json TEXT
);
CREATE TABLE IF NOT EXISTS robustness (
  assessment_id TEXT PRIMARY KEY, hypothesis_id TEXT REFERENCES hypotheses(hypothesis_id),
  test_name TEXT, outcome TEXT, details_json TEXT
);
CREATE TABLE IF NOT EXISTS llm_assessments (
  assessment_id TEXT PRIMARY KEY, snapshot_id TEXT, chain_id TEXT,
  pass_type TEXT, provider TEXT, prompt_sha256 TEXT, output_json TEXT, accepted INTEGER,
  validation_errors_json TEXT
);
CREATE TABLE IF NOT EXISTS syntheses (
  synthesis_id TEXT PRIMARY KEY, snapshot_id TEXT REFERENCES snapshots(snapshot_id),
  pass_type TEXT, provider TEXT, content_json TEXT, accepted INTEGER,
  errors_json TEXT, evidence_ids_json TEXT
);
CREATE INDEX IF NOT EXISTS e_date ON evidence(publication_date);
CREATE INDEX IF NOT EXISTS e_subject ON evidence(subject);
CREATE INDEX IF NOT EXISTS rel_from ON relations(from_id);
'''


def connect(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def add(db,table,columns):
    keys=list(columns)
    db.execute('INSERT OR REPLACE INTO '+table+' ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',[columns[k] for k in keys])


def rows(db,table):
    return [dict(r) for r in db.execute('SELECT * FROM '+table)]


def j(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
