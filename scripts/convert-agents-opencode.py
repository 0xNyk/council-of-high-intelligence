#!/usr/bin/env python3
"""Convert council-*.md Claude subagent files into opencode-compatible subagent files.

opencode's agent frontmatter schema is stricter than Claude's: it rejects the
`tools: [...]` array (deprecated in opencode, replaced by `permission`), rejects
free-form `color` names (must be a hex code or a fixed theme keyword), and has
no notion of Claude's `opus`/`sonnet` model aliases. This script re-shapes each
agent's frontmatter to fit while preserving the original routing metadata
(`council:` block, including the Claude tier) for the coordinator skill to
reference.

Usage: convert-agents-opencode.py <src_agents_dir> <dst_agents_dir>
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

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def convert(src_path: Path) -> str:
    text = src_path.read_text()
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"no frontmatter in {src_path}")
    fm = yaml.safe_load(m.group(1))
    body = text[m.end():]

    council = fm.get("council", {}) or {}
    council["claude_tier"] = fm.get("model")

    new_fm = {
        "description": fm["description"],
        "mode": "subagent",
        "permission": {"edit": "deny", "write": "deny"},
        "council": council,
    }

    new_frontmatter = yaml.safe_dump(
        new_fm, sort_keys=False, default_flow_style=False, allow_unicode=True
    )
    return f"---\n{new_frontmatter}---\n{body}"


def main():
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} <src_agents_dir> <dst_agents_dir>")
    src_dir, dst_dir = Path(sys.argv[1]), Path(sys.argv[2])
    dst_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    for src in sorted(src_dir.glob("council-*.md")):
        (dst_dir / src.name).write_text(convert(src))
        converted += 1

    print(converted)


if __name__ == "__main__":
    main()
