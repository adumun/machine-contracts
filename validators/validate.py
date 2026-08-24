#!/usr/bin/env python3
"""Local deterministic validator for ADÜMÜN machine contracts.

Runs locally and does not depend on GitHub Actions. Structural validation uses
JSON Schema; semantic validation enforces provider-neutral governance invariants
that are awkward or inappropriate to encode as JSON Schema alone.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "work-item": ROOT / "schemas" / "work-management" / "work-item.schema.json",
    "workflow-contract": ROOT / "schemas" / "workflow" / "workflow-contract.schema.json",
    "provider-mapping": ROOT / "schemas" / "provider-mapping" / "provider-mapping.schema.json",
}
NON_LIFECYCLE_STATES = {"RECONCILIATION_REQUIRED", "INCUBATE", "INCUBATION"}
READY_OR_LATER = {"READY", "IN_PROGRESS", "BLOCKED", "IN_REVIEW", "DONE"}
WORK_TYPES = {"STORY", "BUG", "TASK", "SPIKE", "EXPERIMENT", "TECHNICAL_DEBT", "INCIDENT"}
WORK_STATES = {"PROPOSED", "REFINING", "READY", "IN_PROGRESS", "BLOCKED", "IN_REVIEW", "DONE", "CANCELED", "DEFERRED"}
WORK_FIELDS = {"work_id", "title", "type", "category", "areas", "source", "priority", "severity", "state", "owner", "acceptance_criteria", "evidence_refs", "provider_refs", "reclassification"}


def load_document(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(fh)
        return json.load(fh)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def infer_schema(document: dict) -> str:
    version = document.get("schema_version", "")
    if version.startswith("work-item."):
        return "work-item"
    if version.startswith("workflow-contract."):
        return "workflow-contract"
    if version.startswith("provider-mapping."):
        return "provider-mapping"
    raise ValueError(f"Cannot infer schema from schema_version={version!r}")


def semantic_work_item(document: dict) -> list[str]:
    errors: list[str] = []
    state = document.get("state")
    if state in READY_OR_LATER:
        if not document.get("owner"):
            errors.append("owner: required when work is READY or later")
        if not document.get("acceptance_criteria"):
            errors.append("acceptance_criteria: required when work is READY or later")
    if state == "DONE" and not document.get("evidence_refs"):
        errors.append("evidence_refs: DONE requires retained completion evidence")

    reclassification = document.get("reclassification")
    if reclassification:
        from_type = reclassification.get("from_type")
        to_type = reclassification.get("to_type")
        if from_type == to_type:
            errors.append("reclassification: from_type and to_type must differ")
        if to_type != document.get("type"):
            errors.append("reclassification.to_type: must equal current canonical type")
    return errors


def semantic_workflow(document: dict) -> list[str]:
    errors: list[str] = []
    stages = document.get("stages", [])
    stage_ids = [stage.get("stage_id") for stage in stages]
    if len(stage_ids) != len(set(stage_ids)):
        errors.append("stages: duplicate stage_id values are forbidden")
    known_stages = set(stage_ids)

    artifact_ids: set[str] = set()
    for stage in stages:
        state = stage.get("canonical_state")
        if state in NON_LIFECYCLE_STATES:
            errors.append(f"stage {stage.get('stage_id')}: {state} is not a canonical lifecycle state")
        for collection, expected_direction in (("inputs", "INPUT"), ("outputs", "OUTPUT")):
            for artifact in stage.get(collection, []):
                artifact_id = artifact.get("artifact_id")
                if artifact_id in artifact_ids:
                    errors.append(f"artifact_id {artifact_id}: duplicate stable ID")
                artifact_ids.add(artifact_id)
                if artifact.get("direction") != expected_direction:
                    errors.append(f"artifact {artifact_id}: {collection} must use direction {expected_direction}")
                if artifact.get("requirement") == "CONDITIONAL" and not artifact.get("condition"):
                    errors.append(f"artifact {artifact_id}: CONDITIONAL requires condition")

    transition_ids: set[str] = set()
    for transition in document.get("transitions", []):
        transition_id = transition.get("transition_id")
        if transition_id in transition_ids:
            errors.append(f"transition_id {transition_id}: duplicate stable ID")
        transition_ids.add(transition_id)
        if transition.get("source") not in known_stages:
            errors.append(f"transition {transition_id}: unknown source stage {transition.get('source')}")
        if transition.get("target") not in known_stages:
            errors.append(f"transition {transition_id}: unknown target stage {transition.get('target')}")
        if transition.get("source") == transition.get("target"):
            errors.append(f"transition {transition_id}: source and target must differ")
    return errors


def _unique_mapping(errors: list[str], mappings: list[dict], field: str, label: str) -> None:
    values = [m.get(field) for m in mappings]
    duplicates = sorted({v for v in values if v is not None and values.count(v) > 1})
    for value in duplicates:
        errors.append(f"{label}: duplicate {field} mapping {value}")


def semantic_provider_mapping(document: dict) -> list[str]:
    errors: list[str] = []
    types = document.get("work_type_mappings", [])
    states = document.get("state_mappings", [])
    fields = document.get("field_mappings", [])

    _unique_mapping(errors, types, "canonical", "work_type_mappings")
    _unique_mapping(errors, types, "provider", "work_type_mappings")
    _unique_mapping(errors, states, "canonical", "state_mappings")
    _unique_mapping(errors, states, "provider", "state_mappings")
    _unique_mapping(errors, fields, "canonical_field", "field_mappings")

    for mapping in types:
        if mapping.get("canonical") not in WORK_TYPES:
            errors.append(f"work_type_mappings: unknown canonical type {mapping.get('canonical')}")
        if mapping.get("lossy") and not mapping.get("notes"):
            errors.append(f"work_type_mappings: lossy mapping {mapping.get('canonical')} requires notes")

    for mapping in states:
        if mapping.get("canonical") not in WORK_STATES:
            errors.append(f"state_mappings: unknown canonical state {mapping.get('canonical')}")
        if mapping.get("lossy") and not mapping.get("notes"):
            errors.append(f"state_mappings: lossy mapping {mapping.get('canonical')} requires notes")

    for mapping in fields:
        if mapping.get("canonical_field") not in WORK_FIELDS:
            errors.append(f"field_mappings: unknown canonical field {mapping.get('canonical_field')}")

    for transition in document.get("transition_mappings", []):
        source = transition.get("canonical_from")
        target = transition.get("canonical_to")
        if source not in WORK_STATES or target not in WORK_STATES:
            errors.append(f"transition_mappings: unknown canonical transition {source}->{target}")
        if source == target:
            errors.append(f"transition_mappings: source and target must differ for {source}->{target}")
        if transition.get("guards_preserved") is not True:
            errors.append(f"transition_mappings: {source}->{target} must preserve canonical guards or remain unmapped")

    return errors


def validate(path: Path, schema_name: str | None = None) -> list[str]:
    document = load_document(path)
    if not isinstance(document, dict):
        raise ValueError("top-level document must be an object/map")
    name = schema_name or infer_schema(document)
    schema_path = SCHEMAS.get(name)
    if not schema_path:
        raise ValueError(f"Unknown schema {name!r}. Available: {', '.join(sorted(SCHEMAS))}")
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.path)):
        location = ".".join(str(x) for x in error.absolute_path) or "$"
        errors.append(f"{location}: {error.message}")

    if name == "work-item":
        errors.extend(semantic_work_item(document))
    elif name == "workflow-contract":
        errors.extend(semantic_workflow(document))
    elif name == "provider-mapping":
        errors.extend(semantic_provider_mapping(document))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--schema", choices=sorted(SCHEMAS))
    parser.add_argument("--expect-invalid", action="store_true", help="Succeed only when every supplied document is invalid.")
    args = parser.parse_args()

    failures = 0
    for path in args.paths:
        try:
            errors = validate(path, args.schema)
        except Exception as exc:
            print(f"ERROR {path}: {exc}")
            failures += 1
            continue

        if args.expect_invalid:
            if errors:
                print(f"PASS (invalid as expected) {path}")
                for error in errors:
                    print(f"  - {error}")
            else:
                print(f"FAIL {path}: expected invalid, but validation passed")
                failures += 1
        else:
            if errors:
                print(f"FAIL {path}")
                for error in errors:
                    print(f"  - {error}")
                failures += 1
            else:
                print(f"PASS {path}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
