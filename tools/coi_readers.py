#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = ROOT / "mappings" / "corporate-operating-intelligence" / "source-fact-mapping.v1.yaml"

OBJECT_TYPES = {
    "FH-CF-01": "FUNDING_POSITION",
    "FH-CF-02": "INITIATIVE",
    "FH-CF-03": "DECISION",
    "FH-CF-04": "ORGANIZATIONAL_UNIT",
    "FH-CF-05": "READ_MODEL_HEALTH",
}


def _sanitize(value: Any) -> str:
    normalized = re.sub(r"[^A-Z0-9._-]+", "-", str(value).upper()).strip("-")
    return normalized or "UNKNOWN"


def _column_index(letter: str) -> int:
    value = letter.strip().upper()
    if not re.fullmatch(r"[A-Z]+", value):
        raise ValueError(f"invalid column reference: {letter!r}")
    index = 0
    for char in value:
        index = index * 26 + (ord(char) - 64)
    return index - 1


def _parse_integer_formatted_number(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean cannot be parsed as integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"non-integer numeric value: {value!r}")
        return int(value)
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not re.fullmatch(r"[-+]?\d{1,3}(?:,\d{3})*|[-+]?\d+", text):
        raise ValueError(f"invalid integer representation: {value!r}")
    return int(text.replace(",", ""))


