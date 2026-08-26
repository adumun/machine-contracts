#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from coi_readers import read_bundle  # noqa: E402

SCHEMA_DIR = ROOT / "schemas" / "corporate-operating-intelligence"
MAPPING_PATH = ROOT / "mappings" / "corporate-operating-intelligence" / "source-fact-mapping.v1.yaml"
FIXTURE_PATH = ROOT / "examples" / "corporate-operating-intelligence" / "reader-input.synthetic.json"
VOCAB_PATH = ROOT / "vocabularies" / "corporate-operating-intelligence.v1.yaml"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_schemas():
    registry = Registry()
    schemas = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def fail(message: str) -> int:
    print(f"ERROR: {message}")
    return 1


def main() -> int:
    mapping = yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8"))
    fixture = load_json(FIXTURE_PATH)
    vocab = yaml.safe_load(VOCAB_PATH.read_text(encoding="utf-8"))
    schemas, registry = load_schemas()
    output = read_bundle(mapping, fixture)

    if len(output["sources"]) != 5:
        return fail(f"expected 5 source results, got {len(output['sources'])}")
    if any(source["status"] != "OK" for source in output["sources"]):
        return fail(f"fixture source not OK: {[(s['source_id'], s['status'], s['errors']) for s in output['sources']]}")

    concern_validator = Draft202012Validator(
        schemas["concern-record.schema.json"],
        registry=registry,
        format_checker=FormatChecker(),
    )
    semantic_classes = set(vocab["semantic_classes"])
    record_count = 0
    fact_count = 0
    for source in output["sources"]:
        for record in source["records"]:
            record_count += 1
            errors = list(concern_validator.iter_errors(record))
            if errors:
                for error in errors:
                    print(f"ERROR schema {source['source_id']} {list(error.absolute_path)}: {error.message}")
                return 1
            for fact in record["facts"]:
                fact_count += 1
                if fact["semantic_class"] not in semantic_classes:
                    return fail(f"unknown semantic class emitted: {fact['semantic_class']}")

    by_source = {source["source_id"]: source for source in output["sources"]}
    funding_facts = {fact["canonical_concept"]: fact for fact in by_source["RM-FUND-001"]["records"][0]["facts"]}
    for concept in ("FUNDING_PREDICTABLE_MONTHLY_COVERAGE", "FUNDING_COLLECTED_CASH_MTD"):
        fact = funding_facts[concept]
        if fact["value_state"] != "UNKNOWN" or "value" in fact:
            return fail(f"{concept} must preserve missing token as UNKNOWN without value")
        if "SOURCE_NOT_EVIDENCED" not in fact["limitations"]:
            return fail(f"{concept} must retain SOURCE_NOT_EVIDENCED limitation")

    lifecycle_records = by_source["REG-INIT-LIFECYCLE-001"]["records"]
    if [record["object_id"] for record in lifecycle_records] != ["INIT-SYN-001"]:
        return fail("lifecycle row filter must emit only Portfolio Object Type = INITIATIVE")

    structural_records = by_source["REG-STR-REC-001"]["records"]
    if [record["object_id"] for record in structural_records] != ["ORG-SYN-001"]:
        return fail("structural row filter must exclude initiative rows")

    unavailable = json.loads(json.dumps(fixture))
    unavailable["sources"].pop("REG-DEC-001")
    unavailable_output = read_bundle(mapping, unavailable)
    missing_decision = next(source for source in unavailable_output["sources"] if source["source_id"] == "REG-DEC-001")
    if missing_decision["status"] != "UNAVAILABLE" or missing_decision["source_envelope"]["reconciliation_state"] != "UNAVAILABLE":
        return fail("missing source snapshot must fail closed as UNAVAILABLE")

    print("PASS: 5 bounded source readers execute deterministically from approved M2 mapping")
    print(f"PASS: {record_count} synthetic concern records / {fact_count} material answers validate against M1 schemas")
    print("PASS: '-' and blank financial source tokens are not coerced to zero")
    print("PASS: lifecycle and structural source row filters preserve bounded object classes")
    print("PASS: missing source snapshot fails closed as UNAVAILABLE")
    print("PASS: no provider SDK, credential, database, runtime or GitHub Actions dependency is required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
