#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path

import yaml

from tools.coi_materializer import materialize
from tools.coi_operability import assess_snapshot, diagnose_reader_output, safe_rebuild
from tools.coi_readers import read_bundle

ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "mappings" / "corporate-operating-intelligence" / "source-fact-mapping.v1.yaml"
FIXTURE_PATH = ROOT / "examples" / "corporate-operating-intelligence" / "reader-input.synthetic.json"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    mapping = yaml.safe_load(MAPPING_PATH.read_text(encoding="utf-8"))
    base_bundle = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    healthy_reader = read_bundle(mapping, base_bundle)
    healthy_snapshot = materialize(healthy_reader)
    healthy = assess_snapshot(healthy_snapshot, diagnose_reader_output(healthy_reader))
    assert_true(healthy["operational_state"] in {"HEALTHY", "DEGRADED"}, "baseline assessment missing")

    stale_bundle = copy.deepcopy(base_bundle)
    stale_bundle["sources"]["RM-FUND-001"]["freshness"]["state"] = "STALE"
    stale_reader = read_bundle(mapping, stale_bundle)
    stale_snapshot = materialize(stale_reader)
    stale = assess_snapshot(stale_snapshot, diagnose_reader_output(stale_reader))
    assert_true(stale["operational_state"] == "DEGRADED", "stale source must degrade snapshot")
    assert_true("SNAPSHOT_FRESHNESS_STALE" in stale["reasons"], "stale reason not explicit")

    unavailable_bundle = copy.deepcopy(base_bundle)
    del unavailable_bundle["sources"]["REG-RM-001"]
    unavailable_reader = read_bundle(mapping, unavailable_bundle)
    unavailable_diag = diagnose_reader_output(unavailable_reader)
    unavailable_snapshot = materialize(unavailable_reader)
    unavailable = assess_snapshot(unavailable_snapshot, unavailable_diag)
    assert_true(unavailable["operational_state"] == "DEGRADED", "single unavailable source must degrade, not invent data")
    assert_true(any(i["code"] == "SOURCE_UNAVAILABLE" for i in unavailable_diag["issues"]), "unavailable source diagnostic missing")

    drift_bundle = copy.deepcopy(base_bundle)
    lifecycle_rows = drift_bundle["sources"]["REG-INIT-LIFECYCLE-001"]["rows"]
    lifecycle_rows[0] = [h for h in lifecycle_rows[0] if h != "Current Gate"]
    for idx in range(1, len(lifecycle_rows)):
        lifecycle_rows[idx] = lifecycle_rows[idx][:-1]
    drift_reader = read_bundle(mapping, drift_bundle)
    drift_diag = diagnose_reader_output(drift_reader)
    assert_true(any(i["code"] == "SOURCE_SCHEMA_DRIFT" for i in drift_diag["issues"]), "schema drift diagnostic missing")

    recovery = safe_rebuild(mapping, unavailable_bundle, healthy_snapshot)
    assert_true(recovery["status"] == "KEEP_LAST_KNOWN_GOOD", "degraded rebuild must preserve LKG")
    assert_true(recovery["fallback"]["read_model_id"] == "RM-COI-001", "fallback snapshot identity lost")

    broken_bundle = copy.deepcopy(base_bundle)
    broken_bundle.pop("retrieved_at", None)
    failed = safe_rebuild(mapping, broken_bundle, healthy_snapshot)
    assert_true(failed["status"] == "KEEP_LAST_KNOWN_GOOD", "rebuild exception must keep LKG")
    assert_true(failed["candidate"] is None, "failed rebuild must not publish candidate")
    assert_true(failed["diagnostics"]["issues"][0]["code"] == "REBUILD_EXCEPTION", "rebuild exception diagnostic missing")

    no_fallback = safe_rebuild(mapping, broken_bundle, None)
    assert_true(no_fallback["status"] == "REBUILD_FAILED_NO_FALLBACK", "no-fallback failure state must be explicit")
    assert_true(all(v == "BLOCKED" for v in no_fallback["assessment"]["consumer_policy"].values()), "consumers must block when no usable snapshot exists")

    print("PASS: stale input degrades explicitly")
    print("PASS: unavailable source is diagnosed and does not invent facts")
    print("PASS: source schema drift is classified explicitly")
    print("PASS: degraded rebuild preserves last-known-good snapshot")
    print("PASS: rebuild exception never promotes a partial candidate")
    print("PASS: no-fallback rebuild failure blocks all consumers")
    print("PASS: local operability validation requires no GitHub Actions or paid runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
