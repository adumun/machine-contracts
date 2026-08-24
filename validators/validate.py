#!/usr/bin/env python3
"""Local deterministic validator for ADÜMÜN machine contracts.

This validator intentionally runs locally and does not depend on GitHub Actions.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "work-item": ROOT / "schemas" / "work-management" / "work-item.schema.json",
    "workflow-contract": ROOT / "schemas" / "workflow" / "workflow-contract.schema.json",
}


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


def validate(path: Path, schema_name: str | None = None) -> list[str]:
    document = load_json(path)
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
