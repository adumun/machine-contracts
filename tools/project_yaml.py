#!/usr/bin/env python3
"""Project human-maintainable YAML definitions into deterministic canonical JSON."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def canonical_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = canonical_json(load_yaml(args.source))
    if args.check:
        if not args.target.exists() or args.target.read_text(encoding="utf-8") != rendered:
            print(f"FAIL projection drift: {args.source} -> {args.target}")
            return 1
        print(f"PASS projection parity: {args.target}")
        return 0

    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(rendered, encoding="utf-8")
    print(f"WROTE {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
