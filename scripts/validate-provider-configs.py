#!/usr/bin/env python3
"""Validate that seats in `configs/*.yaml` name providers the coordinator can dispatch.

`scripts/detect-providers.sh` and the dispatch table in `SKILL.md` are the source of
truth for provider tags. An example seat map that names a provider neither of them
reports cannot be routed: the seat carries no `exec_method`, so the coordinator drops
it to the fallback path without an error. Example files are copy/paste templates, so
that drift turns into a silent per-seat fallback for everyone who follows the README.

Custom endpoints are supported, but only through the documented
`openai_compatible_api` contract, which requires `base_url` and `api_key_env`
(SKILL.md STEP 1, Path A, rule 4).

Usage: validate-provider-configs.py [repo_root]
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(
        "Error: PyYAML is required. Install it with: pip3 install --user pyyaml"
    )

DETECTED_PROVIDER_RE = re.compile(r'json_provider "([a-z_]+)"')
OPENAI_COMPATIBLE = "openai_compatible_api"
ROUTING_KEYS = ("provider_models", "chairman_defaults")

failures = []
checks = 0


def fail(message):
    """Record one failed check."""
    global checks
    checks += 1
    failures.append(message)


def check(condition, message):
    """Record one check, failing it when the condition does not hold."""
    global checks
    if condition:
        checks += 1
    else:
        fail(message)


def is_dispatchable(seat, providers):
    """A seat routes when its provider is detected or it declares the API contract."""
    provider = seat.get("provider")
    if provider in providers:
        return True
    return (
        seat.get("exec_method") == OPENAI_COMPATIBLE
        and bool(seat.get("base_url"))
        and bool(seat.get("api_key_env"))
    )


def describe(seat, providers):
    provider = seat.get("provider")
    if provider in providers:
        return f"provider '{provider}'"
    return (
        f"provider '{provider}' (not reported by detect-providers.sh, and the seat does "
        f"not set exec_method: {OPENAI_COMPATIBLE} with base_url + api_key_env)"
    )


def main():
    # Default to the repo root relative to this script, so the check behaves the
    # same from any working directory (matching validate-roster.py).
    default_root = Path(__file__).resolve().parent.parent
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_root

    detector = (root / "scripts" / "detect-providers.sh").read_text(encoding="utf-8")
    providers = set(DETECTED_PROVIDER_RE.findall(detector))
    if not providers:
        sys.exit("No providers found in scripts/detect-providers.sh")

    for path in sorted((root / "configs").glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        for member, seat in sorted((data.get("seats") or {}).items()):
            if not isinstance(seat, dict):
                fail(f"{path.name}: seat '{member}' is not a mapping")
                continue
            check(
                is_dispatchable(seat, providers),
                f"{path.name}: seat '{member}' uses {describe(seat, providers)}",
            )

        fallback = data.get("fallback")
        if isinstance(fallback, dict):
            check(
                is_dispatchable(fallback, providers),
                f"{path.name}: fallback uses {describe(fallback, providers)}",
            )

        # auto-route-defaults.yaml keys tier/chairman lookups by provider tag, so an
        # unknown key is dead configuration the router can never read.
        for key in ROUTING_KEYS:
            block = data.get(key)
            if not isinstance(block, dict):
                continue
            for provider in sorted(block):
                check(
                    provider in providers,
                    f"{path.name}: {key} names provider '{provider}' that "
                    f"detect-providers.sh never reports",
                )

    print(f"== Provider Config Validation ==\nproviders: {', '.join(sorted(providers))}")
    print(f"checks: {checks}")
    if failures:
        for line in failures:
            print(f"[FAIL] {line}")
        sys.exit(f"\n{len(failures)} problem(s) found")
    print("[PASS] Every configured seat names a dispatchable provider")


if __name__ == "__main__":
    main()
