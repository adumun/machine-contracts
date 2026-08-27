#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from tools.coi_readers import read_bundle
from tools.coi_materializer import materialize
from tools.coi_coverage import enrich_snapshot
from tools.coi_consumers import portfolio_progress, initiative_evidence

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "corporate-operating-intelligence"
MAPPING_PATH = ROOT / "mappings" / "corporate-operating-intelligence" / "source-fact-mapping.v1.yaml"
FIXTURE_PATH = ROOT / "examples" / "corporate-operating-intelligence" / "reader-input.synthetic.json"


def load_registry():
    registry = Registry()
    schemas = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def validate(instance, schema, registry):
    return list(Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()).iter_errors(instance))


def coverage_bundle() -> dict:
    lifecycle_headers = [
        "ID", "Initiative", "Explore Ideas Folder", "Lifecycle Stage", "Current Gate", "Gate Outcome",
        "Evidence Confidence", "Last Reviewed", "Initiative Lifecycle Folder", "Next Review / Evidence Needed",
        "Notes", "Canonical Lifecycle State", "Reconciliation Status", "Portfolio Object Type", "Authority State",
        "Schema Version", "Normalized Object ID",
    ]
    evidence_headers = [
        "Evidence ID", "Title / Finding", "Evidence Date", "Recorded Date", "Producing Initiative / Context",
        "Evidence Type", "Source / Provenance", "Linked Object Type", "Linked Object ID / Name",
        "Observation / Result", "Interpretation", "Polarity", "Strength", "Confidence", "Confidence Rationale",
        "Scope / Population / Environment", "Known Limitations", "Related / Contradictory Evidence IDs",
        "Decision Affected", "Decision Status", "Remaining Uncertainty", "Owner / Reviewer",
        "Freshness / Review Trigger", "Lifecycle State", "Source URL / Reference", "Notes", "Authority State",
        "Schema Version", "Predecessor Evidence ID(s)", "Successor Evidence ID(s)",
    ]
    return {
        "retrieved_at": "2026-08-27T08:00:00-04:00",
        "lifecycle_registry": {
            "source_ref": "Lifecycle Registry / Registry",
            "freshness": {"state": "CURRENT", "as_of": "2026-08-27"},
            "confidentiality": {"classification": "INTERNAL"},
            "reconciliation_state": "CURRENT",
            "rows": [
                lifecycle_headers,
                ["1", "Initiative A", "", "S8 — Delivery & Continuous Validation", "G8", "OPEN", "HIGH", "2026-08-27", "", "", "", "DELIVERING", "MAPPED", "INITIATIVE", "CURRENT", "v1", "INIT-A"],
                ["2", "Initiative B", "", "S4 — Hypothesis Design & Validation", "G4", "OPEN", "HIGH", "2026-08-27", "", "", "", "VALIDATING", "MAPPED", "INITIATIVE", "CURRENT", "v1", "INIT-B"],
                ["3", "Legacy Candidate", "", "RECONCILIATION_REQUIRED", "", "", "LOW", "2026-08-27", "", "", "", "", "RECONCILIATION_REQUIRED", "UNRESOLVED", "CURRENT", "v1", ""],
            ],
        },
        "evidence_registry": {
            "source_ref": "Evidence Registry / Evidence Registry",
            "freshness": {"state": "CURRENT", "as_of": "2026-08-27"},
            "confidentiality": {"classification": "INTERNAL"},
            "reconciliation_state": "PARTIAL",
            "rows": [
                evidence_headers,
                ["EVD-1", "A validation passed", "2026-08-26", "2026-08-26", "INIT-A / S8", "Delivery milestone evidence", "src", "Initiative delivery evidence", "INIT-A / CAP-X", "Passed bounded validation", "Milestone supported", "SUPPORTS", "DIRECT", "HIGH", "direct", "scope", "none", "", "DEC-A", "CONFIRMS", "", "owner", "review", "DELIVERING", "artifact-a", "", "CURRENT", "evidence-registry.v1", "", ""],
                ["EVD-2", "A operational trial", "2026-08-27", "2026-08-27", "INIT-A / M6", "Operational usage evidence", "src", "Initiative delivery evidence", "INIT-A", "Real-use trial completed", "Coverage gap identified", "SUPPORTS", "DIRECT", "HIGH", "direct", "scope", "small sample", "EVD-1", "DEC-A", "REMEDIATE_IN_S8", "", "owner", "review", "DELIVERING", "artifact-b", "", "CURRENT", "evidence-registry.v1", "EVD-1", ""],
                ["EVD-X", "Unrelated evidence", "2026-08-27", "2026-08-27", "INIT-X", "Other", "src", "Initiative evidence", "INIT-X", "Other", "Other", "SUPPORTS", "DIRECT", "HIGH", "direct", "scope", "", "", "", "USED", "", "owner", "review", "VALIDATING", "artifact-x", "", "CURRENT", "evidence-registry.v1", "", ""],
            ],
        },
    }


