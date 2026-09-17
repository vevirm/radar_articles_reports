#!/usr/bin/env python3
"""Schema and vocabulary validation for Radar reasoning claims.

This module is deliberately downstream-only.  It does not import or modify the
scanner, Deep Scan admission logic, or the active-corpus builder.  The same
validator can later be called by the claims backfill importer and by future Deep
Scan result imports.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VOCAB = ROOT / "claims_vocabulary.json"
CLAIMS_FORMAT = "radar-claims-v1"


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def load_vocabulary(path: Path = DEFAULT_VOCAB) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("profile") != "radar-claims-vocabulary-v1":
        raise ValueError(f"Invalid claims vocabulary: {path}")
    objects = raw.get("objects")
    if not isinstance(objects, dict) or not objects:
        raise ValueError("claims vocabulary must contain objects")
    clusters = set(raw.get("clusters") or [])
    stake_classes = set(raw.get("stake_classes") or [])
    for name, meta in objects.items():
        if not isinstance(meta, dict):
            raise ValueError(f"object {name!r} metadata must be an object")
        if meta.get("cluster") not in clusters:
            raise ValueError(f"object {name!r} has unknown primary cluster {meta.get('cluster')!r}")
        bad_secondary = [x for x in meta.get("secondary_clusters", []) if x not in clusters]
        if bad_secondary:
            raise ValueError(f"object {name!r} has unknown secondary clusters: {bad_secondary}")
        if meta.get("stake_class") not in (None, "") and meta.get("stake_class") not in stake_classes:
            raise ValueError(f"object {name!r} has unknown stake_class {meta.get('stake_class')!r}")
    return raw


def date_precision(value: Any) -> str | None:
    """Return the supported source-date precision without inventing missing parts."""
    text = clean(value)
    if not text:
        return None
    if re.fullmatch(r"\d{4}", text):
        year = int(text)
        return "year" if 1 <= year <= 9999 else None
    if re.fullmatch(r"\d{4}-\d{2}", text):
        try:
            dt.date.fromisoformat(text + "-01")
        except ValueError:
            return None
        return "month"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            dt.date.fromisoformat(text)
        except ValueError:
            return None
        return "day"
    return None


def exact_iso_date(value: Any) -> bool:
    return date_precision(value) == "day"


def _valid_record_key(key: str) -> bool:
    return bool(
        re.match(r"^(?:link|doi|id):\S+", key)
        or re.match(r"^historical:(?:link|doi|id):\S+", key)
    )


def _json_safe_attribute(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(_json_safe_attribute(x) for x in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _json_safe_attribute(v) for k, v in value.items())
    return False


def validate_claim(claim: Any, vocabulary: dict[str, Any] | None = None) -> list[str]:
    v = vocabulary or load_vocabulary()
    if not isinstance(claim, dict):
        return ["claim must be a JSON object"]

    problems: list[str] = []
    required = (
        "record_key", "claim_id", "object", "secondary_objects", "actor", "mechanism",
        "direction", "status", "status_date", "scope", "kind", "merit",
        "qualification", "text", "confidence", "origin", "era",
    )
    for field in required:
        if field not in claim:
            problems.append(f"missing required field: {field}")

    record_key = clean(claim.get("record_key"))
    if record_key.startswith("url:"):
        problems.append("record_key uses spec-only 'url:' prefix; repository canonical prefix is 'link:'")
    elif not _valid_record_key(record_key):
        problems.append("record_key must use link:/doi:/id: or historical:link:/doi:/id:")

    claim_id = clean(claim.get("claim_id"))
    if not re.fullmatch(r"c:[A-Za-z0-9_.:@/\-]+", claim_id):
        problems.append("claim_id must be a stable non-space id beginning with 'c:'")

    objects = v["objects"]
    aliases = v.get("object_aliases") if isinstance(v.get("object_aliases"), dict) else {}
    obj = clean(claim.get("object"))
    if obj in aliases:
        problems.append(f"object {obj!r} is an alias; use canonical {aliases[obj]!r}")
    elif obj not in objects:
        problems.append(f"unknown object: {obj!r}")

    secondary = claim.get("secondary_objects")
    if not isinstance(secondary, list):
        problems.append("secondary_objects must be a list")
    else:
        if len(secondary) > 3:
            problems.append("secondary_objects may contain at most 3 objects")
        if len({clean(x) for x in secondary}) != len(secondary):
            problems.append("secondary_objects must not contain duplicates")
        for item in secondary:
            s = clean(item)
            if s == obj:
                problems.append("secondary_objects must not repeat the primary object")
            elif s in aliases:
                problems.append(f"secondary object {s!r} is an alias; use canonical {aliases[s]!r}")
            elif s not in objects:
                problems.append(f"unknown secondary object: {s!r}")

    actor = claim.get("actor")
    if not isinstance(actor, dict):
        problems.append("actor must be an object with name and class")
    else:
        if len(clean(actor.get("name"))) < 2:
            problems.append("actor.name is required")
        if clean(actor.get("class")) not in set(v["actor_classes"]):
            problems.append(f"unknown actor.class: {clean(actor.get('class'))!r}")

    for field, vocabulary_key in (
        ("mechanism", "mechanisms"),
        ("direction", "directions"),
        ("status", "statuses"),
        ("kind", "kinds"),
        ("confidence", "confidence"),
        ("origin", "origins"),
        ("era", "eras"),
    ):
        value = clean(claim.get(field))
        if value not in set(v[vocabulary_key]):
            problems.append(f"unknown {field}: {value!r}")

    precision = date_precision(claim.get("status_date"))
    declared_precision = clean(claim.get("status_date_precision"))
    if precision is None:
        problems.append("status_date must be YYYY, YYYY-MM, or YYYY-MM-DD")
    elif precision in {"year", "month"}:
        if declared_precision != precision:
            problems.append(f"partial status_date requires status_date_precision={precision!r}")
    elif declared_precision not in {"", "day"}:
        problems.append("day-precision status_date may omit status_date_precision or set it to 'day'")
    if claim.get("deadline") not in (None, "") and not exact_iso_date(claim.get("deadline")):
        problems.append("deadline must be null/absent or YYYY-MM-DD")

    scope = claim.get("scope")
    if not isinstance(scope, dict):
        problems.append("scope must be an object with level and countries")
    else:
        level = clean(scope.get("level"))
        if level not in set(v["scopes"]):
            problems.append(f"unknown scope.level: {level!r}")
        countries = scope.get("countries", [])
        if not isinstance(countries, list) or any(not clean(x) for x in countries):
            problems.append("scope.countries must be a list of non-empty strings")
        if level in {"member_state", "associated_country"} and isinstance(countries, list) and not countries:
            problems.append(f"scope.countries must identify at least one country for {level}")

    merit = claim.get("merit")
    if isinstance(merit, bool) or not isinstance(merit, (int, float)) or not (0 <= merit <= 100):
        problems.append("merit must be a number from 0 to 100")

    if not isinstance(claim.get("qualification"), str):
        problems.append("qualification must be a string (empty is allowed)")
    if len(clean(claim.get("text"))) < 8:
        problems.append("text must contain a substantive one-sentence claim")

    attrs = claim.get("attributes", {})
    if attrs is not None and (not isinstance(attrs, dict) or not _json_safe_attribute(attrs)):
        problems.append("attributes must be a JSON-safe object")

    origin = clean(claim.get("origin"))
    provisional = claim.get("provisional", origin == "provisional")
    if not isinstance(provisional, bool):
        problems.append("provisional must be boolean when present")
    elif (origin == "provisional") != provisional:
        problems.append("origin='provisional' and provisional flag must agree")

    era = clean(claim.get("era"))
    if record_key.startswith("historical:") and era != "historical":
        problems.append("historical record_key requires era='historical'")
    if record_key and not record_key.startswith("historical:") and era == "historical":
        problems.append("era='historical' requires a historical:* record_key")

    return problems


def validate_claims(claims: Iterable[Any], vocabulary: dict[str, Any] | None = None) -> list[str]:
    v = vocabulary or load_vocabulary()
    rows = list(claims)
    problems: list[str] = []
    ids: list[str] = []
    keys: list[str] = []
    for index, claim in enumerate(rows):
        if isinstance(claim, dict):
            ids.append(clean(claim.get("claim_id")))
            keys.append(clean(claim.get("record_key")))
        for problem in validate_claim(claim, v):
            problems.append(f"claims[{index}]: {problem}")

    duplicates = sorted(k for k, n in Counter(x for x in ids if x).items() if n > 1)
    if duplicates:
        problems.append("duplicate claim_id(s): " + ", ".join(duplicates))

    per_record = Counter(x for x in keys if x)
    too_many = sorted(k for k, n in per_record.items() if n > 3)
    if too_many:
        problems.append("more than 3 claims for record(s): " + ", ".join(too_many))
    return problems


def validate_document(doc: Any, vocabulary: dict[str, Any] | None = None) -> list[str]:
    if not isinstance(doc, dict):
        return ["document top level must be a JSON object"]
    problems: list[str] = []
    if doc.get("format") != CLAIMS_FORMAT:
        problems.append(f"format must be {CLAIMS_FORMAT!r}")
    claims = doc.get("claims")
    if not isinstance(claims, list):
        problems.append("claims must be a JSON list")
        return problems
    problems.extend(validate_claims(claims, vocabulary))
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a radar-claims-v1 JSON document")
    ap.add_argument("path", type=Path)
    ap.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCAB)
    args = ap.parse_args()
    vocabulary = load_vocabulary(args.vocabulary)
    try:
        doc = json.loads(args.path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"INVALID: cannot read JSON: {exc}")
        return 2
    problems = validate_document(doc, vocabulary)
    if problems:
        print("INVALID")
        for p in problems:
            print(f"- {p}")
        return 1
    print(f"OK: {len(doc['claims'])} claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
