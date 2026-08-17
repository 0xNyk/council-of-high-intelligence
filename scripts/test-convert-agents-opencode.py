#!/usr/bin/env python3
"""Regression tests for the dependency-free opencode agent converter."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CONVERTER = Path(__file__).with_name("convert-agents-opencode.py")
VALID_AGENT = """---
name: council-ada
description: "Council member: formal systems & abstraction."
model: sonnet
color: cyan
tools: ["Read", "Bash"]
council:
  figure: Ada Lovelace
  domain: "Formal systems & abstraction"
  polarity: "What can/can't be mechanized"
  polarity_pairs: ["machiavelli"]
  triads: ["architecture", "debugging"]
  duo_keywords: ["formalization", "systems"]
  profiles: ["classic", "execution-lean"]
  provider_affinity: ["openai", "anthropic"]
  reasoning_method: formal-stepwise-verification
---

## Identity

Test body.
"""


class ConverterTests(unittest.TestCase):
    def run_converter(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-S", str(CONVERTER), *args],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

    def test_conversion_uses_only_standard_library_and_preserves_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            src_dir = root / "src"
            dst_dir = root / "dst"
            src_dir.mkdir()
            (src_dir / "council-ada.md").write_text(VALID_AGENT, encoding="utf-8")

            result = self.run_converter(str(src_dir), str(dst_dir))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "1")
            converted_path = dst_dir / "council-ada.md"
            converted = converted_path.read_text(encoding="utf-8")
            self.assertEqual(converted_path.stat().st_mode & 0o777, 0o644)
            self.assertIn('description: "Council member: formal systems & abstraction."', converted)
            self.assertIn("permission:\n  edit: deny\n  write: deny", converted)
            self.assertIn('profiles: ["classic", "execution-lean"]', converted)
            self.assertIn("claude_tier: sonnet", converted)
            self.assertIn("## Identity\n\nTest body.", converted)
            for removed_field in ("name:", "model:", "color:", "tools:"):
                self.assertNotIn(f"\n{removed_field}", converted.split("council:", 1)[0])

    def test_check_validates_without_creating_a_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            src_dir = Path(temp_dir) / "src"
            src_dir.mkdir()
            (src_dir / "council-ada.md").write_text(VALID_AGENT, encoding="utf-8")

            result = self.run_converter("--check", str(src_dir))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), "1")
            self.assertEqual(list(Path(temp_dir).iterdir()), [src_dir])

    def test_invalid_source_fails_before_writing_any_agents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            src_dir = root / "src"
            dst_dir = root / "dst"
            src_dir.mkdir()
            (src_dir / "council-ada.md").write_text(VALID_AGENT, encoding="utf-8")
            invalid = VALID_AGENT.replace("model: sonnet\n", "")
            (src_dir / "council-broken.md").write_text(invalid, encoding="utf-8")

            result = self.run_converter(str(src_dir), str(dst_dir))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing model", result.stderr)
            self.assertFalse(dst_dir.exists())

    def test_rejects_malformed_or_ambiguous_yaml_subset(self) -> None:
        malformed_cases = {
            "unquoted colon": VALID_AGENT.replace(
                'description: "Council member: formal systems & abstraction."',
                "description: Council member: formal systems & abstraction.",
            ),
            "invalid council mapping": VALID_AGENT.replace(
                "  figure: Ada Lovelace",
                "  figure Ada Lovelace",
            ),
            "duplicate council key": VALID_AGENT.replace(
                "  figure: Ada Lovelace",
                "  figure: Ada Lovelace\n  figure: Duplicate",
            ),
            "yaml alias": VALID_AGENT.replace(
                "  figure: Ada Lovelace",
                "  figure: *ada",
            ),
            "implicit date": VALID_AGENT.replace(
                "  figure: Ada Lovelace",
                "  figure: 2026-07-22",
            ),
            "implicit hexadecimal integer": VALID_AGENT.replace(
                "  figure: Ada Lovelace",
                "  figure: 0x10",
            ),
            "implicit numeric separator": VALID_AGENT.replace(
                "  figure: Ada Lovelace",
                "  figure: 1_000",
            ),
            "implicit scientific float": VALID_AGENT.replace(
                "  figure: Ada Lovelace",
                "  figure: 1.0e+3",
            ),
        }

        for case_name, content in malformed_cases.items():
            with self.subTest(case=case_name), tempfile.TemporaryDirectory() as temp_dir:
                src_dir = Path(temp_dir) / "src"
                src_dir.mkdir()
                (src_dir / "council-ada.md").write_text(content, encoding="utf-8")

                result = self.run_converter("--check", str(src_dir))

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Error:", result.stderr)


if __name__ == "__main__":
    unittest.main()
