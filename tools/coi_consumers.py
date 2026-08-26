#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

CONSUMER_AUTHORITY = "DERIVED_NON_AUTHORITATIVE"


def _base(snapshot: dict[str, Any], consumer_type: str) -> dict[str, Any]:
    return {
        "schema_version": "coi-consumer-output.v1",
        "contract_version": "1.0.0",
        "consumer_type": consumer_type,
        "read_model_id": snapshot["read_model_id"],
        "snapshot_as_of": snapshot["as_of"],
        "snapshot_freshness_state": snapshot["freshness_state"],
        "snapshot_reconciliation_state": snapshot["reconciliation_state"],
        "authority_mode": CONSUMER_AUTHORITY,
    }


def quick_lookup(snapshot: dict[str, Any], object_id: str, canonical_concept: str) -> dict[str, Any]:
    result = _base(snapshot, "QUICK_LOOKUP")
    key = f"{object_id}::{canonical_concept}"
    fact = next((copy.deepcopy(item) for item in snapshot["fact_index"] if item["fact_key"] == key), None)
    result["query"] = {"object_id": object_id, "canonical_concept": canonical_concept}
    if fact is None:
        result.update({"status": "NOT_FOUND", "fact": None, "limitations": ["FACT_NOT_PRESENT_IN_RM_COI_001"]})
    else:
        result.update({"status": "FOUND", "fact": fact, "limitations": []})
    return result


def executive_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    result = _base(snapshot, "EXECUTIVE_SNAPSHOT")
    facts = [copy.deepcopy(item) for item in snapshot["fact_index"]]
    sections: dict[str, list[dict[str, Any]]] = {}
    for fact in facts:
        sections.setdefault(fact["concern_family"], []).append(fact)
    attention = [
        copy.deepcopy(item)
        for item in facts
        if item["value_state"] in {"UNKNOWN", "MISSING", "STALE", "RECONCILIATION_REQUIRED", "RESTRICTED"}
        or item.get("freshness", {}).get("state") in {"STALE", "REVIEW_REQUIRED", "UNKNOWN"}
    ]
    result.update({
        "status": "AVAILABLE" if snapshot["reconciliation_state"] != "UNAVAILABLE" else "UNAVAILABLE",
        "source_status_summary": copy.deepcopy(snapshot["source_status_summary"]),
        "fact_count": len(facts),
        "attention_count": len(attention),
        "sections": sections,
        "attention": attention,
        "limitations": [] if snapshot["reconciliation_state"] == "CURRENT" else ["SNAPSHOT_NOT_FULLY_RECONCILED"],
    })
    return result


def evidence_trace(snapshot: dict[str, Any], fact_key: str) -> dict[str, Any]:
    result = _base(snapshot, "EVIDENCE_TRACE")
    fact = next((copy.deepcopy(item) for item in snapshot["fact_index"] if item["fact_key"] == fact_key), None)
    if fact is None:
        result.update({"status": "NOT_FOUND", "fact_key": fact_key, "trace": None, "limitations": ["FACT_NOT_PRESENT_IN_RM_COI_001"]})
        return result
    record = next((copy.deepcopy(item) for item in snapshot["records"] if item["record_id"] == fact["record_id"]), None)
    refs = set(fact.get("source_refs", []))
    envelopes = []
    for envelope in (record or {}).get("source_envelopes", []):
        if envelope.get("source_ref") in refs:
            envelopes.append(copy.deepcopy(envelope))
    if not envelopes:
        for envelope in snapshot.get("sources", []):
            if envelope.get("source_ref") in refs:
                envelopes.append(copy.deepcopy(envelope))
    result.update({
        "status": "FOUND",
        "fact_key": fact_key,
        "trace": {"fact": fact, "record": record, "source_envelopes": envelopes},
        "limitations": [] if envelopes else ["SOURCE_ENVELOPE_NOT_RESOLVED"],
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Consume RM-COI-001 without touching authoritative sources.")
    parser.add_argument("snapshot", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    lookup = sub.add_parser("lookup")
    lookup.add_argument("object_id")
    lookup.add_argument("canonical_concept")
    trace = sub.add_parser("trace")
    trace.add_argument("fact_key")
    sub.add_parser("executive")
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    if args.command == "lookup":
        output = quick_lookup(snapshot, args.object_id, args.canonical_concept)
    elif args.command == "trace":
        output = evidence_trace(snapshot, args.fact_key)
    else:
        output = executive_snapshot(snapshot)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
