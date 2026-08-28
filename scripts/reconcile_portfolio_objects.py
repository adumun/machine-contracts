#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "policies" / "corporate-operating-intelligence" / "portfolio-reconciliation-policy.v1.yaml"

MATERIAL_FIELDS = {
    "portfolio_object_type": "PORTFOLIO_OBJECT_TYPE",
    "normalized_object_id": "NORMALIZED_OBJECT_ID",
    "canonical_lifecycle_state": "CANONICAL_LIFECYCLE_STATE",
    "lifecycle_stage": "LIFECYCLE_STAGE",
    "current_gate": "CURRENT_GATE",
    "gate_outcome": "GATE_OUTCOME",
}


def _eligible_claims(record: dict[str, Any], policy: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    accepted_modes = set(policy["authoritative_modes"])
    accepted_states = set(policy["accepted_authority_states"])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in record.get("claims", []):
        if claim.get("authority_mode") not in accepted_modes:
            continue
        if claim.get("authority_state") not in accepted_states:
            continue
        claim_type = str(claim.get("claim_type") or "")
        if claim_type in MATERIAL_FIELDS.values():
            grouped[claim_type].append(claim)
    return grouped


def _resolve_field(claims: list[dict[str, Any]]) -> tuple[str, Any | None, list[str]]:
    values = {str(c.get("value") or "").strip() for c in claims if str(c.get("value") or "").strip()}
    refs = sorted({str(c.get("source_ref") or "").strip() for c in claims if str(c.get("source_ref") or "").strip()})
    if not values:
        return "MISSING", None, refs
    if len(values) > 1:
        return "CONFLICT", None, refs
    return "RESOLVED", next(iter(values)), refs


def reconcile_record(record: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    current = dict(record.get("current") or {})
    grouped = _eligible_claims(record, policy)
    proposed: dict[str, Any] = {}
    reasons: list[str] = []
    evidence_refs: set[str] = set()
    conflict = False
    missing_material = False

    for field, claim_type in MATERIAL_FIELDS.items():
        state, value, refs = _resolve_field(grouped.get(claim_type, []))
        evidence_refs.update(refs)
        if state == "CONFLICT":
            conflict = True
            reasons.append(f"CONFLICTING_AUTHORITATIVE_CLAIMS:{field}")
        elif state == "RESOLVED":
            proposed[field] = value
        elif field in {"portfolio_object_type", "normalized_object_id"}:
            missing_material = True
            reasons.append(f"AUTHORITATIVE_CLAIM_MISSING:{field}")

    # Fail closed on identity/classification gaps before considering any other
    # otherwise-resolved lifecycle changes. Without both authoritative
    # portfolio object type and normalized object ID, the reconciler cannot
    # safely target a governed registry object.
    if conflict:
        disposition = "CONFLICT"
        proposed = {}
    elif missing_material:
        proposed = {}
        disposition = "INSUFFICIENT_EVIDENCE"
    else:
        material_changes = {
            k: v for k, v in proposed.items()
            if str(current.get(k) or "").strip() != str(v or "").strip()
        }
        if material_changes:
            proposed = material_changes
            disposition = "REQUIRES_GOVERNANCE"
            reasons.append("MATERIAL_REGISTRY_CHANGE_REQUIRES_GOVERNANCE")
        else:
            proposed = {}
            disposition = "NO_CHANGE"
            reasons.append("AUTHORITATIVE_STATE_ALREADY_MATCHES")

    return {
        "source_row_id": str(record["source_row_id"]),
        "label": str(record["label"]),
        "disposition": disposition,
        "current": current,
        "proposed": proposed,
        "reasons": sorted(set(reasons)) or ["NO_ACTIONABLE_CHANGE"],
        "evidence_refs": sorted(evidence_refs),
    }


def reconcile(snapshot: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    proposals = [reconcile_record(item, policy) for item in snapshot.get("objects", [])]
    proposals.sort(key=lambda item: (item["source_row_id"], item["label"]))
    counts = Counter(item["disposition"] for item in proposals)
    return {
        "schema_version": "coi-portfolio-reconciliation-proposal.v1",
        "contract_version": "1.0.0",
        "generated_at": snapshot["retrieved_at"],
        "authority_mode": "DERIVED_NON_AUTHORITATIVE",
        "mode": "PROPOSAL_ONLY",
        "source_snapshot_ref": snapshot.get("source_snapshot_ref"),
        "summary": {
            "objects_scanned": len(proposals),
            "requires_governance": counts["REQUIRES_GOVERNANCE"],
            "insufficient_evidence": counts["INSUFFICIENT_EVIDENCE"],
            "conflicts": counts["CONFLICT"],
            "no_change": counts["NO_CHANGE"],
        },
        "proposals": proposals,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministically propose portfolio reconciliation without mutating authoritative registries.")
    parser.add_argument("input", type=Path, help="Observed portfolio evidence snapshot JSON")
    parser.add_argument("-p", "--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    snapshot = json.loads(args.input.read_text(encoding="utf-8"))
    policy = yaml.safe_load(args.policy.read_text(encoding="utf-8"))
    if policy.get("mode") != "PROPOSAL_ONLY" or policy.get("safe_apply_enabled") is not False:
        raise SystemExit("policy must remain PROPOSAL_ONLY with safe_apply_enabled=false for R1")
    result = reconcile(snapshot, policy)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
