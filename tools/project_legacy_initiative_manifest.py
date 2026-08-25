#!/usr/bin/env python3
"""Project legacy ILS 0.2-alpha initiative manifests into ADÜMÜN initiative-manifest.v1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import yaml

REGISTRY_TYPES = {
    "sources": "SOURCES",
    "gates": "GATES",
    "artifacts": "ARTIFACTS",
    "evidence": "EVIDENCE",
    "hypotheses": "HYPOTHESES",
    "risks": "RISKS",
    "decisions": "DECISIONS",
}


def load(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def normalize_registry_type(key: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", key.upper()).strip("_")


def project(source: dict) -> dict:
    if source.get("schema_version") != "0.2-alpha":
        raise ValueError("only legacy schema_version 0.2-alpha is supported")

    initiative = dict(source.get("initiative") or {})
    initiative.pop("adoption_mode", None)
    initiative.pop("domain_classification", None)
    initiative.pop("operating_intent", None)

    profile_src = source.get("profile") or {}
    profile = {
        "primary": profile_src.get("primary"),
        "rigor": profile_src.get("rigor"),
    }
    if profile_src.get("modifiers"):
        profile["modifiers"] = profile_src["modifiers"]
    if profile_src.get("tailoring"):
        profile["tailoring_ref"] = "legacy-inline-tailoring"

    adoption = source.get("adoption")
    if not adoption and source.get("initiative", {}).get("adoption_mode"):
        adoption = {"mode": source["initiative"]["adoption_mode"]}

    lifecycle_src = source.get("lifecycle") or {}
    lifecycle = {
        "state": lifecycle_src.get("state"),
        "canonical_state": None,
    }
    for field in (
        "current_stage", "current_stage_name", "current_gate",
        "last_accepted_gate", "last_gate_decision_record", "gate_history_complete"
    ):
        if field in lifecycle_src:
            lifecycle[field] = lifecycle_src[field]
    if adoption and adoption.get("mode") == "RETROSPECTIVE_ADOPTION":
        lifecycle["reconciliation_status"] = "RECONCILIATION_REQUIRED"
    else:
        lifecycle["reconciliation_status"] = "CURRENT"

    registries = []
    for key, ref in (source.get("registries") or {}).items():
        registries.append({
            "registry_type": REGISTRY_TYPES.get(key, normalize_registry_type(key)),
            "ref": ref,
            "authority_scope": "INITIATIVE_LOCAL",
            "required": key in REGISTRY_TYPES,
        })

    projection_src = source.get("projection_policy") or {}
    projection = {
        "canonical_format": projection_src.get("canonical_format", "YAML"),
        "generated_files_are_authoritative": bool(projection_src.get("generated_files_are_authoritative", False)),
    }
    for field in ("generated_json", "portfolio_projection", "dashboard_consumer"):
        if field in projection_src:
            projection[field] = projection_src[field]

    extensions = {}
    reserved = {"schema_version", "standard_version", "initiative", "profile", "adoption", "lifecycle", "registries", "projection_policy", "updated_at"}
    for key, value in source.items():
        if key not in reserved:
            extensions[f"legacy.{key}"] = value
    for key in ("adoption_mode", "domain_classification", "operating_intent"):
        if key in (source.get("initiative") or {}):
            extensions[f"legacy.initiative.{key}"] = source["initiative"][key]
    if profile_src.get("local_domain_profile"):
        extensions["legacy.profile.local_domain_profile"] = profile_src["local_domain_profile"]
    if profile_src.get("tailoring"):
        extensions["legacy.profile.tailoring"] = profile_src["tailoring"]

    result = {
        "schema_version": "initiative-manifest.v1",
        "contract_version": "1.0.0",
        "initiative": initiative,
        "profile": profile,
        "lifecycle": lifecycle,
        "registries": registries,
        "projection_policy": projection,
        "updated_at": source.get("updated_at") or "1970-01-01T00:00:00Z",
    }
    if adoption:
        result["adoption"] = adoption
    if extensions:
        result["extensions"] = extensions
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    projected = project(load(args.source))
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(json.dumps(projected, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PASS projected {args.source} -> {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
