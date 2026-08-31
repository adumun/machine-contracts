#!/usr/bin/env python3
"""Stack-neutral contract tests for ADUMUN communication standards.

The normative JSON Schemas stay in the Standards repository. This runner consumes a
checkout/path supplied by the caller so the implementation never becomes normative
by copying or silently redefining those contracts.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


def load_data(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) if path.suffix.lower() in {".yaml", ".yml"} else json.load(fh)


def schema_errors(schema_path: Path, body) -> list[str]:
    schema = load_data(schema_path)
    validator = Draft202012Validator(schema)
    return [
        f"{'.'.join(str(x) for x in err.absolute_path) or '$'}: {err.message}"
        for err in sorted(validator.iter_errors(body), key=lambda e: list(e.path))
    ]


def check_required_headers(headers, required: list[str]) -> list[str]:
    normalized = {str(k).lower(): str(v) for k, v in headers.items()}
    return [f"missing required response header: {name}" for name in required if name.lower() not in normalized]


def read_live(base_url: str, scenario: dict):
    url = base_url.rstrip("/") + scenario["path"]
    request = urllib.request.Request(url=url, method=scenario.get("method", "GET"))
    for name, value in scenario.get("request_headers", {}).items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=float(scenario.get("timeout_seconds", 5))) as response:
            status = response.status
            headers = dict(response.headers.items())
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        status = exc.code
        headers = dict(exc.headers.items())
        raw = exc.read().decode("utf-8")
    body = json.loads(raw) if raw else None
    return status, headers, body


def run_scenario(scenario: dict, standards_root: Path, suite_root: Path, base_url: str | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if base_url and scenario.get("path"):
        status, headers, body = read_live(base_url, scenario)
        expected_status = scenario.get("expected_status")
        if expected_status is not None and status != expected_status:
            errors.append(f"status: expected {expected_status}, got {status}")
        errors.extend(check_required_headers(headers, scenario.get("required_response_headers", [])))
    else:
        body_file = scenario.get("body_file")
        if not body_file:
            return False, ["scenario requires body_file when --base-url is not supplied"]
        source_root = standards_root if scenario.get("body_source", "standards") == "standards" else suite_root
        body = load_data(source_root / body_file)
        headers = scenario.get("response_headers", {})
        errors.extend(check_required_headers(headers, scenario.get("required_response_headers", [])))

    schema_path = standards_root / scenario["schema_path"]
    errors.extend(schema_errors(schema_path, body))

    request_id_path = scenario.get("request_id_json_path")
    if request_id_path:
        cursor = body
        for part in request_id_path.split("."):
            cursor = cursor.get(part) if isinstance(cursor, dict) else None
        if not cursor:
            errors.append(f"missing request identifier at {request_id_path}")
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="ADUMUN communication contract test kit")
    parser.add_argument("--standards-root", required=True, type=Path, help="checkout/path of the authoritative Standards repository")
    parser.add_argument("--suite", type=Path, default=Path(__file__).with_name("example-suite.yaml"))
    parser.add_argument("--base-url", help="optional live target; without it, fixture mode is used")
    args = parser.parse_args()

    suite = load_data(args.suite)
    expected_versions = suite.get("standards", {})
    if not expected_versions:
        print("FAIL: suite must pin exact standard versions")
        return 2

    failures = 0
    for scenario in suite.get("scenarios", []):
        try:
            ok, errors = run_scenario(scenario, args.standards_root, args.suite.parent, args.base_url)
        except Exception as exc:
            ok, errors = False, [str(exc)]
        if ok:
            print(f'PASS {scenario["id"]}')
        else:
            failures += 1
            print(f'FAIL {scenario.get("id", "UNKNOWN")}')
            for error in errors:
                print(f"  - {error}")
    total = len(suite.get("scenarios", []))
    print(f'{"PASS" if failures == 0 else "FAIL"}: {total - failures}/{total} communication scenarios')
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
