#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
RECORD_SCHEMA=json.loads((ROOT/'schemas/decision-governance/decision-record.schema.json').read_text(encoding='utf-8'))
REGISTRY_SCHEMA=json.loads((ROOT/'schemas/decision-governance/decision-registry.schema.json').read_text(encoding='utf-8'))


def validate(path: Path) -> list[str]:
    doc=json.loads(path.read_text(encoding='utf-8'))
    errors=[]
    if doc.get('schema_version')!='decision-registry.v1': errors.append('schema_version must be decision-registry.v1')
    if not doc.get('registry_id'): errors.append('registry_id is required')
    if doc.get('status') not in {'CURRENT','DRAFT','HISTORICAL'}: errors.append('invalid registry status')
    decisions=doc.get('decisions')
    if not isinstance(decisions,list): return errors+['decisions must be an array']
    ids=[]
    validator=Draft202012Validator(RECORD_SCHEMA)
    for idx,d in enumerate(decisions):
        for e in validator.iter_errors(d): errors.append(f'decisions[{idx}].{'.'.join(str(x) for x in e.path)}: {e.message}')
        did=d.get('decision_id'); ids.append(did)
        if d.get('authority_mode')=='REGISTRY_AUTHORITY' and not d.get('decision_statement'): errors.append(f'{did}: REGISTRY_AUTHORITY requires decision_statement')
        if d.get('authority_mode')=='SOURCE_AUTHORITY' and not d.get('source_ref'): errors.append(f'{did}: SOURCE_AUTHORITY requires source_ref')
        if d.get('status')=='SUPERSEDED' and not d.get('superseded_by'): errors.append(f'{did}: SUPERSEDED requires superseded_by')
        if d.get('status')=='ACCEPTED_WITH_CONDITIONS' and not d.get('conditions'): errors.append(f'{did}: ACCEPTED_WITH_CONDITIONS requires conditions')
    duplicates={x for x in ids if x and ids.count(x)>1}
    for x in sorted(duplicates): errors.append(f'duplicate decision_id: {x}')
    known=set(x for x in ids if x)
    for d in decisions:
        for x in d.get('supersedes',[]):
            if x==d.get('decision_id'): errors.append(f"{x}: decision cannot supersede itself")
        if d.get('superseded_by')==d.get('decision_id'): errors.append(f"{d.get('decision_id')}: decision cannot supersede itself")
    return errors


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument('paths',nargs='+',type=Path); p.add_argument('--expect-invalid',action='store_true'); a=p.parse_args(); failed=0
    Draft202012Validator.check_schema(RECORD_SCHEMA); Draft202012Validator.check_schema(REGISTRY_SCHEMA)
    for path in a.paths:
        try: errors=validate(path)
        except Exception as exc: print(f'ERROR {path}: {exc}'); failed+=1; continue
        if a.expect_invalid:
            if errors: print(f'PASS (invalid as expected) {path}'); [print(f'  - {e}') for e in errors]
            else: print(f'FAIL {path}: expected invalid'); failed+=1
        elif errors:
            print(f'FAIL {path}'); [print(f'  - {e}') for e in errors]; failed+=1
        else: print(f'PASS {path}')
    return 1 if failed else 0

if __name__=='__main__': sys.exit(main())
