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
}
NON_LIFECYCLE_STATES = {"RECONCILIATION_REQUIRED", "INCUBATE", "INCUBATION"}
READY_OR_LATER = {"READY", "IN_PROGRESS", "BLOCKED", "IN_REVIEW", "DONE"}


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
            errors.append(
                f"stage {stage.get('stage_id')}: {state} is not a canonical lifecycle state"
            )
        for collection, expected_direction in (("inputs", "INPUT"), ("outputs", "OUTPUT")):
            for artifact in stage.get(collection, []):
                artifact_id = artifact.get("artifact_id")
                if artifact_id in artifact_ids:
                    errors.append(f"artifact_id {artifact_id}: duplicate stable ID")
                artifact_ids.add(artifact_id)
                if artifact.get("direction") != expected_direction:
                    errors.append(
                        f"artifact {artifact_id}: {collection} must use direction {expected_direction}"
                    )
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
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--schema", choices=sorted(SCHEMAS))
    parser.add_argument(
        "--expect-invalid",
        action="store_true",
        help="Succeed only when every supplied document is invalid.",
    )
    args = parser.parse_args()

    failures = 0
    for path in args.paths:
        try:
            errors = validate(path, args.schema)
        except Exception as exc:  # fail closed on unreadable/ambiguous input
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