def _rows_to_dicts(rows: list[list[Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    if not rows:
        return [], []
    headers = [str(value).strip() for value in rows[0]]
    result: list[dict[str, Any]] = []
    for source_row in rows[1:]:
        padded = list(source_row) + [""] * max(0, len(headers) - len(source_row))
        result.append(dict(zip(headers, padded[: len(headers)])))
    return headers, result


def _matches_filter(row: dict[str, Any], row_filter: dict[str, Any] | None) -> bool:
    if not row_filter:
        return True
    value = str(row.get(row_filter["column"], ""))
    if "equals" in row_filter:
        return value == row_filter["equals"]
    if "in" in row_filter:
        return value in row_filter["in"]
    return False


def _source_envelope(spec: dict[str, Any], snapshot: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    freshness = copy.deepcopy(snapshot.get("freshness") or {"state": "UNKNOWN"})
    freshness.setdefault("as_of", None)
    freshness.setdefault("policy_ref", spec["freshness_registry_ref"])
    confidentiality = copy.deepcopy(snapshot.get("confidentiality") or {"classification": "INTERNAL"})
    return {
        "schema_version": "coi-source-envelope.v1",
        "contract_version": "1.0.0",
        "source_id": f"COI-SRC-{_sanitize(spec['source_id'])}",
        "concern_family": spec["concern_family"],
        "authority_mode": spec["authority_mode"],
        "authority_owner": spec["authority_owner"],
        "source_ref": snapshot.get("source_ref") or f"{spec['source_title']} / {spec['sheet']}",
        "read_only": True,
        "retrieved_at": retrieved_at,
        "freshness": freshness,
        "confidentiality": confidentiality,
        "reconciliation_state": snapshot.get("reconciliation_state", "CURRENT"),
        "error": snapshot.get("error"),
    }


def _material_answer(
    spec: dict[str, Any],
    mapping: dict[str, Any],
    raw_value: Any,
    object_id: str,
    retrieved_at: str,
    source_envelope: dict[str, Any],
    interpretation: Any | None = None,
) -> dict[str, Any]:
    missing = raw_value is None or str(raw_value).strip() in mapping["missing_tokens"]
    answer: dict[str, Any] = {
        "schema_version": "coi-material-answer.v1",
        "contract_version": "1.0.0",
        "answer_id": f"COI-ANS-{_sanitize(spec['source_id'])}.{_sanitize(object_id)}.{mapping['canonical_concept']}",
        "concern_family": spec["concern_family"],
        "canonical_concept": mapping["canonical_concept"],
        "display_label": mapping["display_label"],
        "value_state": mapping["missing_value_state"] if missing else "KNOWN",
        "semantic_class": mapping["semantic_class"],
        "authority": {
            "mode": spec["authority_mode"],
            "owner": spec["authority_owner"],
            "source_ref": source_envelope["source_ref"],
        },
        "provenance": {
            "source_refs": [source_envelope["source_ref"]],
            "derivation": mapping["transform"],
            "evidence_refs": [],
        },
        "freshness": copy.deepcopy(source_envelope["freshness"]),
        "confidentiality": {
            "classification": source_envelope["confidentiality"]["classification"],
            "authorization_state": "ALLOWED",
        },
        "limitations": [mapping["missing_limitation"]] if missing else [],
        "related_refs": [],
        "drill_through_ref": source_envelope["source_ref"],
        "generated_at": retrieved_at,
    }
    if mapping.get("unit"):
        answer["unit"] = mapping["unit"]
    if interpretation not in (None, ""):
        answer["business_meaning"] = str(interpretation)
    if not missing:
        if mapping["transform"] == "COPY_STRING":
            answer["value"] = str(raw_value)
        elif mapping["transform"] == "PARSE_INTEGER_FORMATTED_NUMBER":
            answer["value"] = _parse_integer_formatted_number(raw_value)
        else:
            raise ValueError(f"unsupported transform: {mapping['transform']}")
    return answer


def _concern_record(
    spec: dict[str, Any],
    object_id: str,
    label: str | None,
    facts: list[dict[str, Any]],
    source_envelope: dict[str, Any],
    reconciliation_state: str,
) -> dict[str, Any]:
    return {
        "schema_version": "coi-concern-record.v1",
        "contract_version": "1.0.0",
        "record_id": f"COI-REC-{_sanitize(spec['source_id'])}.{_sanitize(object_id)}",
        "concern_family": spec["concern_family"],
        "object_type": OBJECT_TYPES[spec["concern_family"]],
        "object_id": object_id,
        "label": label,
        "reconciliation_state": reconciliation_state,
        "facts": facts,
        "source_envelopes": [source_envelope],
        "related_refs": [spec["freshness_registry_ref"]],
    }


def read_source(spec: dict[str, Any], snapshot: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    envelope = _source_envelope(spec, snapshot, retrieved_at)
    if snapshot.get("error") or "rows" not in snapshot:
        envelope["reconciliation_state"] = "UNAVAILABLE"
        error = snapshot.get("error") or "SOURCE_ROWS_MISSING"
        envelope["error"] = error
        return {"source_id": spec["source_id"], "status": "UNAVAILABLE", "source_envelope": envelope, "records": [], "errors": [error]}

    rows = snapshot["rows"]
    records: list[dict[str, Any]] = []
    errors: list[str] = []

    if spec["selector_mode"] == "LABEL_VALUE":
        facts: list[dict[str, Any]] = []
        for fact_mapping in spec["mappings"]:
            match_index = _column_index(fact_mapping["match_column"])
            matches = [row for row in rows if len(row) > match_index and str(row[match_index]) == fact_mapping["match_value"]]
            if len(matches) != 1:
                errors.append(f"{fact_mapping['canonical_concept']}: expected exactly one matching row, found {len(matches)}")
                continue
            row = matches[0]
            value_index = _column_index(fact_mapping["value_column"])
            raw_value = row[value_index] if len(row) > value_index else ""
            interpretation = None
            if fact_mapping.get("interpretation_column"):
                interpretation_index = _column_index(fact_mapping["interpretation_column"])
                interpretation = row[interpretation_index] if len(row) > interpretation_index else None
            try:
                facts.append(_material_answer(spec, fact_mapping, raw_value, spec["row_identity"], retrieved_at, envelope, interpretation))
            except Exception as exc:  # fail the affected fact, never infer
                errors.append(f"{fact_mapping['canonical_concept']}: {exc}")
        records.append(
            _concern_record(
                spec,
                spec["row_identity"],
                spec["source_title"],
                facts,
                envelope,
                "CURRENT" if not errors else "RECONCILIATION_REQUIRED",
            )
        )
    elif spec["selector_mode"] == "TABLE_COLUMNS":
        headers, source_rows = _rows_to_dicts(rows)
        required_columns = {spec["row_identity_column"], spec["label_column"]}
        required_columns.update(item["value_column"] for item in spec["mappings"])
        if spec.get("row_filter"):
            required_columns.add(spec["row_filter"]["column"])
        missing_columns = sorted(required_columns - set(headers))
        if missing_columns:
            errors.append("missing source columns: " + ", ".join(missing_columns))
        else:
            for row in source_rows:
                if not _matches_filter(row, spec.get("row_filter")):
                    continue
                object_id = str(row.get(spec["row_identity_column"], "")).strip()
                if not object_id:
                    errors.append("source row missing required identity")
                    continue
                facts: list[dict[str, Any]] = []
                row_errors = 0
                for fact_mapping in spec["mappings"]:
                    try:
                        facts.append(_material_answer(spec, fact_mapping, row.get(fact_mapping["value_column"], ""), object_id, retrieved_at, envelope))
                    except Exception as exc:
                        row_errors += 1
                        errors.append(f"{object_id}/{fact_mapping['canonical_concept']}: {exc}")
                records.append(
                    _concern_record(
                        spec,
                        object_id,
                        str(row.get(spec["label_column"]) or "") or None,
                        facts,
                        envelope,
                        "CURRENT" if row_errors == 0 else "RECONCILIATION_REQUIRED",
                    )
                )
    else:
        errors.append(f"unsupported selector_mode: {spec['selector_mode']}")

    return {
        "source_id": spec["source_id"],
        "status": "OK" if not errors else "PARTIAL",
        "source_envelope": envelope,
        "records": records,
        "errors": errors,
    }


def read_bundle(mapping: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    retrieved_at = bundle["retrieved_at"]
    source_snapshots = bundle.get("sources", {})
    results = []
    for spec in mapping["sources"]:
        snapshot = source_snapshots.get(spec["source_id"], {"error": "SOURCE_SNAPSHOT_MISSING"})
        results.append(read_source(spec, snapshot, retrieved_at))
    return {
        "schema_version": "coi-reader-output.v1",
        "contract_version": "1.0.0",
        "initiative_id": mapping["initiative_id"],
        "milestone": mapping["milestone"],
        "generated_at": retrieved_at,
        "sources": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministically project governed source snapshots into COI concern records.")
    parser.add_argument("input", type=Path, help="JSON source snapshot bundle; acquisition is intentionally outside this reader.")
    parser.add_argument("-m", "--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args()

    mapping = yaml.safe_load(args.mapping.read_text(encoding="utf-8"))
    bundle = json.loads(args.input.read_text(encoding="utf-8"))
    output = read_bundle(mapping, bundle)
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if all(item["status"] == "OK" for item in output["sources"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
