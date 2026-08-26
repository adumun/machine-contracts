#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from tools.coi_readers import read_bundle
from tools.coi_materializer import materialize, quick_lookup, executive_briefing_projection, static_view_projection

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
    return sorted(
        Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )


def main() -> int:
    schemas, registry = load_registry()
    mapping = yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8"))
    bundle = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    reader_output = read_bundle(mapping, bundle)
    if not all(item["status"] == "OK" for item in reader_output["sources"]):
        print("ERROR: synthetic M2 reader output is not fully OK")
        return 1

    first = materialize(reader_output)
    second = materialize(copy.deepcopy(reader_output))
    if first != second:
        print("ERROR: materialization is not deterministic for identical input")
        return 1

    errors = validate(first, schemas["materialized-snapshot.schema.json"], registry)
    if errors:
        for error in errors:
            print(f"ERROR snapshot {list(error.absolute_path)}: {error.message}")
        return 1

    fact_count = sum(len(record["facts"]) for record in first["records"])
    if fact_count != len(first["fact_index"]):
        print("ERROR: fact index count differs from governed facts")
        return 1

    if first["authority_mode"] != "DERIVED_NON_AUTHORITATIVE":
        print("ERROR: materialized read model elevated authority")
        return 1

    for item in first["fact_index"]:
        if item["value_state"] != "KNOWN" and "value" in item:
            print(f"ERROR: non-KNOWN fact exposes a value: {item['fact_key']}")
            return 1

    funding_unknown = quick_lookup(first, "Dashboard singleton", "FUNDING_PREDICTABLE_MONTHLY_COVERAGE")
    if not funding_unknown or funding_unknown["value_state"] != "UNKNOWN" or "value" in funding_unknown:
        print("ERROR: predictable coverage unknown integrity failed")
        return 1

    briefing = executive_briefing_projection(first)
    funding_static = static_view_projection(first, "FH-CF-01")
    funding_static_lookup = next(
        item for item in funding_static
        if item["fact_key"] == funding_unknown["fact_key"]
    )
    if funding_static_lookup != funding_unknown:
        print("ERROR: consumers observe different governed fact representations")
        return 1
    if briefing["read_model_id"] != first["read_model_id"] or briefing["as_of"] != first["as_of"]:
        print("ERROR: briefing projection lost snapshot identity/as-of")
        return 1

    degraded_bundle = copy.deepcopy(bundle)
    del degraded_bundle["sources"]["REG-RM-001"]
    degraded_reader = read_bundle(mapping, degraded_bundle)
    degraded = materialize(degraded_reader)
    if degraded["source_status_summary"]["unavailable"] != 1:
        print("ERROR: unavailable source not surfaced")
        return 1
    if degraded["reconciliation_state"] != "RECONCILIATION_REQUIRED":
        print("ERROR: degraded materialized snapshot did not require reconciliation")
        return 1

    print(f"PASS: materialized snapshot schema valid with {len(first['records'])} records / {len(first['fact_index'])} indexed facts")
    print("PASS: identical M2 input rebuilds byte-equivalent logical snapshot")
    print("PASS: read model remains DERIVED_NON_AUTHORITATIVE")
    print("PASS: UNKNOWN facts remain valueless in materialized index")
    print("PASS: Quick Lookup, Executive Briefing and Static View consume the same snapshot identity/facts")
    print("PASS: missing source degrades to RECONCILIATION_REQUIRED without invented data")
    print("PASS: local validation requires no GitHub Actions or paid runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
