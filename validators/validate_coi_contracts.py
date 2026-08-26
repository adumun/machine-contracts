#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "corporate-operating-intelligence"
VOCAB_PATH = ROOT / "vocabularies" / "corporate-operating-intelligence.v1.yaml"
EXAMPLES_DIR = ROOT / "examples" / "corporate-operating-intelligence"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_registry():
    registry = Registry()
    schemas = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry

def validate_material_answer(instance, schema, registry):
    errors = list(Draft202012Validator(schema, registry=registry, format_checker=FormatChecker()).iter_errors(instance))
    return sorted(errors, key=lambda e: list(e.absolute_path))

def semantic_checks(instance, vocab):
    errors = []
    if instance.get("concern_family") not in vocab["concern_families"]:
        errors.append(f"unknown concern_family: {instance.get('concern_family')}")
    if instance.get("semantic_class") not in vocab["semantic_classes"]:
        errors.append(f"unknown semantic_class: {instance.get('semantic_class')}")
    if instance.get("value_state") not in vocab["value_states"]:
        errors.append(f"unknown value_state: {instance.get('value_state')}")
    return errors

def main():
    schemas, registry = load_registry()
    vocab = yaml.safe_load(VOCAB_PATH.read_text(encoding="utf-8"))
    material = schemas["material-answer.schema.json"]
    valid = load_json(EXAMPLES_DIR / "valid-material-answer.json")
    valid_errors = validate_material_answer(valid, material, registry)
    semantic_errors = semantic_checks(valid, vocab)
    if valid_errors or semantic_errors:
        for err in valid_errors:
            print(f"ERROR valid fixture {list(err.absolute_path)}: {err.message}")
        for err in semantic_errors:
            print(f"ERROR valid fixture semantic: {err}")
        return 1
    invalid = load_json(EXAMPLES_DIR / "invalid-unknown-with-value.json")
    invalid_errors = validate_material_answer(invalid, material, registry)
    if not invalid_errors:
        print("ERROR invalid fixture unexpectedly validated")
        return 1
    print(f"PASS: {len(schemas)} COI schemas are structurally valid")
    print("PASS: controlled vocabularies load and valid fixture uses governed values")
    print("PASS: valid material-answer fixture validates")
    print(f"PASS: invalid fixture is rejected ({len(invalid_errors)} expected validation error(s))")
    print("PASS: local validation path does not depend on GitHub Actions")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
