#!/usr/bin/env python3
"""Build and apply manual LLM readability batches.

The source text is canonical. A batch is a proposal envelope: the LLM may only
fill decision/improved_text. Applying validates source hashes and exact source
text before editing anything.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "language" / "config.json"
STATE_PATH = ROOT / "language" / "state.json"
PROMPT_PATH = ROOT / "language" / "PROMPT.md"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def words(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def mode_for(path: str, cfg: dict[str, Any]) -> str:
    return "light" if matches_any(path, cfg.get("light_mode_paths", [])) else "normal"


def eligible_files(cfg: dict[str, Any], scope: str | None = None) -> list[Path]:
    out: list[Path] = []
    scope_norm = (scope or "").strip().strip("/")
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rp = rel(p)
        if scope_norm and not (rp == scope_norm or rp.startswith(scope_norm + "/")):
            continue
        if matches_any(rp, cfg.get("exclude_globs", [])):
            continue
        if matches_any(rp, cfg.get("include_globs", [])):
            out.append(p)
    return sorted(set(out), key=lambda p: rel(p))


def html_items(path: Path, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    tags = "|".join(re.escape(t) for t in cfg["html_tags"])
    # V1 intentionally handles only blocks without nested HTML. That prevents
    # readability edits from accidentally deleting links/emphasis/markup.
    rx = re.compile(rf"<(?P<tag>{tags})\b(?P<attrs>[^>]*)>(?P<body>[^<>]+)</(?P=tag)>", re.I | re.S)
    items = []
    ordinal = 0
    for m in rx.finditer(source):
        ordinal += 1
        body_raw = m.group("body")
        text = html.unescape(body_raw).strip()
        wc = words(text)
        if wc < cfg["min_words"]:
            continue
        if re.search(r"\{\{|{%|<%", text):
            continue
        items.append({
            "locator": f"html:{m.group('tag').lower()}:{ordinal}",
            "source_kind": "html_text",
            "text": text,
            "source_token": body_raw,
        })
    return items


def markdown_items(path: Path, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    items = []
    in_fence = False
    ordinal = 0
    offset = 0
    # Paragraph blocks with their exact source positions.
    for m in re.finditer(r"(?:\A|\n\s*\n)(?P<block>.*?)(?=\n\s*\n|\Z)", source, re.S):
        block = m.group("block").strip("\n")
        if not block.strip():
            continue
        stripped = block.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            continue
        if stripped.startswith(("#", "|", "---", "+++")):
            continue
        if re.match(r"^\s*[-*+]\s+", stripped):
            continue
        text = re.sub(r"\s+", " ", block.strip())
        if words(text) < cfg["min_words"]:
            continue
        ordinal += 1
        items.append({
            "locator": f"md:paragraph:{ordinal}",
            "source_kind": "markdown_block",
            "text": text,
            "source_token": block,
        })
    return items


def walk_data(obj: Any, allowed: set[str], path: tuple[Any, ...] = ()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = path + (k,)
            if k in allowed and isinstance(v, str):
                yield p, v
            yield from walk_data(v, allowed, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_data(v, allowed, path + (i,))


def path_label(parts: tuple[Any, ...]) -> str:
    return "/".join(str(x) for x in parts)


def parse_data_source(path: Path) -> tuple[Any, str, str] | None:
    source = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(source), "", ""
    if path.name == "site-data.js":
        m = re.match(r"(?s)(\s*window\.siteData\s*=\s*)(\{.*\})(\s*;\s*)\Z", source)
        if not m:
            return None
        return json.loads(m.group(2)), m.group(1), m.group(3)
    return None


def data_items(path: Path, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    parsed = parse_data_source(path)
    if parsed is None:
        return []
    obj, _, _ = parsed
    source = path.read_text(encoding="utf-8")
    allowed = set(cfg["data_keys"])
    items = []
    for parts, text in walk_data(obj, allowed):
        if words(text) < cfg["min_words"]:
            continue
        token = json.dumps(text, ensure_ascii=False)
        # Exact token replacement is safest when unique in the source.
        if source.count(token) != 1:
            continue
        items.append({
            "locator": "data:" + path_label(parts),
            "source_kind": "json_string",
            "text": text,
            "source_token": token,
        })
    return items


def collect(cfg: dict[str, Any], scope: str | None = None) -> list[dict[str, Any]]:
    result = []
    for path in eligible_files(cfg, scope):
        rp = rel(path)
        if path.suffix.lower() == ".html":
            found = html_items(path, cfg)
        elif path.suffix.lower() == ".md":
            found = markdown_items(path, cfg)
        elif path.suffix.lower() in {".json", ".js"}:
            found = data_items(path, cfg)
        else:
            found = []
        for it in found:
            text = it.pop("text")
            token = it.pop("source_token")
            item_hash = sha(text)
            result.append({
                "id": sha(f"{rp}|{it['locator']}|{item_hash}")[:16],
                "source": rp,
                "locator": it["locator"],
                "source_kind": it["source_kind"],
                "mode": mode_for(rp, cfg),
                "word_count": words(text),
                "original_sha256": item_hash,
                "original_text": text,
                "_source_token": token,
            })
    return result


def build_batch(args: argparse.Namespace) -> Path:
    cfg = load_json(CONFIG_PATH)
    state = load_json(STATE_PATH) if STATE_PATH.exists() else {"reviewed": {}}
    reviewed = state.get("reviewed", {})
    candidates = collect(cfg, args.scope)
    if not args.rescan:
        candidates = [x for x in candidates if reviewed.get(x["id"]) != x["original_sha256"]]

    target = args.target_words or cfg["target_words"]
    hard = cfg.get("hard_max_words", target + 2000)
    chosen = []
    total = 0
    for item in candidates:
        wc = item["word_count"]
        if chosen and total + wc > hard:
            break
        chosen.append(item)
        total += wc
        if total >= target:
            break

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_id = f"reader-language-{stamp}"
    public_items = []
    for x in chosen:
        public_items.append({k: v for k, v in x.items() if not k.startswith("_")} | {
            "decision": "",
            "improved_text": ""
        })
    payload = {
        "schema": "vevirm-reader-language/v1",
        "batch_id": batch_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "instructions_file": "language/PROMPT.md",
        "scope": args.scope or "all eligible reader-facing prose",
        "target_words": target,
        "batch_word_count": sum(x["word_count"] for x in public_items),
        "item_count": len(public_items),
        "instructions": PROMPT_PATH.read_text(encoding="utf-8"),
        "items": public_items,
    }
    outdir = ROOT / "language-outbox"
    outdir.mkdir(exist_ok=True)
    out = outdir / f"{batch_id}.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created {rel(out)}: {len(public_items)} items, {payload['batch_word_count']} words")
    return out


def validate_batch(batch: dict[str, Any]) -> None:
    if batch.get("schema") != "vevirm-reader-language/v1":
        raise ValueError("Unsupported or missing schema")
    if not isinstance(batch.get("items"), list):
        raise ValueError("Batch has no items list")
    ids = [x.get("id") for x in batch["items"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate item IDs")


def verify_against_outbox(returned: dict[str, Any]) -> Path:
    """Ensure the LLM changed only decision/improved_text fields."""
    batch_id = returned.get("batch_id")
    if not batch_id or not re.fullmatch(r"reader-language-[A-Za-z0-9T_-]+", str(batch_id)):
        raise ValueError("Invalid batch_id")
    outbox = ROOT / "language-outbox" / f"{batch_id}.json"
    if not outbox.exists():
        raise ValueError(f"Matching outbox batch not found: {rel(outbox)}")
    original = load_json(outbox)
    validate_batch(original)

    immutable_top = ["schema", "batch_id", "created_utc", "instructions_file", "scope",
                     "target_words", "batch_word_count", "item_count"]
    for key in immutable_top:
        if returned.get(key) != original.get(key):
            raise ValueError(f"Returned batch changed immutable field: {key}")
    if returned.get("instructions") != original.get("instructions"):
        raise ValueError("Returned batch changed embedded instructions")
    if len(returned["items"]) != len(original["items"]):
        raise ValueError("Returned batch changed item count")

    mutable = {"decision", "improved_text"}
    for idx, (ret, orig) in enumerate(zip(returned["items"], original["items"])):
        if set(ret) != set(orig):
            raise ValueError(f"Item {idx} changed field structure")
        for key in orig:
            if key not in mutable and ret.get(key) != orig.get(key):
                raise ValueError(f"Item {orig.get('id', idx)} changed immutable field: {key}")
    return outbox


def safety_check(original: str, improved: str) -> list[str]:
    problems = []
    if not improved.strip():
        problems.append("empty improved_text")
        return problems
    # Mechanical tripwires; semantic preservation is primarily the LLM task.
    number_rx = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)*(?:%|\b)")
    if number_rx.findall(original) != number_rx.findall(improved):
        problems.append("numbers changed")
    url_rx = re.compile(r"https?://\S+")
    if url_rx.findall(original) != url_rx.findall(improved):
        problems.append("URLs changed")
    if len(improved.strip()) < max(20, int(len(original.strip()) * 0.35)):
        problems.append("rewrite is suspiciously short")
    return problems


def apply_one(item: dict[str, Any]) -> tuple[str, str]:
    path = ROOT / item["source"]
    if not path.exists():
        return "stale", "source file missing"
    source = path.read_text(encoding="utf-8")
    original = item["original_text"]
    if sha(original) != item["original_sha256"]:
        return "invalid", "original_text does not match its hash"

    kind = item["source_kind"]
    if kind == "json_string":
        old_token = json.dumps(original, ensure_ascii=False)
        improved = item["improved_text"]
        new_token = json.dumps(improved, ensure_ascii=False)
    elif kind == "html_text":
        # Re-find the exact human text among simple HTML text blocks.
        old_token = None
        for candidate in {original, html.escape(original, quote=False)}:
            if source.count(candidate) == 1:
                old_token = candidate
                break
        if old_token is None:
            return "stale", "original HTML text is no longer uniquely present"
        improved = item["improved_text"]
        new_token = html.escape(improved, quote=False)
    elif kind == "markdown_block":
        # Markdown batch normalizes whitespace for the LLM, so use a whitespace-flexible match.
        parts = re.split(r"\s+", original.strip())
        pattern = r"\s+".join(re.escape(p) for p in parts)
        matches = list(re.finditer(pattern, source))
        if len(matches) != 1:
            return "stale", "original Markdown paragraph is no longer uniquely present"
        m = matches[0]
        old_token = m.group(0)
        improved = item["improved_text"]
        new_token = improved
    else:
        return "invalid", f"unknown source_kind {kind}"

    if source.count(old_token) != 1:
        return "stale", "source token is no longer uniquely present"
    if sha(original) != item["original_sha256"]:
        return "stale", "source hash changed"
    path.write_text(source.replace(old_token, new_token, 1), encoding="utf-8")
    return "applied", ""


def apply_batch(path: Path, archive: bool = True) -> dict[str, Any]:
    batch = load_json(path)
    validate_batch(batch)
    outbox_path = verify_against_outbox(batch)
    state = load_json(STATE_PATH) if STATE_PATH.exists() else {"reviewed": {}}
    state.setdefault("reviewed", {})
    report = {"batch_id": batch["batch_id"], "applied": [], "kept": [], "skipped": [], "rejected": []}

    for item in batch["items"]:
        decision = str(item.get("decision", "")).strip().lower()
        if decision not in {"keep", "rewrite", "skip"}:
            report["rejected"].append({"id": item.get("id"), "reason": "decision must be keep, rewrite, or skip"})
            continue
        if decision == "rewrite":
            improved = item.get("improved_text", "")
            problems = safety_check(item["original_text"], improved)
            if problems:
                report["rejected"].append({"id": item["id"], "reason": "; ".join(problems)})
                continue
            status, reason = apply_one(item)
            if status == "applied":
                report["applied"].append(item["id"])
            else:
                report["rejected"].append({"id": item["id"], "reason": reason})
                continue
        elif decision == "keep":
            if item.get("improved_text", "").strip():
                report["rejected"].append({"id": item["id"], "reason": "keep item must have empty improved_text"})
                continue
            report["kept"].append(item["id"])
        else:
            report["skipped"].append(item["id"])

        # Mark only successfully handled items as reviewed at this exact source hash.
        state["reviewed"][item["id"]] = item["original_sha256"]

    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_path = ROOT / "language-archive" / f"{batch['batch_id']}-report.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if archive:
        dest = ROOT / "language-archive" / path.name
        if path.resolve() != dest.resolve():
            if dest.exists():
                dest.unlink()
            shutil.move(str(path), str(dest))
        outbox_dest = ROOT / "language-archive" / (outbox_path.stem + "-original.json")
        if outbox_dest.exists():
            outbox_dest.unlink()
        shutil.move(str(outbox_path), str(outbox_dest))
    print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in report.items()}, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="create the next readability batch")
    b.add_argument("--target-words", type=int, default=None)
    b.add_argument("--scope", default=None, help="optional repo path prefix, e.g. trends")
    b.add_argument("--rescan", action="store_true", help="include text already reviewed at the same hash")
    a = sub.add_parser("apply", help="validate and apply one returned batch")
    a.add_argument("batch", type=Path)
    a.add_argument("--no-archive", action="store_true")
    args = parser.parse_args()
    if args.cmd == "build":
        build_batch(args)
    else:
        p = args.batch if args.batch.is_absolute() else ROOT / args.batch
        apply_batch(p, archive=not args.no_archive)


if __name__ == "__main__":
    main()