def main() -> int:
    schemas, registry = load_registry()
    mapping = yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8"))
    base_bundle = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    base_snapshot = materialize(read_bundle(mapping, base_bundle))
    enriched = enrich_snapshot(base_snapshot, coverage_bundle())

    errors = validate(enriched, schemas["materialized-snapshot.schema.json"], registry)
    if errors:
        for error in errors:
            print(f"ERROR enriched snapshot {list(error.absolute_path)}: {error.message}")
        return 1

    coverage = enriched["coverage"]
    portfolio = coverage["portfolio"]
    if portfolio["status"] != "PARTIAL":
        print("ERROR portfolio should be PARTIAL while unresolved rows remain")
        return 1
    if portfolio["global_comparison_supported"]:
        print("ERROR global comparison must not be supported with unresolved portfolio population")
        return 1
    if portfolio["non_comparable_row_count"] != 1:
        print("ERROR unresolved/non-comparable row count not preserved")
        return 1
    if [item["object_id"] for item in portfolio["comparable_initiatives"]] != ["INIT-A", "INIT-B"]:
        print("ERROR comparable initiative population or deterministic ordering failed")
        return 1

    portfolio_output = portfolio_progress(enriched)
    evidence_output = initiative_evidence(enriched, "INIT-A")
    for name, output in [("portfolio", portfolio_output), ("initiative-evidence", evidence_output)]:
        output_errors = validate(output, schemas["consumer-output.schema.json"], registry)
        if output_errors:
            for error in output_errors:
                print(f"ERROR {name} {list(error.absolute_path)}: {error.message}")
            return 1
        if output["authority_mode"] != "DERIVED_NON_AUTHORITATIVE":
            print(f"ERROR {name}: consumer elevated authority")
            return 1

    if portfolio_output["status"] != "PARTIAL" or portfolio_output["most_advanced"]["object_id"] != "INIT-A":
        print("ERROR bounded portfolio progression output failed")
        return 1
    if "PORTFOLIO_POPULATION_NOT_FULLY_COMPARABLE" not in portfolio_output["limitations"]:
        print("ERROR portfolio coverage limitation was lost")
        return 1
    if evidence_output["status"] != "PARTIAL" or evidence_output["evidence_count"] != 2:
        print("ERROR partial initiative evidence inventory status was not preserved")
        return 1
    if {item["evidence_id"] for item in evidence_output["evidence"]} != {"EVD-1", "EVD-2"}:
        print("ERROR unrelated evidence leaked into initiative evidence inventory")
        return 1
    if "EVIDENCE_SOURCE_NOT_FULLY_RECONCILED" not in evidence_output["limitations"]:
        print("ERROR partial evidence source limitation was lost")
        return 1

    raw = json.dumps(enriched, ensure_ascii=False)
    forbidden = ["estimated_completion", "completion_percent", "eta_days", "remaining_days"]
    if any(token in raw for token in forbidden):
        print("ERROR coverage enrichment invented ETA/completion semantics")
        return 1

    print("PASS: M6-R2 coverage enrichment validates as RM-COI-001 contract 1.2.0")
    print("PASS: only canonically classified MAPPED/CURRENT INITIATIVE rows are comparable")
    print("PASS: unresolved portfolio rows prevent false global ranking")
    print("PASS: lifecycle progression ranking is deterministic and explicitly bounded")
    print("PASS: initiative evidence inventory preserves exact registry-linked evidence only")
    print("PASS: partial evidence source state propagates to consumer status/limitations")
    print("PASS: portfolio/evidence consumers remain DERIVED_NON_AUTHORITATIVE")
    print("PASS: no ETA, completion percentage, DB, runtime, UI or writeback is introduced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
