#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

READ_MODEL_ID = "RM-COI-001"
READ_MODEL_NAME = "Corporate Operating Snapshot"


def _aggregate_freshness(states: list[str]) -> str:
    if not states:
        return "UNKNOWN"
    if "STALE" in states:
        return "STALE"
    if "REVIEW_REQUIRED" in states:
        return "REVIEW_REQUIRED"
    if "UNKNOWN" in states:
        return "UNKNOWN"
    return "CURRENT"


def _aggregate_reconciliation(statuses: list[str]) -> str:
    if not statuses:
        return "UNAVAILABLE"
    if all(status == "UNAVAILABLE" for status in statuses):
        return "UNAVAILABLE"
    if any(status != "OK" for status in statuses):
        return "RECONCILIATION_REQUIRED"
    return "CURRENT"


def _fact_index_entry(record: dict[str, Any], fact: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "fact_key": f"{record['object_id']}::{fact['canonical_concept']}",
        "answer_id": fact["answer_id"],
        "record_id": record["record_id"],
        "concern_family": record["concern_family"],
        "object_id": record["object_id"],
        "canonical_concept": fact["canonical_concept"],
        "display_label": fact["display_label"],
        "value_state": fact["value_state"],
        "semantic_class": fact["semantic_class"],
        "authority": copy.deepcopy(fact["authority"]),
        "authority_mode": fact["authority"]["mode"],
        "provenance": copy.deepcopy(fact["provenance"]),
        "source_refs": list(fact["provenance"]["source_refs"]),
        "freshness": copy.deepcopy(fact["freshness"]),
        "confidentiality": copy.deepcopy(fact["confidentiality"]),
        "limitations": copy.deepcopy(fact.get("limitations", [])),
        "drill_through_ref": fact.get("drill_through_ref"),
    }
    if "business_meaning" in fact:
        entry["business_meaning"] = fact["business_meaning"]
    if "value" in fact:
        entry["value"] = copy.deepcopy(fact["value"])
    if "unit" in fact:
        entry["unit"] = fact["unit"]
    return entry


def materialize(reader_output: dict[str, Any]) -> dict[str, Any]:
    generated_at = reader_output["generated_at"]
    source_results = reader_output.get("sources", [])

    sources = []
    records = []
    source_statuses = []
    freshness_states = []

    for source_result in source_results:
        source_statuses.append(source_result["status"])
        envelope = copy.deepcopy(source_result["source_envelope"])
        sources.append(envelope)
        freshness_states.append(envelope.get("freshness", {}).get("state", "UNKNOWN"))
        records.extend(copy.deepcopy(source_result.get("records", [])))

    records.sort(key=lambda item: (item["concern_family"], item["object_id"], item["record_id"]))
    sources.sort(key=lambda item: item["source_id"])

    fact_index = []
    for record in records:
        for fact in record.get("facts", []):
            fact_index.append(_fact_index_entry(record, fact))
    fact_index.sort(key=lambda item: (item["concern_family"], item["object_id"], item["canonical_concept"]))

    summary = {
        "total": len(source_statuses),
        "ok": sum(1 for status in source_statuses if status == "OK"),
        "partial": sum(1 for status in source_statuses if status == "PARTIAL"),
        "unavailable": sum(1 for status in source_statuses if status == "UNAVAILABLE"),
    }

    return {
        "schema_version": "coi-materialized-snapshot.v1",
        "contract_version": "1.1.0",
        "read_model_id": READ_MODEL_ID,
        "name": READ_MODEL_NAME,
        "initiative_id": reader_output["initiative_id"],
        "authority_mode": "DERIVED_NON_AUTHORITATIVE",
        "generated_at": generated_at,
        "as_of": generated_at,
        "freshness_state": _aggregate_freshness(freshness_states),
        "reconciliation_state": _aggregate_reconciliation(source_statuses),
        "source_status_summary": summary,
        "sources": sources,
        "records": records,
        "fact_index": fact_index,
    }


def quick_lookup(snapshot: dict[str, Any], object_id: str, canonical_concept: str) -> dict[str, Any] | None:
    key = f"{object_id}::{canonical_concept}"
    return next((copy.deepcopy(item) for item in snapshot["fact_index"] if item["fact_key"] == key), None)


def executive_briefing_projection(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "read_model_id": snapshot["read_model_id"],
        "as_of": snapshot["as_of"],
        "freshness_state": snapshot["freshness_state"],
        "reconciliation_state": snapshot["reconciliation_state"],
        "source_status_summary": copy.deepcopy(snapshot["source_status_summary"]),
        "fact_count": len(snapshot["fact_index"]),
        "unknown_or_missing_count": sum(
            1 for item in snapshot["fact_index"] if item["value_state"] in {"UNKNOWN", "MISSING", "RECONCILIATION_REQUIRED", "RESTRICTED"}
        ),
    }


def static_view_projection(snapshot: dict[str, Any], concern_family: str) -> list[dict[str, Any]]:
    return [copy.deepcopy(item) for item in snapshot["fact_index"] if item["concern_family"] == concern_family]


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize a rebuildable COI file/JSON read model from deterministic M2 reader output.")
    parser.add_argument("input", type=Path, help="M2 coi-reader-output.v1 JSON")
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    reader_output = json.loads(args.input.read_text(encoding="utf-8"))
    snapshot = materialize(reader_output)
    rendered = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
