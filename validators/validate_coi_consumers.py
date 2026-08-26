#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from tools.coi_readers import read_bundle
from tools.coi_materializer import materialize
from tools.coi_consumers import quick_lookup, executive_snapshot, evidence_trace

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


def main() -> int:
    schemas, registry = load_registry()
    mapping = yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8"))
    bundle = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    snapshot = materialize(read_bundle(mapping, bundle))

    snapshot_errors = validate(snapshot, schemas["materialized-snapshot.schema.json"], registry)
    if snapshot_errors:
        for error in snapshot_errors:
            print(f"ERROR snapshot {list(error.absolute_path)}: {error.message}")
        return 1

    object_id = "Dashboard singleton"
    concept = "FUNDING_PREDICTABLE_MONTHLY_COVERAGE"
    lookup = quick_lookup(snapshot, object_id, concept)
    executive = executive_snapshot(snapshot)
    trace = evidence_trace(snapshot, f"{object_id}::{concept}")

    for name, output in [("lookup", lookup), ("executive", executive), ("trace", trace)]:
        errors = validate(output, schemas["consumer-output.schema.json"], registry)
        if errors:
            for error in errors:
                print(f"ERROR {name} {list(error.absolute_path)}: {error.message}")
            return 1
        if output["read_model_id"] != snapshot["read_model_id"] or output["snapshot_as_of"] != snapshot["as_of"]:
            print(f"ERROR {name}: snapshot identity/as-of changed")
            return 1
        if output["authority_mode"] != "DERIVED_NON_AUTHORITATIVE":
            print(f"ERROR {name}: consumer elevated authority")
            return 1

    if lookup["status"] != "FOUND" or lookup["fact"]["value_state"] != "UNKNOWN" or "value" in lookup["fact"]:
        print("ERROR quick lookup unknown integrity failed")
        return 1

    executive_fact = next(
        fact for fact in executive["sections"]["FH-CF-01"]
        if fact["fact_key"] == lookup["fact"]["fact_key"]
    )
    traced_fact = trace["trace"]["fact"]
    if executive_fact != lookup["fact"] or traced_fact != lookup["fact"]:
        print("ERROR consumers do not expose the same governed fact representation")
        return 1

    if not trace["trace"]["source_envelopes"]:
        print("ERROR evidence trace did not resolve source envelope")
        return 1
    if set(lookup["fact"]["source_refs"]) != {item["source_ref"] for item in trace["trace"]["source_envelopes"]}:
        print("ERROR evidence trace source refs differ from fact provenance")
        return 1

    not_found = quick_lookup(snapshot, "NO-SUCH-OBJECT", "NO_SUCH_CONCEPT")
    if not_found["status"] != "NOT_FOUND" or not_found["fact"] is not None:
        print("ERROR bounded not-found behavior failed")
        return 1

    required_metadata = ["semantic_class","value_state","authority","provenance","freshness","limitations","drill_through_ref"]
    missing = [field for field in required_metadata if field not in lookup["fact"]]
    if missing:
        print("ERROR consumer fact lost metadata: " + ", ".join(missing))
        return 1

    print("PASS: Quick Lookup consumes RM-COI-001 only and preserves governed fact semantics")
    print("PASS: Executive Snapshot groups the same immutable fact index without source reinterpretation")
    print("PASS: Evidence Trace resolves fact -> record -> source envelope using preserved provenance")
    print("PASS: snapshot identity/as-of, freshness, authority, limitations and drill-through metadata are preserved")
    print("PASS: UNKNOWN remains valueless across all three consumers")
    print("PASS: not-found is bounded and does not invent facts")
    print("PASS: consumer authority remains DERIVED_NON_AUTHORITATIVE")
    print("PASS: local validation requires no GitHub Actions, DB, runtime or UI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
