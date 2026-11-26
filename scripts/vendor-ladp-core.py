#!/usr/bin/env python3
"""Verify or synchronize a reviewed LADP Core source release (no network)."""
import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "skills/council/adapters/ladp/ladp_core"
FILES = ("__init__.py", "storage.py", "metadata.py", "sessions.py", "LICENSE")


def manifest(source):
    data = json.loads((source / "release.json").read_text(encoding="utf-8"))
    if data.get("api_version") != 1 or not isinstance(data.get("version"), str):
        raise ValueError("unsupported LADP Core API version")
    if set(data.get("sha256", {})) != set(FILES):
        raise ValueError("unexpected LADP Core release file set")
    for name in FILES:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("missing or unsafe release file: " + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != data["sha256"][name]:
            raise ValueError("LADP Core release checksum mismatch: " + name)
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="local LADP Core package directory containing release.json")
    args = parser.parse_args()
    if args.source:
        source = args.source.resolve()
        if source == TARGET.resolve():
            parser.error("source must be the independently maintained package, not the vendor directory")
        data = manifest(source)
        for name in (*FILES, "release.json"):
            (TARGET / name).write_bytes((source / name).read_bytes())
        print("Synchronized LADP Core", data["version"])
    data = manifest(TARGET)
    print("Verified LADP Core", data["version"], "API", data["api_version"])


if __name__ == "__main__":
    main()
