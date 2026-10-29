#!/usr/bin/env python3
"""Small standard-library harness for a taste-as-learning-signal study ledger.

All commands are local and file-based. This tool does not call models or upload data.
"""

from __future__ import annotations

import argparse
import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


DIMENSIONS = ("novelty", "value", "feasibility")
MODES = ("fixed_pool", "iterative_search", "unaided_transfer")
TASTE_LABELS = ("exceptional", "strong", "fair", "limited")


class LedgerError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LedgerError("ledger root must be a JSON object")
    return value


def canonical_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pool_fingerprint(data: dict[str, Any]) -> str:
    material = {"study_id": data["study_id"], "fixed_pool": data["modes"]["fixed_pool"]}
    encoded = json.dumps(material, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _ensure_distinct_output(output_path: Path, *input_paths: Path) -> None:
    output = output_path.resolve()
    if any(output == p.resolve() for p in input_paths):
        raise LedgerError(f"refusing to overwrite an input file: {output_path}")


def _new_event_id(events: list[dict[str, Any]], prefix: str) -> str:
    existing = {event.get("event_id") for event in events if isinstance(event, dict)}
    i = 1
    while f"{prefix}-{i:04d}" in existing:
        i += 1
    return f"{prefix}-{i:04d}"


def validate_ledger(data: dict[str, Any]) -> list[str]:
    """Validate the study controls and append-only event records."""
    errors: list[str] = []
    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    if not data.get("study_id"):
        errors.append("study_id is required")
    status = data.get("fixture_status")
    if status not in ("synthetic_only", "governed_human_study"):
        errors.append("fixture_status must be synthetic_only or governed_human_study")
    if status == "governed_human_study":
        governance = data.get("governance", {})
        if not isinstance(governance, dict) or governance.get("status") != "approved_or_determined" or not governance.get("protocol_reference"):
            errors.append("governed_human_study requires governance.status=approved_or_determined and a protocol_reference")
    modes = data.get("modes")
    if not isinstance(modes, dict):
        return errors + ["modes must be an object"]

    fixed = modes.get("fixed_pool")
    if not isinstance(fixed, dict):
        errors.append("modes.fixed_pool is required")
    else:
        k = fixed.get("k")
        arms = fixed.get("arms")
        if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
            errors.append("fixed_pool.k must be a positive integer")
        if not isinstance(arms, list) or len(arms) < 2:
            errors.append("fixed_pool requires at least two arms")
        else:
            by_arm: list[dict[str, Any]] = []
            fixed_arm_ids: set[str] = set()
            for arm in arms:
                if not isinstance(arm, dict) or not arm.get("arm_id"):
                    errors.append("each fixed_pool arm needs arm_id")
                    continue
                if not isinstance(arm["arm_id"], str):
                    errors.append(f"fixed_pool arm_id must be a unique string: {arm.get('arm_id')!r}")
                    continue
                if arm["arm_id"] in fixed_arm_ids:
                    errors.append(f"fixed_pool arm_id must be unique: {arm.get('arm_id')!r}")
                fixed_arm_ids.add(arm["arm_id"])
                candidates = arm.get("candidates")
                if not isinstance(candidates, list):
                    errors.append(f"arm {arm.get('arm_id')} candidates must be a list")
                    continue
                seen: set[str] = set()
                selected = 0
                for c in candidates:
                    if not isinstance(c, dict) or not isinstance(c.get("candidate_id"), str) or not c.get("candidate_id"):
                        errors.append(f"arm {arm['arm_id']} candidate requires candidate_id")
                        continue
                    cid = c["candidate_id"]
                    if cid in seen:
                        errors.append(f"arm {arm['arm_id']} has duplicate candidate_id {cid}")
                    seen.add(cid)
                    text = c.get("text")
                    expected = canonical_hash(text) if isinstance(text, str) else None
                    if expected is None or c.get("content_sha256") != expected:
                        errors.append(f"arm {arm['arm_id']} candidate {cid} content hash mismatch")
                    if not isinstance(c.get("selected"), bool):
                        errors.append(f"arm {arm['arm_id']} candidate {cid} selected must be boolean")
                    if c.get("selected") is True:
                        selected += 1
                    label = c.get("taste_label")
                    if label is not None and label not in TASTE_LABELS:
                        errors.append(f"arm {arm['arm_id']} candidate {cid} taste_label must be one of {', '.join(TASTE_LABELS)}")
                if isinstance(k, int) and selected != k:
                    errors.append(f"arm {arm['arm_id']} selects {selected}; fixed_pool.k is {k}")
                by_arm.append({"arm_id": arm["arm_id"], "ids": seen,
                               "hashes": {c.get("candidate_id"): c.get("content_sha256") for c in candidates if isinstance(c, dict) and isinstance(c.get("candidate_id"), str)}})
            if by_arm:
                ref = by_arm[0]
                for arm in by_arm[1:]:
                    if arm["ids"] != ref["ids"]:
                        errors.append(f"fixed_pool candidate IDs differ between {ref['arm_id']} and {arm['arm_id']}")
                    elif arm["hashes"] != ref["hashes"]:
                        errors.append(f"fixed_pool candidate content hashes differ between {ref['arm_id']} and {arm['arm_id']}")
        if fixed.get("external_outcomes_blinded") is not True:
            errors.append("fixed_pool.external_outcomes_blinded must be true")
        if fixed.get("external_outcome_source") in (None, "", "source_journal_tier", "journal_tier"):
            errors.append("fixed_pool needs an independent external_outcome_source; source-tier labels cannot be the reward proof")

    iterative = modes.get("iterative_search")
    if not isinstance(iterative, dict):
        errors.append("modes.iterative_search is required")
    else:
        budget = iterative.get("budget_ceiling")
        arms = iterative.get("arms")
        valid_budget = isinstance(budget, dict) and all(isinstance(budget.get(x), int) and not isinstance(budget.get(x), bool) and budget[x] > 0 for x in ("model_calls", "tokens"))
        if not valid_budget:
            errors.append("iterative_search.budget_ceiling requires positive integer model_calls and tokens")
        if iterative.get("budget_claim") != "ceiling_only_not_strict_equality":
            errors.append("iterative_search must state that budgets are ceilings, not strict equality")
        if not isinstance(arms, list) or len(arms) < 2:
            errors.append("iterative_search requires at least two arms")
        else:
            iterative_arm_ids: set[str] = set()
            for arm in arms:
                if not isinstance(arm, dict) or not isinstance(arm.get("arm_id"), str) or not isinstance(arm.get("revisions"), list):
                    errors.append("each iterative_search arm requires a revisions list")
                    continue
                if arm["arm_id"] in iterative_arm_ids:
                    errors.append(f"duplicate iterative_search arm_id {arm['arm_id']}")
                iterative_arm_ids.add(arm["arm_id"])
                calls = tokens = 0
                rev_ids: set[str] = set()
                for rev in arm["revisions"]:
                    if not isinstance(rev, dict) or not isinstance(rev.get("revision_id"), str) or not rev.get("revision_id"):
                        errors.append(f"iterative arm {arm.get('arm_id')} revision requires revision_id")
                        continue
                    if rev["revision_id"] in rev_ids:
                        errors.append(f"iterative arm {arm.get('arm_id')} has duplicate revision_id {rev['revision_id']}")
                    parent = rev.get("parent_revision_id")
                    if parent is not None and (not isinstance(parent, str) or parent not in rev_ids):
                        errors.append(f"revision {rev['revision_id']} parent must refer to an earlier revision in the same arm")
                    rev_ids.add(rev["revision_id"])
                    content = rev.get("text")
                    expected_hash = canonical_hash(content) if isinstance(content, str) else None
                    if expected_hash is None or rev.get("content_sha256") != expected_hash:
                        errors.append(f"revision {rev['revision_id']} content hash mismatch")
                    label = rev.get("taste_label")
                    if label is not None and label not in TASTE_LABELS:
                        errors.append(f"revision {rev['revision_id']} taste_label must be one of {', '.join(TASTE_LABELS)}")
                    for field in ("model_calls", "tokens"):
                        val = rev.get(field)
                        if not isinstance(val, int) or isinstance(val, bool) or val < 0:
                            errors.append(f"revision {rev['revision_id']} {field} must be a nonnegative integer")
                        elif field == "model_calls":
                            calls += val
                        else:
                            tokens += val
                    if not rev.get("provenance"):
                        errors.append(f"revision {rev['revision_id']} needs provenance")
                if valid_budget:
                    if calls > budget.get("model_calls", 0):
                        errors.append(f"iterative arm {arm.get('arm_id')} exceeds model-call ceiling")
                    if tokens > budget.get("tokens", 0):
                        errors.append(f"iterative arm {arm.get('arm_id')} exceeds token ceiling")

    transfer = modes.get("unaided_transfer")
    if not isinstance(transfer, dict):
        errors.append("modes.unaided_transfer is required")
    else:
        tasks = transfer.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            errors.append("unaided_transfer.tasks must be a nonempty list")
        else:
            task_ids: set[str] = set()
            for task in tasks:
                if not isinstance(task, dict) or not isinstance(task.get("task_id"), str) or not task["task_id"]:
                    errors.append("each unaided transfer task requires a task_id")
                    continue
                if task["task_id"] in task_ids:
                    errors.append(f"duplicate unaided transfer task_id {task['task_id']}")
                task_ids.add(task["task_id"])
                if task.get("condition") != "unaided":
                    errors.append("unaided_transfer tasks must be explicitly unaided")

    event_ids: set[str] = set()
    events = data.get("events", [])
    if not isinstance(events, list):
        errors.append("events must be a list")
        events = []
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("event_id"), str) or not event.get("event_id"):
            errors.append("every event requires event_id")
            continue
        if event["event_id"] in event_ids:
            errors.append(f"duplicate event_id {event['event_id']}")
        event_ids.add(event["event_id"])
        if event.get("event_type") not in ("candidate_created", "candidate_revised", "rating_imported", "transfer_response"):
            errors.append(f"event {event['event_id']} has unsupported event_type")
        if not event.get("timestamp") or not event.get("provenance"):
            errors.append(f"event {event['event_id']} requires timestamp and provenance")
    ratings = data.get("external_blind_ratings", [])
    if not isinstance(ratings, list):
        errors.append("external_blind_ratings must be a list")
    else:
        rating_keys: set[tuple[str, str, str]] = set()
        for i, rating in enumerate(ratings, start=1):
            if not isinstance(rating, dict):
                errors.append(f"external rating {i} must be an object")
                continue
            blind_id, reviewer, dimension = (rating.get(k) for k in ("blind_id", "reviewer_code", "dimension"))
            score = rating.get("rating")
            if not all(isinstance(x, str) and x for x in (blind_id, reviewer)):
                errors.append(f"external rating {i} requires blind_id and reviewer_code")
                continue
            if dimension not in DIMENSIONS:
                errors.append(f"external rating {i} has invalid dimension")
            if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 7:
                errors.append(f"external rating {i} must be an integer from 1 to 7")
            key = (blind_id, reviewer, dimension if isinstance(dimension, str) else "")
            if key in rating_keys:
                errors.append(f"duplicate stored external rating {blind_id}/{reviewer}/{dimension}")
            rating_keys.add(key)
    return errors


