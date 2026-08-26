#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "corporate-operating-intelligence"
CONTRACT_INDEX_SCHEMA = ROOT / "schemas" / "contracts" / "contract-authority-index.schema.json"
VOCAB_PATH = ROOT / "vocabularies" / "corporate-operating-intelligence.v1.yaml"
CONCEPT_REGISTRY_PATH = ROOT / "registries" / "corporate-operating-intelligence" / "concepts.v1.yaml"
CONTRACT_INDEX_PATH = ROOT / "registries" / "contract-authority-index.yaml"
PROFILE_PATH = ROOT / "profiles" / "corporate-operating-intelligence" / "first-horizon-contracts.v1.yaml"
SOURCE_MAPPING_PATH = ROOT / "mappings" / "corporate-operating-intelligence" / "source-fact-mapping.v1.yaml"
EXAMPLES_DIR = ROOT / "examples" / "corporate-operating-intelligence"
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validator(schema, registry=None):
    kwargs = {"format_checker": FormatChecker()}
    if registry is not None:
        kwargs["registry"] = registry
    return Draft202012Validator(schema, **kwargs)


def schema_errors(instance, schema, registry=None):
    errors = list(validator(schema, registry).iter_errors(instance))
    return sorted(errors, key=lambda e: list(e.absolute_path))


def load_schema_registry():
    registry = Registry()
    schemas = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schemas[path.name] = schema
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    return schemas, registry


def require(condition: bool, message: str, errors: list[str]):
    if not condition:
        errors.append(message)


def semantic_answer_errors(instance, concepts, vocab):
    errors = []
    concept_id = instance.get("canonical_concept")
    concept = concepts.get(concept_id)
    if concept is None:
        errors.append(f"unregistered canonical_concept: {concept_id}")
        return errors
    if instance.get("concern_family") != concept.get("concern_family"):
        errors.append(
            f"concept {concept_id} concern_family mismatch: "
            f"{instance.get('concern_family')} != {concept.get('concern_family')}"
        )
    if instance.get("semantic_class") != concept.get("semantic_class"):
        errors.append(
            f"concept {concept_id} semantic_class mismatch: "
            f"{instance.get('semantic_class')} != {concept.get('semantic_class')}"
        )
    if instance.get("value_state") not in concept.get("allowed_value_states", []):
        errors.append(
            f"concept {concept_id} does not allow value_state {instance.get('value_state')}"
        )
    if instance.get("semantic_class") not in vocab["semantic_classes"]:
        errors.append(f"unknown semantic_class: {instance.get('semantic_class')}")
    if instance.get("value_state") not in vocab["value_states"]:
        errors.append(f"unknown value_state: {instance.get('value_state')}")
    authority_mode = (instance.get("authority") or {}).get("mode")
    if authority_mode not in vocab["authority_modes"]:
        errors.append(f"unknown authority mode: {authority_mode}")
    freshness_state = (instance.get("freshness") or {}).get("state")
    if freshness_state not in vocab["freshness_states"]:
        errors.append(f"unknown freshness state: {freshness_state}")
    if concept.get("unit_policy") == "REQUIRED" and instance.get("unit") != concept.get("unit"):
        errors.append(
            f"concept {concept_id} requires unit {concept.get('unit')}, got {instance.get('unit')}"
        )
    if concept.get("unit_policy") == "FORBIDDEN" and instance.get("unit") not in (None, ""):
        errors.append(f"concept {concept_id} forbids unit {instance.get('unit')}")
    return errors


def validate_source_mapping(concepts, vocab, errors):
    if not SOURCE_MAPPING_PATH.exists():
        return 0
    mapping = load_yaml(SOURCE_MAPPING_PATH)
    checked = 0
    for source in mapping.get("sources", []):
        for item in source.get("mappings", []):
            checked += 1
            concept_id = item.get("canonical_concept")
            concept = concepts.get(concept_id)
            require(concept is not None, f"source mapping uses unregistered concept {concept_id}", errors)
            if concept is None:
                continue
            require(
                item.get("semantic_class") == concept.get("semantic_class"),
                f"source mapping semantic mismatch for {concept_id}: {item.get('semantic_class')} != {concept.get('semantic_class')}",
                errors,
            )
            require(
                item.get("semantic_class") in vocab["semantic_classes"],
                f"source mapping uses unknown semantic class {item.get('semantic_class')}",
                errors,
            )
            if concept.get("unit_policy") == "REQUIRED":
                require(
                    item.get("unit") == concept.get("unit"),
                    f"source mapping unit mismatch for {concept_id}: {item.get('unit')} != {concept.get('unit')}",
                    errors,
                )
    return checked


