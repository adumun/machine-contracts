#!/usr/bin/env python3
"""Validate final legacy-registry cutover artifacts locally without GitHub Actions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = [
    ROOT / "schemas/contracts/contract-authority-index.schema.json",
    ROOT / "schemas/governance/repository-registry.schema.json",
    ROOT / "schemas/governance/relationship-registry.schema.json",
    ROOT / "schemas/governance/standards-registry.schema.json",
]
INDEX = ROOT / "registries/contract-authority-index.yaml"


def main() -> int:
    failures = 0
    for path in SCHEMAS:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            print(f"PASS schema {path.relative_to(ROOT)}")
        except Exception as exc:
            print(f"FAIL schema {path.relative_to(ROOT)}: {exc}")
            failures += 1

    try:
        index = yaml.safe_load(INDEX.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMAS[0].read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(index), key=lambda e: list(e.path))
        if errors:
            print(f"FAIL {INDEX.relative_to(ROOT)}")
            for error in errors:
                loc = ".".join(str(p) for p in error.absolute_path) or "$"
                print(f"  - {loc}: {error.message}")
            failures += 1
        else:
            print(f"PASS {INDEX.relative_to(ROOT)}")
    except Exception as exc:
        print(f"FAIL authority index: {exc}")
        failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
