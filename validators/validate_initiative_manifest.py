#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "initiative-governance" / "initiative-manifest.schema.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def semantic(doc: dict) -> list[str]:
    errors=[]
    regs=doc.get("registries",[])
    types=[r.get("registry_type") for r in regs]
    if len(types)!=len(set(types)):
        errors.append("registries: registry_type values must be unique")
    if doc.get("projection_policy",{}).get("generated_files_are_authoritative") is not False:
        errors.append("projection_policy.generated_files_are_authoritative must be false without a separate authority exception")
    adoption=doc.get("adoption",{})
    lifecycle=doc.get("lifecycle",{})
    if adoption.get("mode") == "RETROSPECTIVE_ADOPTION" and lifecycle.get("gate_history_complete") is False:
        if lifecycle.get("last_accepted_gate") and not lifecycle.get("last_gate_decision_record"):
            errors.append("retrospective incomplete gate history cannot claim last_accepted_gate without last_gate_decision_record")
    if lifecycle.get("reconciliation_status") == "RECONCILIATION_REQUIRED" and lifecycle.get("canonical_state") is not None:
        errors.append("canonical_state must remain null while lifecycle reconciliation is required")
    return errors


def validate(path: Path) -> list[str]:
    doc=load(path)
    schema=load(SCHEMA)
    errors=[f"{'.'.join(str(x) for x in e.absolute_path) or '$'}: {e.message}" for e in Draft202012Validator(schema).iter_errors(doc)]
    errors.extend(semantic(doc))
    return errors


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("paths",nargs="+",type=Path); p.add_argument("--expect-invalid",action="store_true"); a=p.parse_args(); failed=0
    for path in a.paths:
        errors=validate(path)
        if a.expect_invalid:
            if errors: print(f"PASS (invalid as expected) {path}")
            else: print(f"FAIL {path}: expected invalid"); failed+=1
        elif errors:
            print(f"FAIL {path}"); [print(f"  - {e}") for e in errors]; failed+=1
        else: print(f"PASS {path}")
    return 1 if failed else 0

if __name__ == "__main__": sys.exit(main())
