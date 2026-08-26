#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "mappings/corporate-operating-intelligence/source-fact-mapping.v1.yaml"
SCHEMA = ROOT / "schemas/corporate-operating-intelligence/source-fact-mapping.schema.json"
VOCAB = ROOT / "vocabularies/corporate-operating-intelligence.v1.yaml"

EXPECTED = {
    "FH-CF-01": "RM-FUND-001",
    "FH-CF-02": "REG-INIT-LIFECYCLE-001",
    "FH-CF-03": "REG-DEC-001",
    "FH-CF-04": "REG-STR-REC-001",
    "FH-CF-05": "REG-RM-001",
}


def fail(msg):
    print(f"FAIL: {msg}")
    return 1


def main():
    mapping = yaml.safe_load(MAPPING.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    vocab = yaml.safe_load(VOCAB.read_text(encoding="utf-8"))

    errors = sorted(Draft202012Validator(schema).iter_errors(mapping), key=lambda e: list(e.path))
    if errors:
        for e in errors:
            print(f"FAIL schema {list(e.path)}: {e.message}")
        return 1
    print("PASS: source-fact mapping validates against schema")

    sources = mapping["sources"]
    by_family = {s["concern_family"]: s for s in sources}
    if set(by_family) != set(EXPECTED):
        return fail(f"concern-family coverage mismatch: {sorted(by_family)}")
    for family, source_id in EXPECTED.items():
        if by_family[family]["source_id"] != source_id:
            return fail(f"{family} expected {source_id}, got {by_family[family]['source_id']}")
    print("PASS: exact first-horizon source selected for all FH-CF-01..05")

    semantic_classes = set(vocab["semantic_classes"])
    concepts = set()
    for source in sources:
        if source["authority_mode"] == "DERIVED_NON_AUTHORITATIVE" and source["source_id"] != "RM-FUND-001":
            return fail(f"unexpected derived source baseline: {source['source_id']}")
        for item in source["mappings"]:
            concept = item["canonical_concept"]
            scoped = (source["source_id"], concept)
            if scoped in concepts:
                return fail(f"duplicate mapping {scoped}")
            concepts.add(scoped)
            if item["semantic_class"] not in semantic_classes:
                return fail(f"unknown semantic class {item['semantic_class']} for {concept}")
            if "-" in item["missing_tokens"] and item["missing_value_state"] not in {"UNKNOWN", "MISSING"}:
                return fail(f"dash token must remain unknown/missing for {concept}")
    print("PASS: all mapped facts use controlled semantic classes and explicit missing-token rules")

    policy = mapping["mapping_policy"]
    if not policy["read_only"] or policy["semantic_inference"] != "prohibited" or policy["authority_escalation"] != "prohibited":
        return fail("mapping policy violates M2 read-only/no-inference/no-authority-escalation guardrail")
    print("PASS: M2 read-only / no-inference / no-authority-escalation policy enforced")

    required_new = {"LIFECYCLE_STAGE", "PREDICTABLE_COVERAGE"}
    if not required_new.issubset(semantic_classes):
        return fail("M2 semantic distinctions missing from controlled vocabulary")
    print("PASS: lifecycle stage and predictable coverage remain distinct semantic classes")

    print(f"PASS: {len(sources)} sources, {sum(len(s['mappings']) for s in sources)} canonical fact mappings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