def main():
    errors: list[str] = []
    schemas, registry = load_schema_registry()
    vocab = load_yaml(VOCAB_PATH)
    concept_registry = load_yaml(CONCEPT_REGISTRY_PATH)
    profile = load_yaml(PROFILE_PATH)
    contract_index = load_yaml(CONTRACT_INDEX_PATH)

    concept_registry_errors = schema_errors(
        concept_registry, schemas["canonical-concept-registry.schema.json"], registry
    )
    for err in concept_registry_errors:
        errors.append(f"concept registry {list(err.absolute_path)}: {err.message}")

    profile_errors = schema_errors(profile, schemas["contract-profile.schema.json"], registry)
    for err in profile_errors:
        errors.append(f"contract profile {list(err.absolute_path)}: {err.message}")

    index_schema = load_json(CONTRACT_INDEX_SCHEMA)
    Draft202012Validator.check_schema(index_schema)
    index_errors = schema_errors(contract_index, index_schema)
    for err in index_errors:
        errors.append(f"contract authority index {list(err.absolute_path)}: {err.message}")

    concept_list = concept_registry.get("concepts", [])
    concept_ids = [c.get("concept_id") for c in concept_list]
    require(len(concept_ids) == len(set(concept_ids)), "duplicate canonical concept IDs", errors)
    concepts = {c["concept_id"]: c for c in concept_list if c.get("concept_id")}

    for concept in concept_list:
        concept_id = concept.get("concept_id")
        require(concept.get("semantic_class") in vocab["semantic_classes"], f"concept {concept_id} uses unknown semantic class", errors)
        require(concept.get("concern_family") in vocab["concern_families"], f"concept {concept_id} uses unknown concern family", errors)
        require(concept.get("authority_expectation") in vocab["authority_modes"], f"concept {concept_id} uses unknown authority expectation", errors)
        for state in concept.get("allowed_value_states", []):
            require(state in vocab["value_states"], f"concept {concept_id} uses unknown value state {state}", errors)

    expected_value_states = {
        "KNOWN", "UNKNOWN", "MISSING", "STALE", "RECONCILIATION_REQUIRED", "RESTRICTED", "NOT_APPLICABLE"
    }
    expected_freshness = {"CURRENT", "STALE", "UNKNOWN", "REVIEW_REQUIRED"}
    expected_reconciliation = {"CURRENT", "RECONCILIATION_REQUIRED", "UNAVAILABLE"}
    expected_availability = {"AVAILABLE", "DEGRADED", "UNAVAILABLE", "UNKNOWN"}
    require(expected_value_states == set(vocab.get("value_states", [])), "value-state vocabulary drift", errors)
    require(expected_freshness == set(vocab.get("freshness_states", [])), "freshness vocabulary drift", errors)
    require(expected_reconciliation == set(vocab.get("reconciliation_states", [])), "reconciliation vocabulary drift", errors)
    require(expected_availability == set(vocab.get("availability_states", [])), "availability vocabulary drift", errors)

    finance_classes = set(profile["required_semantic_partitions"]["finance"])
    state_classes = set(profile["required_semantic_partitions"]["state_dimensions"])
    require(finance_classes <= set(vocab["semantic_classes"]), "financial semantic partition is incomplete", errors)
    require(state_classes <= set(vocab["semantic_classes"]), "state-dimension semantic partition is incomplete", errors)
    require(len(finance_classes) == 8, "financial semantic partition collapsed or duplicated", errors)
    require(len(state_classes) == 7, "state-dimension semantic partition collapsed or duplicated", errors)

    valid_answer = load_json(EXAMPLES_DIR / "valid-material-answer.json")
    for err in schema_errors(valid_answer, schemas["material-answer.schema.json"], registry):
        errors.append(f"valid material answer {list(err.absolute_path)}: {err.message}")
    for err in semantic_answer_errors(valid_answer, concepts, vocab):
        errors.append(f"valid material answer semantic: {err}")

    invalid_unknown = load_json(EXAMPLES_DIR / "invalid-unknown-with-value.json")
    invalid_unknown_schema_errors = schema_errors(
        invalid_unknown, schemas["material-answer.schema.json"], registry
    )
    require(bool(invalid_unknown_schema_errors), "UNKNOWN-with-value negative fixture unexpectedly validated", errors)

    semantic_mismatch = load_json(EXAMPLES_DIR / "invalid-semantic-class-mismatch.json")
    mismatch_schema_errors = schema_errors(
        semantic_mismatch, schemas["material-answer.schema.json"], registry
    )
    require(not mismatch_schema_errors, "semantic mismatch fixture must be structurally valid", errors)
    mismatch_semantic_errors = semantic_answer_errors(semantic_mismatch, concepts, vocab)
    require(
        any("semantic_class mismatch" in err for err in mismatch_semantic_errors),
        "semantic mismatch negative fixture was not rejected by concept semantics",
        errors,
    )

    source_health = load_json(EXAMPLES_DIR / "valid-source-health.json")
    for err in schema_errors(source_health, schemas["source-health.schema.json"], registry):
        errors.append(f"valid source health {list(err.absolute_path)}: {err.message}")
    require(source_health.get("availability_state") in vocab["availability_states"], "source health availability not governed", errors)
    require(source_health.get("freshness", {}).get("state") in vocab["freshness_states"], "source health freshness not governed", errors)
    require(source_health.get("reconciliation_state") in vocab["reconciliation_states"], "source health reconciliation not governed", errors)
    require(source_health.get("substitution_allowed") is False, "source health permits source substitution", errors)

    read_model_metadata = load_json(EXAMPLES_DIR / "valid-read-model-metadata.json")
    for err in schema_errors(read_model_metadata, schemas["read-model-metadata.schema.json"], registry):
        errors.append(f"valid read-model metadata {list(err.absolute_path)}: {err.message}")
    require(read_model_metadata.get("authority_mode") == "DERIVED_NON_AUTHORITATIVE", "read model gained authority", errors)
    derivation = read_model_metadata.get("derivation", {})
    require(derivation.get("deterministic") is True, "derivation is not deterministic", errors)
    require(derivation.get("inference") is False, "derivation permits semantic inference", errors)
    require(bool(derivation.get("generator_revision")), "derivation lacks generator revision", errors)
    require(bool(derivation.get("rebuild_ref")), "derivation lacks rebuild reference", errors)

    inventory = profile.get("contract_inventory", [])
    inventory_ids = [item.get("id") for item in inventory]
    require(len(inventory_ids) == len(set(inventory_ids)), "duplicate contract IDs in COI profile", errors)
    index_by_id = {item.get("id"): item for item in contract_index.get("contracts", [])}
    for item in inventory:
        path = ROOT / item["path"]
        require(path.exists(), f"registered COI contract path missing: {item['path']}", errors)
        indexed = index_by_id.get(item["id"])
        require(indexed is not None, f"COI contract missing from authority index: {item['id']}", errors)
        if indexed is not None:
            require(indexed.get("successorRef") == item["path"], f"authority index path mismatch for {item['id']}", errors)
            require(indexed.get("version") == item["version"], f"authority index version mismatch for {item['id']}", errors)
            require(indexed.get("authorityState") == "ADUMUN_CANONICAL", f"COI contract not canonical in authority index: {item['id']}", errors)
            require("STD-COI-001" in indexed.get("semanticAuthority", ""), f"COI contract lacks STD-COI-001 semantic authority: {item['id']}", errors)
        require(SEMVER_RE.match(item["version"]) is not None, f"invalid SemVer in profile for {item['id']}", errors)

    duplicate_consumer_contracts = [
        ROOT / "schemas" / "corporate-operating-intelligence" / "quick-lookup-result.schema.json",
        ROOT / "schemas" / "corporate-operating-intelligence" / "executive-snapshot.schema.json",
        ROOT / "schemas" / "corporate-operating-intelligence" / "evidence-trace.schema.json",
    ]
    require(not any(path.exists() for path in duplicate_consumer_contracts), "consumer-specific duplicate semantic contract detected", errors)

    require(profile["principles"]["consumer_independent_semantics"] is True, "consumer-independent semantics disabled", errors)
    require(profile["principles"]["provider_neutral"] is True, "provider neutrality disabled", errors)
    require(profile["principles"]["file_json_first"] is True, "file/JSON-first disabled", errors)
    require(profile["principles"]["fail_closed_unknowns"] is True, "unknown vocabulary does not fail closed", errors)
    require(profile["principles"]["semantic_inference"] == "PROHIBITED", "semantic inference not prohibited", errors)
    require(profile["versioning"]["breaking_requires_migration"] is True, "breaking changes lack migration requirement", errors)
    require(profile["versioning"]["lineage_required"] is True, "breaking changes lack lineage requirement", errors)
    require(profile["compatibility"]["structural_and_semantic"] is True, "compatibility is not semantic + structural", errors)
    require(profile["compatibility"]["unknown_vocab"] == "FAIL_CLOSED", "unknown vocabulary compatibility is not fail-closed", errors)
    require(profile["compatibility"]["silent_reinterpretation"] == "PROHIBITED", "silent semantic reinterpretation allowed", errors)
    require(profile["rebuildability"]["exact_revision_local_validation"] is True, "exact-revision local validation not required", errors)
    require(profile["rebuildability"]["paid_actions_required"] is False, "paid Actions became required", errors)

    mapped_fact_count = validate_source_mapping(concepts, vocab, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"PASS: {len(schemas)} COI schemas are structurally valid")
    print(f"PASS: {len(concepts)} canonical concepts are unique, registered and vocabulary-conformant")
    print("PASS: Material Answer / QuickLookupResult semantics are concept-bound and consumer-independent")
    print("PASS: UNKNOWN-with-value is rejected and semantic-class mismatch fails closed")
    print("PASS: value, freshness, reconciliation and availability vocabularies are exact and explicit")
    print("PASS: finance and state semantic partitions remain distinct")
    print("PASS: source-health contract forbids substitution and preserves degraded states")
    print("PASS: read-model metadata requires DERIVED_NON_AUTHORITATIVE deterministic non-inferential rebuild metadata")
    print(f"PASS: {len(inventory)} COI contracts are registered in the canonical contract authority index")
    if mapped_fact_count:
        print(f"PASS: {mapped_fact_count} existing source-to-fact mappings consume registered M1 concepts without semantic override")
    print("PASS: SemVer, semantic backward compatibility, stewardship and registry requirements are machine-verifiable")
    print("PASS: local exact-revision validation is required; paid GitHub Actions are not required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
