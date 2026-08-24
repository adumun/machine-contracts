#!/usr/bin/env python3
"""Local deterministic validator for ADÜMÜN machine contracts."""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    "work-item": ROOT / "schemas" / "work-management" / "work-item.schema.json",
    "workflow-contract": ROOT / "schemas" / "workflow" / "workflow-contract.schema.json",
    "provider-mapping": ROOT / "schemas" / "provider-mapping" / "provider-mapping.schema.json",
    "provider-config": ROOT / "schemas" / "provider-config" / "provider-config.schema.json",
}
NON_LIFECYCLE_STATES = {"RECONCILIATION_REQUIRED", "INCUBATE", "INCUBATION"}
READY_OR_LATER = {"READY", "IN_PROGRESS", "BLOCKED", "IN_REVIEW", "DONE"}
WORK_TYPES = {"STORY", "BUG", "TASK", "SPIKE", "EXPERIMENT", "TECHNICAL_DEBT", "INCIDENT"}
WORK_STATES = {"PROPOSED", "REFINING", "READY", "IN_PROGRESS", "BLOCKED", "IN_REVIEW", "DONE", "CANCELED", "DEFERRED"}
WORK_FIELDS = {"work_id", "title", "type", "category", "areas", "source", "priority", "severity", "state", "owner", "acceptance_criteria", "evidence_refs", "provider_refs", "reclassification"}


def load_document(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) if path.suffix.lower() in {".yaml", ".yml"} else json.load(fh)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def infer_schema(document: dict) -> str:
    version = document.get("schema_version", "")
    for prefix, name in (("work-item.", "work-item"), ("workflow-contract.", "workflow-contract"), ("provider-mapping.", "provider-mapping"), ("provider-config.", "provider-config")):
        if version.startswith(prefix): return name
    raise ValueError(f"Cannot infer schema from schema_version={version!r}")


def semantic_work_item(document: dict) -> list[str]:
    errors=[]; state=document.get("state")
    if state in READY_OR_LATER:
        if not document.get("owner"): errors.append("owner: required when work is READY or later")
        if not document.get("acceptance_criteria"): errors.append("acceptance_criteria: required when work is READY or later")
    if state == "DONE" and not document.get("evidence_refs"): errors.append("evidence_refs: DONE requires retained completion evidence")
    r=document.get("reclassification")
    if r:
        if r.get("from_type") == r.get("to_type"): errors.append("reclassification: from_type and to_type must differ")
        if r.get("to_type") != document.get("type"): errors.append("reclassification.to_type: must equal current canonical type")
    return errors


def semantic_workflow(document: dict) -> list[str]:
    errors=[]; stages=document.get("stages",[]); ids=[s.get("stage_id") for s in stages]
    if len(ids)!=len(set(ids)): errors.append("stages: duplicate stage_id values are forbidden")
    known=set(ids); artifact_ids=set(); transition_ids=set()
    for stage in stages:
        if stage.get("canonical_state") in NON_LIFECYCLE_STATES: errors.append(f"stage {stage.get('stage_id')}: non-lifecycle state used as lifecycle state")
        for collection,direction in (("inputs","INPUT"),("outputs","OUTPUT")):
            for a in stage.get(collection,[]):
                aid=a.get("artifact_id")
                if aid in artifact_ids: errors.append(f"artifact_id {aid}: duplicate stable ID")
                artifact_ids.add(aid)
                if a.get("direction") != direction: errors.append(f"artifact {aid}: {collection} must use direction {direction}")
                if a.get("requirement") == "CONDITIONAL" and not a.get("condition"): errors.append(f"artifact {aid}: CONDITIONAL requires condition")
    for t in document.get("transitions",[]):
        tid=t.get("transition_id")
        if tid in transition_ids: errors.append(f"transition_id {tid}: duplicate stable ID")
        transition_ids.add(tid)
        if t.get("source") not in known: errors.append(f"transition {tid}: unknown source stage {t.get('source')}")
        if t.get("target") not in known: errors.append(f"transition {tid}: unknown target stage {t.get('target')}")
        if t.get("source") == t.get("target"): errors.append(f"transition {tid}: source and target must differ")
    return errors


def _duplicates(mappings, field):
    vals=[m.get(field) for m in mappings]
    return sorted({v for v in vals if v is not None and vals.count(v)>1})


