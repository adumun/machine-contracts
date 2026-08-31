#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

COVERAGE_AUTHORITY = "DERIVED_NON_AUTHORITATIVE"
LIFECYCLE_PROGRESS_RANK = {
    "CAPTURED": 0,
    "DISCOVERING": 1,
    "VALIDATING": 2,
    "QUALIFIED": 3,
    "DEFINING": 4,
    "READY_FOR_DELIVERY": 5,
    "DELIVERING": 6,
    "RELEASE_CANDIDATE": 7,
    "OPERATING": 8,
    "MAINTAINING": 9,
    "EVOLVING": 10,
}


def _rows_to_dicts(rows: list[list[Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    if not rows:
        return [], []
    headers = [str(value).strip() for value in rows[0]]
    result: list[dict[str, Any]] = []
    for source_row in rows[1:]:
        padded = list(source_row) + [""] * max(0, len(headers) - len(source_row))
        result.append(dict(zip(headers, padded[: len(headers)])))
    return headers, result


def _source_meta(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_ref": str(source.get("source_ref") or ""),
        "freshness": copy.deepcopy(source.get("freshness") or {"state": "UNKNOWN"}),
        "confidentiality": copy.deepcopy(source.get("confidentiality") or {"classification": "INTERNAL"}),
        "reconciliation_state": str(source.get("reconciliation_state") or "CURRENT"),
    }


def _exact_link(value: Any, initiative_id: str) -> bool:
    text = str(value or "")
    return re.search(rf"(?<![A-Z0-9_-]){re.escape(initiative_id)}(?![A-Z0-9_-])", text) is not None


def _is_governed_non_initiative(row: dict[str, Any]) -> bool:
    """Return True only for explicitly classified, current, mapped non-initiative objects.

    These rows are governed portfolio/application objects, but they are outside the
    lifecycle-progression population because COI portfolio progression compares
    INITIATIVE objects only. They must not make that initiative population look
    incomplete merely because a component/application/experiment is represented in
    the same registry.
    """
    object_type = str(row.get("Portfolio Object Type") or "").strip()
    reconciliation = str(row.get("Reconciliation Status") or "").strip()
    authority_state = str(row.get("Authority State") or "").strip()
    return bool(object_type) and object_type != "INITIATIVE" and reconciliation == "MAPPED" and authority_state == "CURRENT"


def build_portfolio_coverage(source: dict[str, Any]) -> dict[str, Any]:
    headers, rows = _rows_to_dicts(source.get("rows", []))
    required = {
        "Initiative",
        "Lifecycle Stage",
        "Current Gate",
        "Gate Outcome",
        "Evidence Confidence",
        "Canonical Lifecycle State",
        "Reconciliation Status",
        "Portfolio Object Type",
        "Authority State",
        "Normalized Object ID",
    }
    missing = sorted(required - set(headers))
    if missing:
        return {
            "status": "UNAVAILABLE",
            "source": _source_meta(source),
            "comparable_initiatives": [],
            "non_comparable_row_count": len(rows),
            "excluded_non_initiative_row_count": 0,
            "global_comparison_supported": False,
            "ranking_basis": "CANONICAL_LIFECYCLE_PROGRESSION_ONLY",
            "limitations": ["SOURCE_SCHEMA_DRIFT:" + ",".join(missing)],
        }

    comparable: list[dict[str, Any]] = []
    non_comparable = 0
    excluded_non_initiative = 0
    for row in rows:
        object_type = str(row.get("Portfolio Object Type") or "").strip()
        object_id = str(row.get("Normalized Object ID") or "").strip()
        lifecycle_state = str(row.get("Canonical Lifecycle State") or "").strip()
        reconciliation = str(row.get("Reconciliation Status") or "").strip()
        authority_state = str(row.get("Authority State") or "").strip()

        if object_type != "INITIATIVE":
            if _is_governed_non_initiative(row):
                excluded_non_initiative += 1
            else:
                # Unresolved, stale, unmapped or authority-uncertain rows still
                # represent an incomplete portfolio identity population and remain
                # fail-closed for global initiative comparison.
                non_comparable += 1
            continue

        if object_id and lifecycle_state and reconciliation == "MAPPED" and authority_state == "CURRENT":
            comparable.append(
                {
                    "object_id": object_id,
                    "label": str(row.get("Initiative") or object_id),
                    "canonical_lifecycle_state": lifecycle_state,
                    "lifecycle_stage": str(row.get("Lifecycle Stage") or ""),
                    "current_gate": str(row.get("Current Gate") or ""),
                    "gate_outcome": str(row.get("Gate Outcome") or ""),
                    "evidence_confidence": str(row.get("Evidence Confidence") or ""),
                    "reconciliation_status": reconciliation,
                    "authority_state": authority_state,
                    "progress_rank": LIFECYCLE_PROGRESS_RANK.get(lifecycle_state),
                }
            )
        else:
            non_comparable += 1

    comparable.sort(
        key=lambda item: (
            item["progress_rank"] is None,
            -(item["progress_rank"] if item["progress_rank"] is not None else -1),
            item["object_id"],
        )
    )
    limitations: list[str] = []
    if non_comparable:
        limitations.append("PORTFOLIO_POPULATION_NOT_FULLY_COMPARABLE")
    if any(item["progress_rank"] is None for item in comparable):
        limitations.append("UNRANKED_CANONICAL_LIFECYCLE_STATE_PRESENT")
    global_supported = non_comparable == 0 and all(item["progress_rank"] is not None for item in comparable)
    status = "AVAILABLE" if comparable else "UNAVAILABLE"
    if comparable and not global_supported:
        status = "PARTIAL"

    return {
        "status": status,
        "source": _source_meta(source),
        "comparable_initiatives": comparable,
        "non_comparable_row_count": non_comparable,
        "excluded_non_initiative_row_count": excluded_non_initiative,
        "global_comparison_supported": global_supported,
        "ranking_basis": "CANONICAL_LIFECYCLE_PROGRESSION_ONLY",
        "limitations": limitations,
    }


def build_evidence_inventory(source: dict[str, Any], initiative_ids: list[str]) -> dict[str, Any]:
    headers, rows = _rows_to_dicts(source.get("rows", []))
    required = {
        "Evidence ID",
        "Title / Finding",
        "Evidence Date",
        "Producing Initiative / Context",
        "Evidence Type",
        "Linked Object ID / Name",
        "Observation / Result",
        "Interpretation",
        "Polarity",
        "Strength",
        "Confidence",
        "Decision Status",
        "Lifecycle State",
        "Source URL / Reference",
        "Authority State",
    }
    missing = sorted(required - set(headers))
    by_initiative: dict[str, list[dict[str, Any]]] = {initiative_id: [] for initiative_id in initiative_ids}
    if missing:
        return {
            "status": "UNAVAILABLE",
            "source": _source_meta(source),
            "by_initiative": by_initiative,
            "limitations": ["SOURCE_SCHEMA_DRIFT:" + ",".join(missing)],
        }

    for row in rows:
        authority_state = str(row.get("Authority State") or "").strip()
        if authority_state and authority_state != "CURRENT":
            continue
        linked = row.get("Linked Object ID / Name")
        for initiative_id in initiative_ids:
            if not _exact_link(linked, initiative_id):
                continue
            by_initiative[initiative_id].append(
                {
                    "evidence_id": str(row.get("Evidence ID") or ""),
                    "title": str(row.get("Title / Finding") or ""),
                    "evidence_date": str(row.get("Evidence Date") or ""),
                    "producing_context": str(row.get("Producing Initiative / Context") or ""),
                    "evidence_type": str(row.get("Evidence Type") or ""),
                    "observation": str(row.get("Observation / Result") or ""),
                    "interpretation": str(row.get("Interpretation") or ""),
                    "polarity": str(row.get("Polarity") or ""),
                    "strength": str(row.get("Strength") or ""),
                    "confidence": str(row.get("Confidence") or ""),
                    "decision_status": str(row.get("Decision Status") or ""),
                    "lifecycle_state": str(row.get("Lifecycle State") or ""),
                    "source_ref": str(row.get("Source URL / Reference") or ""),
                    "authority_state": authority_state or "CURRENT",
                }
            )

    for items in by_initiative.values():
        items.sort(key=lambda item: (item["evidence_date"], item["evidence_id"]))

    status = "AVAILABLE" if any(by_initiative.values()) else "PARTIAL"
    return {
        "status": status,
        "source": _source_meta(source),
        "by_initiative": by_initiative,
        "limitations": [] if status == "AVAILABLE" else ["NO_LINKED_EVIDENCE_PRESENT"],
    }


def enrich_snapshot(snapshot: dict[str, Any], coverage_bundle: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(snapshot)
    portfolio = build_portfolio_coverage(coverage_bundle.get("lifecycle_registry", {}))
    initiative_ids = [item["object_id"] for item in portfolio["comparable_initiatives"]]
    evidence = build_evidence_inventory(coverage_bundle.get("evidence_registry", {}), initiative_ids)
    result["contract_version"] = "1.2.0"
    result["coverage"] = {
        "schema_version": "coi-coverage-extension.v1",
        "contract_version": "1.0.0",
        "generated_at": coverage_bundle["retrieved_at"],
        "authority_mode": COVERAGE_AUTHORITY,
        "portfolio": portfolio,
        "initiative_evidence": evidence,
        "limitations": sorted(set(portfolio["limitations"] + evidence["limitations"])),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich RM-COI-001 with bounded M6-R2 portfolio/evidence coverage.")
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("coverage_bundle", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    bundle = json.loads(args.coverage_bundle.read_text(encoding="utf-8"))
    output = enrich_snapshot(snapshot, bundle)
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
