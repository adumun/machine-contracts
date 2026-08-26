#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from tools.coi_materializer import materialize
from tools.coi_readers import read_bundle


def diagnose_reader_output(reader_output: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    for source in reader_output.get("sources", []):
        status = source.get("status", "UNAVAILABLE")
        for error in source.get("errors", []):
            text = str(error)
            if "missing source columns" in text:
                code = "SOURCE_SCHEMA_DRIFT"
            elif "SOURCE_SNAPSHOT_MISSING" in text or status == "UNAVAILABLE":
                code = "SOURCE_UNAVAILABLE"
            elif "expected exactly one matching row" in text:
                code = "SOURCE_IDENTITY_DRIFT"
            else:
                code = "SOURCE_TRANSFORM_OR_MAPPING_FAILURE"
            issues.append({"source_id": source.get("source_id"), "code": code, "detail": text})
        if status == "PARTIAL" and not source.get("errors"):
            issues.append({"source_id": source.get("source_id"), "code": "SOURCE_PARTIAL", "detail": "Source returned PARTIAL without explicit error details"})
    return {"issues": issues, "issue_count": len(issues)}


def assess_snapshot(snapshot: dict[str, Any], diagnostics: dict[str, Any] | None = None) -> dict[str, Any]:
    reasons: list[str] = []
    if snapshot.get("reconciliation_state") == "UNAVAILABLE":
        state = "UNAVAILABLE"
        reasons.append("SNAPSHOT_UNAVAILABLE")
    elif snapshot.get("reconciliation_state") == "RECONCILIATION_REQUIRED":
        state = "DEGRADED"
        reasons.append("SNAPSHOT_RECONCILIATION_REQUIRED")
    elif snapshot.get("freshness_state") in {"STALE", "REVIEW_REQUIRED", "UNKNOWN"}:
        state = "DEGRADED"
        reasons.append(f"SNAPSHOT_FRESHNESS_{snapshot.get('freshness_state')}")
    else:
        state = "HEALTHY"

    if diagnostics and diagnostics.get("issue_count"):
        if state == "HEALTHY":
            state = "DEGRADED"
        reasons.extend(sorted({issue["code"] for issue in diagnostics["issues"]}))

    consumer_policy = {
        "quick_lookup": "BLOCKED" if state == "UNAVAILABLE" else "ALLOWED_WITH_STATUS",
        "executive_snapshot": "BLOCKED" if state == "UNAVAILABLE" else "ALLOWED_WITH_STATUS",
        "evidence_trace": "BLOCKED" if state == "UNAVAILABLE" else "ALLOWED_WITH_STATUS",
    }
    return {
        "operational_state": state,
        "reasons": reasons,
        "consumer_policy": consumer_policy,
        "read_model_id": snapshot.get("read_model_id"),
        "as_of": snapshot.get("as_of"),
        "freshness_state": snapshot.get("freshness_state"),
        "reconciliation_state": snapshot.get("reconciliation_state"),
    }


def safe_rebuild(mapping: dict[str, Any], bundle: dict[str, Any], last_known_good: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        reader_output = read_bundle(mapping, bundle)
        diagnostics = diagnose_reader_output(reader_output)
        candidate = materialize(reader_output)
        assessment = assess_snapshot(candidate, diagnostics)
        if assessment["operational_state"] == "HEALTHY":
            return {
                "status": "PROMOTE_CANDIDATE",
                "candidate": candidate,
                "assessment": assessment,
                "diagnostics": diagnostics,
                "fallback": None,
            }
        return {
            "status": "KEEP_LAST_KNOWN_GOOD" if last_known_good is not None else "DEGRADED_CANDIDATE_ONLY",
            "candidate": candidate,
            "assessment": assessment,
            "diagnostics": diagnostics,
            "fallback": copy.deepcopy(last_known_good),
        }
    except Exception as exc:
        return {
            "status": "KEEP_LAST_KNOWN_GOOD" if last_known_good is not None else "REBUILD_FAILED_NO_FALLBACK",
            "candidate": None,
            "assessment": {
                "operational_state": "UNAVAILABLE",
                "reasons": ["REBUILD_EXCEPTION"],
                "consumer_policy": {"quick_lookup": "BLOCKED", "executive_snapshot": "BLOCKED", "evidence_trace": "BLOCKED"},
                "read_model_id": (last_known_good or {}).get("read_model_id"),
                "as_of": (last_known_good or {}).get("as_of"),
                "freshness_state": (last_known_good or {}).get("freshness_state"),
                "reconciliation_state": (last_known_good or {}).get("reconciliation_state"),
            },
            "diagnostics": {"issues": [{"source_id": None, "code": "REBUILD_EXCEPTION", "detail": str(exc)}], "issue_count": 1},
            "fallback": copy.deepcopy(last_known_good),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="COI local operability/degraded-mode helper.")
    parser.add_argument("reader_output", type=Path, help="Existing coi-reader-output.v1 JSON")
    args = parser.parse_args()
    reader_output = json.loads(args.reader_output.read_text(encoding="utf-8"))
    diagnostics = diagnose_reader_output(reader_output)
    snapshot = materialize(reader_output)
    print(json.dumps({"diagnostics": diagnostics, "assessment": assess_snapshot(snapshot, diagnostics)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