def semantic_provider_mapping(document: dict) -> list[str]:
    errors=[]; types=document.get("work_type_mappings",[]); states=document.get("state_mappings",[]); fields=document.get("field_mappings",[])
    for label,maps in (("work_type_mappings",types),("state_mappings",states)):
        for field in ("canonical","provider"):
            for value in _duplicates(maps,field): errors.append(f"{label}: duplicate {field} mapping {value}")
    for value in _duplicates(fields,"canonical_field"): errors.append(f"field_mappings: duplicate canonical_field mapping {value}")
    for m in types:
        if m.get("canonical") not in WORK_TYPES: errors.append(f"work_type_mappings: unknown canonical type {m.get('canonical')}")
        if m.get("lossy") and not m.get("notes"): errors.append(f"work_type_mappings: lossy mapping {m.get('canonical')} requires notes")
    for m in states:
        if m.get("canonical") not in WORK_STATES: errors.append(f"state_mappings: unknown canonical state {m.get('canonical')}")
        if m.get("lossy") and not m.get("notes"): errors.append(f"state_mappings: lossy mapping {m.get('canonical')} requires notes")
    for m in fields:
        if m.get("canonical_field") not in WORK_FIELDS: errors.append(f"field_mappings: unknown canonical field {m.get('canonical_field')}")
    for t in document.get("transition_mappings",[]):
        s,tgt=t.get("canonical_from"),t.get("canonical_to")
        if s not in WORK_STATES or tgt not in WORK_STATES: errors.append(f"transition_mappings: unknown canonical transition {s}->{tgt}")
        if s == tgt: errors.append(f"transition_mappings: source and target must differ for {s}->{tgt}")
        if t.get("guards_preserved") is not True: errors.append(f"transition_mappings: {s}->{tgt} must preserve canonical guards or remain unmapped")
    return errors


def semantic_provider_config(document: dict) -> list[str]:
    errors=[]; state=document.get("binding_state"); target=document.get("target",{})
    if state == "BOUND":
        if not target.get("external_id"): errors.append("target.external_id: required when binding_state is BOUND")
        if not target.get("url"): errors.append("target.url: required when binding_state is BOUND")
    if document.get("hosted_validation_required") is False and document.get("local_validation_required") is not True:
        errors.append("local_validation_required: must be true when hosted validation is not required")
    if not document.get("mapping_ref"): errors.append("mapping_ref: provider configuration must reference a canonical provider mapping")
    return errors


def validate(path: Path, schema_name: str | None = None) -> list[str]:
    doc=load_document(path)
    if not isinstance(doc,dict): raise ValueError("top-level document must be an object/map")
    name=schema_name or infer_schema(doc); schema_path=SCHEMAS.get(name)
    if not schema_path: raise ValueError(f"Unknown schema {name!r}")
    validator=Draft202012Validator(load_json(schema_path))
    errors=[f"{'.'.join(str(x) for x in e.absolute_path) or '$'}: {e.message}" for e in sorted(validator.iter_errors(doc), key=lambda e:list(e.path))]
    if name=="work-item": errors.extend(semantic_work_item(doc))
    elif name=="workflow-contract": errors.extend(semantic_workflow(doc))
    elif name=="provider-mapping": errors.extend(semantic_provider_mapping(doc))
    elif name=="provider-config": errors.extend(semantic_provider_config(doc))
    return errors


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("paths",nargs="+",type=Path); p.add_argument("--schema",choices=sorted(SCHEMAS)); p.add_argument("--expect-invalid",action="store_true"); a=p.parse_args(); failures=0
    for path in a.paths:
        try: errors=validate(path,a.schema)
        except Exception as exc: print(f"ERROR {path}: {exc}"); failures+=1; continue
        if a.expect_invalid:
            if errors:
                print(f"PASS (invalid as expected) {path}"); [print(f"  - {e}") for e in errors]
            else: print(f"FAIL {path}: expected invalid, but validation passed"); failures+=1
        elif errors:
            print(f"FAIL {path}"); [print(f"  - {e}") for e in errors]; failures+=1
        else: print(f"PASS {path}")
    return 1 if failures else 0


if __name__ == "__main__": sys.exit(main())