def _candidate_rows(data: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    rows = []
    for arm in data["modes"]["fixed_pool"]["arms"]:
        for candidate in arm["candidates"]:
            rows.append((arm, candidate))
    return rows


def _expected_blind_and_key_rows(data: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    fingerprint = _pool_fingerprint(data)
    fixed_arms = data["modes"]["fixed_pool"]["arms"]
    reference_candidates = fixed_arms[0]["candidates"]
    blind_by_candidate = {candidate["candidate_id"]: f"B{i:04d}" for i, candidate in enumerate(reference_candidates, 1)}
    blind_rows = [{"blind_id": blind_by_candidate[c["candidate_id"]],
                   "pool_fingerprint": fingerprint,
                   "candidate_text": c["text"],
                   "review_context": "Rate novelty, value, and feasibility independently."}
                  for c in reference_candidates]
    key_rows = []
    for arm, candidate in _candidate_rows(data):
        key_rows.append({
            "blind_id": blind_by_candidate[candidate["candidate_id"]],
            "pool_fingerprint": fingerprint,
            "candidate_id": candidate["candidate_id"],
            "arm_id": arm["arm_id"],
            "condition": arm.get("condition", ""),
            "selected": str(candidate["selected"]).lower(),
            "taste_label": candidate.get("taste_label") or "",
            "content_sha256": candidate["content_sha256"],
        })
    return blind_rows, key_rows


def _read_exact_csv(path: Path, fieldnames: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != fieldnames:
            raise LedgerError(f"{path} has unexpected columns; expected {', '.join(fieldnames)}")
        rows = list(reader)
        if any(None in row for row in rows):
            raise LedgerError(f"{path} has a row with an incorrect number of columns")
        return rows


def validate_blind_export(data: dict[str, Any], path: Path) -> list[dict[str, str]]:
    expected, _ = _expected_blind_and_key_rows(data)
    actual = _read_exact_csv(path, ["blind_id", "pool_fingerprint", "candidate_text", "review_context"])
    if actual != expected:
        raise LedgerError("blinded export does not match this ledger's deterministic candidate IDs and text; regenerate it")
    return actual


def validate_key_map(data: dict[str, Any], path: Path) -> list[dict[str, str]]:
    _, expected = _expected_blind_and_key_rows(data)
    fields = ["blind_id", "pool_fingerprint", "candidate_id", "arm_id", "condition", "selected", "taste_label", "content_sha256"]
    actual = _read_exact_csv(path, fields)
    if actual != expected:
        raise LedgerError("private key map does not exactly match this ledger's expected arm/candidate mapping")
    return actual


def export_blind(data: dict[str, Any], review_path: Path, key_path: Path) -> None:
    errors = validate_ledger(data)
    if errors:
        raise LedgerError("ledger invalid:\n- " + "\n- ".join(errors))
    if review_path.resolve() == key_path.resolve():
        raise LedgerError("review export and private key map must be different files")
    review_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    blind_rows, key_rows = _expected_blind_and_key_rows(data)
    with review_path.open("w", newline="", encoding="utf-8") as f_review, key_path.open("w", newline="", encoding="utf-8") as f_key:
        review = csv.writer(f_review)
        key = csv.writer(f_key)
        review.writerow(["blind_id", "pool_fingerprint", "candidate_text", "review_context"])
        key.writerow(["blind_id", "pool_fingerprint", "candidate_id", "arm_id", "condition", "selected", "taste_label", "content_sha256"])
        for row in blind_rows:
            review.writerow([row[k] for k in ("blind_id", "pool_fingerprint", "candidate_text", "review_context")])
        for row in key_rows:
            key.writerow([row[k] for k in ("blind_id", "pool_fingerprint", "candidate_id", "arm_id", "condition", "selected", "taste_label", "content_sha256")])


def import_ratings(ledger: dict[str, Any], blind_path: Path, ratings_path: Path, output_path: Path) -> None:
    errors = validate_ledger(ledger)
    if errors:
        raise LedgerError("ledger invalid:\n- " + "\n- ".join(errors))
    _ensure_distinct_output(output_path, blind_path, ratings_path)
    blind_rows = validate_blind_export(ledger, blind_path)
    expected_ids = {row["blind_id"] for row in blind_rows}
    if len(expected_ids) != len(blind_rows) or not expected_ids:
        raise LedgerError("blind export has duplicate or missing blind_id values")
    with ratings_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"blind_id", "reviewer_code", "dimension", "rating"}
        if not required.issubset(reader.fieldnames or []):
            raise LedgerError("ratings CSV requires columns: blind_id, reviewer_code, dimension, rating")
        rating_rows = list(reader)
    seen: set[tuple[str, str, str]] = set()
    prior_keys = {(r.get("blind_id"), r.get("reviewer_code"), r.get("dimension")) for r in ledger.get("external_blind_ratings", [])}
    covered: set[tuple[str, str]] = set()
    normalized = []
    for row_num, row in enumerate(rating_rows, start=2):
        bid, reviewer, dimension = (row.get(k, "").strip() for k in ("blind_id", "reviewer_code", "dimension"))
        if bid not in expected_ids:
            raise LedgerError(f"row {row_num}: unknown blind_id {bid!r}")
        if not reviewer:
            raise LedgerError(f"row {row_num}: reviewer_code is required; use a study-issued pseudonym")
        if dimension not in DIMENSIONS:
            raise LedgerError(f"row {row_num}: dimension must be one of {', '.join(DIMENSIONS)}")
        key = (bid, reviewer, dimension)
        if key in seen or key in prior_keys:
            raise LedgerError(f"row {row_num}: duplicate rating for {bid}/{reviewer}/{dimension}")
        seen.add(key)
        covered.add((bid, dimension))
        try:
            rating = int(row.get("rating", ""))
        except ValueError as exc:
            raise LedgerError(f"row {row_num}: rating must be an integer from 1 to 7") from exc
        if str(rating) != row.get("rating", "").strip() or not 1 <= rating <= 7:
            raise LedgerError(f"row {row_num}: rating must be an integer from 1 to 7")
        normalized.append({"blind_id": bid, "reviewer_code": reviewer, "dimension": dimension, "rating": rating})
    missing = [(bid, dim) for bid in sorted(expected_ids) for dim in DIMENSIONS if (bid, dim) not in covered]
    if missing:
        preview = ", ".join(f"{bid}/{dim}" for bid, dim in missing[:8])
        raise LedgerError(f"missing external ratings for {len(missing)} blind-ID/dimension cells: {preview}")
    out = copy.deepcopy(ledger)
    out["external_blind_ratings"] = list(ledger.get("external_blind_ratings", [])) + normalized
    events = out.setdefault("events", [])
    events.append({
        "event_id": _new_event_id(events, "rating-import"),
        "event_type": "rating_imported",
        "timestamp": _utc_now(),
        "provenance": {"tool": "ledger.py", "blind_export": str(blind_path), "blind_export_sha256": _file_sha256(blind_path),
                       "pool_fingerprint": _pool_fingerprint(ledger), "ratings_file": str(ratings_path),
                       "ratings_sha256": _file_sha256(ratings_path), "row_count": len(normalized)},
    })
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def import_transfer(ledger: dict[str, Any], responses_path: Path, output_path: Path) -> None:
    """Append unaided responses while requiring a pre-existing governance determination."""
    errors = validate_ledger(ledger)
    if errors:
        raise LedgerError("ledger invalid:\n- " + "\n- ".join(errors))
    _ensure_distinct_output(output_path, responses_path)
    if ledger.get("fixture_status") == "governed_human_study":
        governance = ledger.get("governance", {})
        if governance.get("status") != "approved_or_determined" or not governance.get("protocol_reference"):
            raise LedgerError("transfer responses require documented approval/determination before collection")
    with responses_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"task_id", "subject_code", "response_text", "timestamp"}
        if not required.issubset(reader.fieldnames or []):
            raise LedgerError("transfer CSV requires task_id, subject_code, response_text, timestamp")
        incoming = list(reader)
    tasks = {t["task_id"] for t in ledger["modes"]["unaided_transfer"]["tasks"]}
    seen: set[tuple[str, str]] = set()
    normalized = []
    for row_num, row in enumerate(incoming, start=2):
        task_id, subject = row["task_id"].strip(), row["subject_code"].strip()
        response = row["response_text"].strip()
        key = (task_id, subject)
        if task_id not in tasks:
            raise LedgerError(f"row {row_num}: unknown unaided transfer task {task_id!r}")
        if not subject or not response or not row["timestamp"].strip():
            raise LedgerError(f"row {row_num}: subject_code, response_text, and timestamp are required")
        if key in seen:
            raise LedgerError(f"row {row_num}: duplicate response for task/subject {task_id}/{subject}")
        seen.add(key)
        normalized.append({"task_id": task_id, "subject_code": subject, "response_text": response,
                           "condition": "unaided", "timestamp": row["timestamp"].strip(),
                           "provenance": "local unaided transfer import"})
    if not normalized:
        raise LedgerError("transfer response file is empty")
    out = copy.deepcopy(ledger)
    prior = list(ledger["modes"]["unaided_transfer"].get("responses", []))
    prior_keys = {(r.get("task_id"), r.get("subject_code")) for r in prior}
    if any((r["task_id"], r["subject_code"]) in prior_keys for r in normalized):
        raise LedgerError("transfer import duplicates a prior task/subject response")
    out["modes"]["unaided_transfer"]["responses"] = prior + normalized
    events = out.setdefault("events", [])
    events.append({
        "event_id": _new_event_id(events, "transfer-import"),
        "event_type": "transfer_response", "timestamp": normalized[-1]["timestamp"],
        "provenance": {"tool": "ledger.py", "responses_file": str(responses_path), "row_count": len(normalized)},
    })
    output_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def summarize(data: dict[str, Any], key_path: Path | None = None) -> list[dict[str, Any]]:
    errors = validate_ledger(data)
    if errors:
        raise LedgerError("ledger invalid:\n- " + "\n- ".join(errors))
    ratings = data.get("external_blind_ratings", [])
    if key_path is None:
        rows = []
        for dim in DIMENSIONS:
            by_item: dict[str, list[int]] = defaultdict(list)
            for rating in ratings:
                if rating["dimension"] == dim:
                    by_item[rating["blind_id"]].append(rating["rating"])
            values = [v for item_values in by_item.values() for v in item_values]
            item_means = [sum(item_values) / len(item_values) for item_values in by_item.values()]
            rows.append({"condition": "unlinked", "dimension": dim, "n_items": len(item_means), "n_ratings": len(values),
                         "mean_rating": round(sum(item_means) / len(item_means), 3) if item_means else None,
                         "pooled_rating_mean": round(sum(values) / len(values), 3) if values else None,
                         "min": min(values) if values else None, "max": max(values) if values else None,
                         "interpretation": "descriptive only; equal-item mean; no inferential or reward-validity claim"})
        return rows
    key_rows = validate_key_map(data, key_path)
    blind_map: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in key_rows:
        blind_map[row["blind_id"]].append(row)
    groups: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for rating in ratings:
        for key in blind_map.get(rating["blind_id"], []):
            if key.get("selected") == "true":
                groups[(key["arm_id"], rating["dimension"], rating["blind_id"])].append(rating["rating"])
    rows = []
    for arm in data["modes"]["fixed_pool"]["arms"]:
        for dim in DIMENSIONS:
            by_item = {blind_id: values for (arm_id, dimension, blind_id), values in groups.items()
                       if arm_id == arm["arm_id"] and dimension == dim}
            values = [v for item_values in by_item.values() for v in item_values]
            item_means = [sum(item_values) / len(item_values) for item_values in by_item.values()]
            rows.append({"arm_id": arm["arm_id"], "condition": arm.get("condition", ""),
                         "selection_status": "selected by arm", "dimension": dim, "n_items": len(item_means), "n_ratings": len(values),
                         "mean_rating": round(sum(item_means) / len(item_means), 3) if item_means else None,
                         "pooled_rating_mean": round(sum(values) / len(values), 3) if values else None,
                         "min": min(values) if values else None, "max": max(values) if values else None,
                         "interpretation": "descriptive only; equal-item mean; no inferential or reward-validity claim"})
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("validate", "summarize"):
        p = sub.add_parser(cmd)
        p.add_argument("ledger", type=Path)
        if cmd == "summarize":
            p.add_argument("--csv", type=Path)
            p.add_argument("--key-map", type=Path, help="private key map from export-blind; keep separate from reviewer files")
    p = sub.add_parser("export-blind")
    p.add_argument("ledger", type=Path)
    p.add_argument("--review", type=Path, required=True)
    p.add_argument("--key-map", type=Path, required=True)
    p = sub.add_parser("import-ratings")
    p.add_argument("ledger", type=Path)
    p.add_argument("--blind-export", type=Path, required=True)
    p.add_argument("--ratings", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("import-transfer")
    p.add_argument("ledger", type=Path)
    p.add_argument("--responses", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        data = read_json(args.ledger)
        if args.command == "validate":
            errors = validate_ledger(data)
            if errors:
                print("INVALID\n- " + "\n- ".join(errors), file=sys.stderr)
                return 2
            print(f"Structurally valid {data['fixture_status']} ledger. This does not prove study approval, data validity, or inferential claims.")
        elif args.command == "export-blind":
            _ensure_distinct_output(args.review, args.ledger, args.key_map)
            _ensure_distinct_output(args.key_map, args.ledger)
            export_blind(data, args.review, args.key_map)
            print(f"Wrote blinded review CSV: {args.review}\nWrote separate private key map: {args.key_map}")
        elif args.command == "import-ratings":
            _ensure_distinct_output(args.out, args.ledger, args.blind_export, args.ratings)
            import_ratings(data, args.blind_export, args.ratings, args.out)
            print(f"Imported external ratings with validation into {args.out}")
        elif args.command == "import-transfer":
            _ensure_distinct_output(args.out, args.ledger, args.responses)
            import_transfer(data, args.responses, args.out)
            print(f"Imported unaided transfer responses into {args.out}")
        elif args.command == "summarize":
            if args.csv:
                _ensure_distinct_output(args.csv, args.ledger, *(tuple([args.key_map]) if args.key_map else tuple()))
            rows = summarize(data, args.key_map)
            if args.csv:
                args.csv.parent.mkdir(parents=True, exist_ok=True)
                with args.csv.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                print(f"Wrote descriptive summary: {args.csv}")
            else:
                print(json.dumps(rows, indent=2))
        return 0
    except (LedgerError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
