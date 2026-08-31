#!/usr/bin/env python3
"""ADUMUN Machine Contracts deterministic conformance fixture runner."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from validators.validate import validate

ROOT = Path(__file__).resolve().parents[1]


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh) if path.suffix.lower() == ".json" else yaml.safe_load(fh)


def run_case(case: dict) -> tuple[bool, str]:
    path = ROOT / case["path"]
    schema = case.get("schema")
    expected = case.get("expected", "valid")
    errors = validate(path, schema)
    ok = (not errors) if expected == "valid" else bool(errors)
    if ok:
        detail = "PASS"
    elif expected == "valid":
        detail = "unexpected validation errors: " + "; ".join(errors)
    else:
        detail = "expected invalid but validation passed"
    return ok, f'{case["id"]}: {detail}'


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ADUMUN machine-contract conformance fixtures")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "conformance" / "core-fixtures.yaml",
        help="fixture manifest relative to repository root or absolute path",
    )
    args = parser.parse_args()
    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    manifest = load_manifest(manifest_path)
    cases = manifest.get("cases", [])
    failures = 0
    for case in cases:
        try:
            ok, message = run_case(case)
        except Exception as exc:  # fail closed: malformed fixture/configuration is a failed gate
            ok, message = False, f'{case.get("id", "UNKNOWN")}: ERROR {exc}'
        print(message)
        failures += 0 if ok else 1
    passed = len(cases) - failures
    print(f'{"PASS" if failures == 0 else "FAIL"}: {passed}/{len(cases)} conformance fixtures')
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
