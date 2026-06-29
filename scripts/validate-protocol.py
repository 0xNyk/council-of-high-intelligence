#!/usr/bin/env python3
"""Validate that council docs, agents, and config examples match protocol.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "protocol.json"
SKILL_FILES = ["SKILL.md", "SKILL.codex.md", "SKILL.gemini.md"]


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def load_protocol() -> dict:
    try:
        return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail("protocol.json is missing")
    except json.JSONDecodeError as exc:
        fail(f"protocol.json is invalid JSON: {exc}")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"{path.relative_to(ROOT)} is missing")


def validate_agents(protocol: dict) -> None:
    members = protocol["members"]
    for member in members:
        agent_path = ROOT / "agents" / f"council-{member}.md"
        if not agent_path.exists():
            fail(f"agent missing for protocol member: {member}")

    for triad, triad_members in protocol["triads"].items():
        unknown = sorted(set(triad_members) - set(members))
        if unknown:
            fail(f"triad {triad} references unknown members: {', '.join(unknown)}")

    for profile, profile_members in protocol["profiles"].items():
        unknown = sorted(set(profile_members) - set(members))
        if unknown:
            fail(f"profile {profile} references unknown members: {', '.join(unknown)}")


def validate_skill_files(protocol: dict) -> None:
    flags = protocol["flags"].keys()
    triads = protocol["triads"].keys()
    profiles = protocol["profiles"].keys()
    sections = protocol["verdict_sections"]

    for skill_name in SKILL_FILES:
        text = read_text(ROOT / skill_name)
        for flag in flags:
            if flag not in text:
                fail(f"{skill_name} does not document protocol flag {flag}")
        for triad in triads:
            if triad not in text:
                fail(f"{skill_name} does not document protocol triad {triad}")
        for profile in profiles:
            if profile not in text:
                fail(f"{skill_name} does not document protocol profile {profile}")
        for section in sections:
            if section not in text:
                fail(f"{skill_name} does not document verdict section {section}")


def config_provider_values(config_text: str) -> list[str]:
    return re.findall(r"(?m)^\s+provider:\s*([A-Za-z0-9_-]+)\s*$", config_text)


def config_seat_names(config_text: str) -> list[str]:
    seats_match = re.search(r"(?ms)^seats:\n(?P<body>.*?)(?:^\S|\Z)", config_text)
    if not seats_match:
        return []
    body = seats_match.group("body")
    return re.findall(r"(?m)^  ([a-z0-9-]+):\s*$", body)


def validate_configs(protocol: dict) -> None:
    known_providers = set(protocol["supported_providers"]) | set(protocol["manual_only_providers"])
    members = set(protocol["members"])

    for config_path in sorted((ROOT / "configs").glob("*.yaml")):
        text = read_text(config_path)
        for provider in config_provider_values(text):
            if provider not in known_providers:
                fail(f"{config_path.relative_to(ROOT)} references unknown provider: {provider}")
        for seat in config_seat_names(text):
            if seat not in members:
                fail(f"{config_path.relative_to(ROOT)} references unknown seat: {seat}")

        if "openai_compatible_api" in text:
            for required in ("base_url", "api_key_env"):
                if required not in text:
                    fail(f"{config_path.relative_to(ROOT)} uses openai_compatible_api without {required}")


def main() -> int:
    protocol = load_protocol()
    validate_agents(protocol)
    validate_skill_files(protocol)
    validate_configs(protocol)
    print("[PASS] protocol.json matches skill docs, agents, and config examples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
