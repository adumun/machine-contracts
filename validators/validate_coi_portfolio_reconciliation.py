#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from scripts.reconcile_portfolio_objects import reconcile

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "corporate-operating-intelligence" / "portfolio-reconciliation.synthetic.json"
POLICY = ROOT / "policies" / "corporate-operating-intelligence" / "portfolio-reconciliation-policy.v1.yaml"
SCHEMA = ROOT / "schemas" / "corporate-operating-intelligence" / "portfolio-reconciliation-proposal.schema.json"


def main() -> int:
    snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))
    policy = yaml.safe_load(POLICY.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    first = reconcile(snapshot, policy)
    second = reconcile(snapshot, policy)
    if first != second:
        print("ERROR reconciliation output is not deterministic")
        return 1

    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(first))
    if errors:
        for error in errors:
            print(f"ERROR proposal {list(error.absolute_path)}: {error.message}")
        return 1

    by_label = {item["label"]: item for item in first["proposals"]}
    if by_label["Nexus Community Ecosystem"]["disposition"] != "REQUIRES_GOVERNANCE":
        print("ERROR explicit Nexus authoritative claims should produce REQUIRES_GOVERNANCE")
        return 1
    if by_label["Nexus Community Ecosystem"]["proposed"].get("portfolio_object_type") != "INITIATIVE":
        print("ERROR explicit portfolio object type was not copied")
        return 1
    if by_label["UNLOCKED"]["disposition"] != "INSUFFICIENT_EVIDENCE":
        print("ERROR missing object type/id must remain INSUFFICIENT_EVIDENCE")
        return 1
    if by_label["Rent a Car Management System"]["disposition"] != "CONFLICT":
        print("ERROR conflicting authoritative claims must fail closed as CONFLICT")
        return 1
    if by_label["ADÜMÜN Control Center"]["disposition"] != "NO_CHANGE":
        print("ERROR matching authoritative state should produce NO_CHANGE")
        return 1
    if first["authority_mode"] != "DERIVED_NON_AUTHORITATIVE" or first["mode"] != "PROPOSAL_ONLY":
        print("ERROR reconciliation proposal elevated authority or apply mode")
        return 1
    if policy.get("safe_apply_enabled") is not False:
        print("ERROR R1 policy must prohibit safe apply")
        return 1

    raw = json.dumps(first, ensure_ascii=False).lower()
    for forbidden in ["completion_percent", "eta_days", "success_probability", "revenue_forecast"]:
        if forbidden in raw:
            print(f"ERROR forbidden inferred semantic leaked: {forbidden}")
            return 1

    print("PASS: portfolio reconciliation R1 is deterministic and schema-valid")
    print("PASS: explicit authoritative claims can produce governance proposals without auto-apply")
    print("PASS: missing material identity remains INSUFFICIENT_EVIDENCE")
    print("PASS: conflicting authoritative claims fail closed as CONFLICT")
    print("PASS: matching current state produces NO_CHANGE")
    print("PASS: reconciliation output remains DERIVED_NON_AUTHORITATIVE / PROPOSAL_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
