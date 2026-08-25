#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
RECORD_SCHEMA = json.loads((ROOT / 'schemas/decision-governance/decision-record.schema.json').read_text(encoding='utf-8'))
REGISTRY_SCHEMA = json.loads((ROOT / 'schemas/decision-governance/decision-registry.schema.json').read_text(encoding='utf-8'))


def validate(path: Path) -> list[str]:
    doc = json.loads(path.read_text(encoding='utf-8'))
    errors: list[str] = []
    if doc.get('schema_version') != 'decision-registry.v1':
        errors.append('schema_version must be decision-registry.v1')
    if not doc.get('registry_id'):
        errors.append('registry_id is required')
    if doc.get('status') not in {'CURRENT', 'DRAFT', 'HISTORICAL'}:
        errors.append('invalid registry status')
    decisions = doc.get('decisions')
    if not isinstance(decisions, list):
        return errors + ['decisions must be an array']

    ids: list[str | None] = []
    validator = Draft202012Validator(RECORD_SCHEMA)
    for idx, decision in enumerate(decisions):
        for error in validator.iter_errors(decision):
            path_text = '.'.join(str(x) for x in error.path) or '$'
            errors.append(f'decisions[{idx}].{path_text}: {error.message}')
        decision_id = decision.get('decision_id')
        ids.append(decision_id)
        if decision.get('authority_mode') == 'REGISTRY_AUTHORITY' and not decision.get('decision_statement'):
            errors.append(f'{decision_id}: REGISTRY_AUTHORITY requires decision_statement')
        if decision.get('authority_mode') == 'SOURCE_AUTHORITY' and not decision.get('source_ref'):
            errors.append(f'{decision_id}: SOURCE_AUTHORITY requires source_ref')
        if decision.get('status') == 'SUPERSEDED' and not decision.get('superseded_by'):
            errors.append(f'{decision_id}: SUPERSEDED requires superseded_by')
        if decision.get('status') == 'ACCEPTED_WITH_CONDITIONS' and not decision.get('conditions'):
            errors.append(f'{decision_id}: ACCEPTED_WITH_CONDITIONS requires conditions')

    duplicates = {x for x in ids if x and ids.count(x) > 1}
    for duplicate in sorted(duplicates):
        errors.append(f'duplicate decision_id: {duplicate}')

    for decision in decisions:
        decision_id = decision.get('decision_id')
        for superseded in decision.get('supersedes', []):
            if superseded == decision_id:
                errors.append(f'{decision_id}: decision cannot supersede itself')
        if decision.get('superseded_by') == decision_id:
            errors.append(f'{decision_id}: decision cannot supersede itself')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--expect-invalid', action='store_true')
    args = parser.parse_args()
    failures = 0

    Draft202012Validator.check_schema(RECORD_SCHEMA)
    Draft202012Validator.check_schema(REGISTRY_SCHEMA)

    for path in args.paths:
        try:
            errors = validate(path)
        except Exception as exc:
            print(f'ERROR {path}: {exc}')
            failures += 1
            continue
        if args.expect_invalid:
            if errors:
                print(f'PASS (invalid as expected) {path}')
                for error in errors:
                    print(f'  - {error}')
            else:
                print(f'FAIL {path}: expected invalid')
                failures += 1
        elif errors:
            print(f'FAIL {path}')
            for error in errors:
                print(f'  - {error}')
            failures += 1
        else:
            print(f'PASS {path}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
