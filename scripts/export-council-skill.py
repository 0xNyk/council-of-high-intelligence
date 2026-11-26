#!/usr/bin/env python3
"""Export a self-contained Council Skill for local skill managers."""
import argparse
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HOSTS = {"claude": "SKILL.md", "codex": "SKILL.codex.md",
         "gemini": "SKILL.gemini.md", "opencode": "SKILL.opencode.md"}


def export(output, host):
    # Require a new directory; never overwrite an installed skill.
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(REPO / HOSTS[host], output / "SKILL.md")
    agents = output / "agents"
    agents.mkdir()
    for path in (REPO / "agents").glob("council-*.md"):
        shutil.copy2(path, agents / path.name)
    configs = output / "configs"
    configs.mkdir()
    config_source = REPO / "configs"
    for path in [config_source / "auto-route-defaults.yaml",
                 *sorted(config_source.glob("provider-model-slots*.example.yaml"))]:
        shutil.copy2(path, configs / path.name)
    scripts = output / "scripts"
    scripts.mkdir()
    for path in (REPO / "scripts").glob("detect-*.sh"):
        shutil.copy2(path, scripts / path.name)
    adapter = REPO / "skills/council/adapters/ladp"
    # Copy the same allowlisted files as the native installer. Do not export
    # tests, local config overrides, scratch files or arbitrary user data.
    dest = output / "adapters/ladp"
    (dest / "ladp_core").mkdir(parents=True)
    for name in ("README.md", "adapter.py", "policy.py", "resources.py", "compatibility.json"):
        shutil.copy2(adapter / name, dest / name)
    for name in ("__init__.py", "storage.py", "metadata.py", "sessions.py", "release.json", "LICENSE"):
        shutil.copy2(adapter / "ladp_core" / name, dest / "ladp_core" / name)
    pinned = dest / "resources"
    pinned.mkdir()
    shutil.copy2(REPO / "SKILL.md", pinned / "SKILL.md")
    shutil.copytree(agents, pinned / "agents")
    shutil.copy2(REPO / "LICENSE", output / "LICENSE")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--host", choices=HOSTS, default="claude")
    args = p.parse_args()
    export(args.output, args.host)
    print("Exported Council Skill:", args.output)


if __name__ == "__main__":
    main()
