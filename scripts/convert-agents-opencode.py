#!/usr/bin/env python3
"""Convert Claude council agents into opencode-compatible subagents.

The source frontmatter uses a deliberately small YAML shape. Conversion keeps
the existing ``description`` and ``council`` values verbatim, removes
Claude-only fields, and adds opencode's permission block plus the original
Claude tier. The accepted subset is single-line string scalars plus JSON-style
inline string lists, matching every tracked agent. No third-party YAML package
is required.

Usage:
  convert-agents-opencode.py --check <src_agents_dir>
  convert-agents-opencode.py <src_agents_dir> <dst_agents_dir>
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
TOP_LEVEL_RE = re.compile(r"^([A-Za-z0-9_-]+):[ \t]*(.*)$")
COUNCIL_FIELD_RE = re.compile(r"^  ([A-Za-z0-9_-]+):[ \t]+(.+)$")
SAFE_PLAIN_SCALAR_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 ._&'()/+-]*$")
MODEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._/-]*$")
TOP_LEVEL_FIELDS = {"name", "description", "model", "color", "tools", "council"}
COUNCIL_SCALAR_FIELDS = {"figure", "domain", "polarity", "reasoning_method"}
COUNCIL_LIST_FIELDS = {
    "polarity_pairs",
    "triads",
    "duo_keywords",
    "profiles",
    "provider_affinity",
}
COUNCIL_FIELDS = COUNCIL_SCALAR_FIELDS | COUNCIL_LIST_FIELDS


def parse_inline_value(value: str, location: str) -> object:
    if value.startswith(('"', "[")):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid inline YAML value at {location}: {error.msg}") from error
        if not isinstance(parsed, (str, list)):
            raise ValueError(f"unsupported inline YAML value at {location}")
        if isinstance(parsed, list) and not all(isinstance(item, str) for item in parsed):
            raise ValueError(f"list values must contain only strings at {location}")
        return parsed

    if not SAFE_PLAIN_SCALAR_RE.fullmatch(value):
        raise ValueError(f"unsupported or unsafe plain YAML scalar at {location}: {value}")
    if value.lower() in {"null", "true", "false", "yes", "no", "on", "off"}:
        raise ValueError(f"ambiguous YAML scalar at {location}: {value}")
    return value


def parse_frontmatter(src_path: Path) -> Tuple[Dict[str, str], List[str], str]:
    text = src_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"no frontmatter in {src_path}")

    fields: Dict[str, str] = {}
    council_lines: Optional[List[str]] = None
    seen_fields: Set[str] = set()
    seen_council_fields: Set[str] = set()
    in_council = False

    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            if in_council and council_lines is not None:
                council_lines.append(line)
            continue
        if line and not line[0].isspace():
            field_match = TOP_LEVEL_RE.match(line)
            if not field_match:
                raise ValueError(f"invalid top-level frontmatter line in {src_path}: {line}")
            key, value = field_match.groups()
            if key in seen_fields:
                raise ValueError(f"duplicate {key} in {src_path}")
            if key not in TOP_LEVEL_FIELDS:
                raise ValueError(f"unsupported top-level field {key} in {src_path}")
            seen_fields.add(key)
            in_council = key == "council"
            if in_council:
                if value:
                    raise ValueError(f"council must be a mapping in {src_path}")
                council_lines = []
            else:
                parsed_value = parse_inline_value(value, f"{src_path}:{key}")
                if key == "tools" and not isinstance(parsed_value, list):
                    raise ValueError(f"tools must be an inline string list in {src_path}")
                if key != "tools" and not isinstance(parsed_value, str):
                    raise ValueError(f"{key} must be a scalar string in {src_path}")
                if key == "model" and not MODEL_RE.fullmatch(parsed_value):
                    raise ValueError(f"unsupported model value in {src_path}: {parsed_value}")
                fields[key] = value
            continue

        if in_council and council_lines is not None:
            council_match = COUNCIL_FIELD_RE.match(line)
            if not council_match:
                raise ValueError(f"invalid council mapping line in {src_path}: {line}")
            key, value = council_match.groups()
            if key in seen_council_fields:
                raise ValueError(f"duplicate council.{key} in {src_path}")
            if key not in COUNCIL_FIELDS:
                raise ValueError(f"unsupported council field {key} in {src_path}")
            seen_council_fields.add(key)
            parsed_value = parse_inline_value(value, f"{src_path}:council.{key}")
            if key in COUNCIL_LIST_FIELDS and not isinstance(parsed_value, list):
                raise ValueError(f"council.{key} must be an inline string list in {src_path}")
            if key in COUNCIL_SCALAR_FIELDS and not isinstance(parsed_value, str):
                raise ValueError(f"council.{key} must be a scalar string in {src_path}")
            council_lines.append(line)
        elif line.strip() and not line.lstrip().startswith("#"):
            raise ValueError(f"unexpected indented frontmatter line in {src_path}: {line}")

    for required in ("description", "model"):
        if not fields.get(required):
            raise ValueError(f"missing {required} in {src_path}")
    if council_lines is None:
        raise ValueError(f"missing council mapping in {src_path}")
    missing_council_fields = COUNCIL_FIELDS - seen_council_fields
    if missing_council_fields:
        missing = ", ".join(sorted(missing_council_fields))
        raise ValueError(f"missing council fields in {src_path}: {missing}")

    return fields, council_lines, text[match.end():]


def convert(src_path: Path) -> str:
    fields, council_lines, body = parse_frontmatter(src_path)

    child_indent = "  "
    for line in council_lines:
        if line.strip() and not line.lstrip().startswith("#"):
            child_indent = line[: len(line) - len(line.lstrip())]
            break

    if any(
        line.startswith(child_indent)
        and line[len(child_indent):].startswith("claude_tier:")
        for line in council_lines
    ):
        raise ValueError(f"council.claude_tier is derived from model in {src_path}")

    new_frontmatter = [
        f"description: {fields['description']}",
        "mode: subagent",
        "permission:",
        "  edit: deny",
        "  write: deny",
        "council:",
        *council_lines,
        f"{child_indent}claude_tier: {fields['model']}",
    ]
    frontmatter_text = "\n".join(new_frontmatter)
    return f"---\n{frontmatter_text}\n---\n{body}"


def source_agents(src_dir: Path) -> List[Path]:
    if not src_dir.is_dir():
        raise ValueError(f"source agent directory not found: {src_dir}")
    agents = sorted(src_dir.glob("council-*.md"))
    if not agents:
        raise ValueError(f"no council agent files found under {src_dir}")
    return agents


def atomic_write(dst_path: Path, content: str) -> None:
    descriptor, temp_name = tempfile.mkstemp(
        dir=dst_path.parent, prefix=f".{dst_path.name}.", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.chmod(temp_name, 0o644)
        os.replace(temp_name, dst_path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def convert_all(src_dir: Path, dst_dir: Optional[Path] = None) -> int:
    converted = [(src, convert(src)) for src in source_agents(src_dir)]
    if dst_dir is None:
        return len(converted)

    dst_dir.mkdir(parents=True, exist_ok=True)
    for src, content in converted:
        atomic_write(dst_dir / src.name, content)
    return len(converted)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate sources without writing")
    parser.add_argument("src_agents_dir", type=Path)
    parser.add_argument("dst_agents_dir", nargs="?", type=Path)
    args = parser.parse_args()
    if args.check and args.dst_agents_dir is not None:
        parser.error("--check does not accept a destination directory")
    if not args.check and args.dst_agents_dir is None:
        parser.error("destination directory is required unless --check is used")
    return args


def main() -> None:
    args = parse_args()
    try:
        converted = convert_all(
            args.src_agents_dir,
            None if args.check else args.dst_agents_dir,
        )
    except (OSError, ValueError) as error:
        sys.exit(f"Error: {error}")
    print(converted)


if __name__ == "__main__":
    main()
