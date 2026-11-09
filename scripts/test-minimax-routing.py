#!/usr/bin/env python3
"""Offline regression checks for detection, routing, and coordinator HTTP templates.

Run with Python 3 and PyYAML (also used by validate-roster.py).
No provider credentials or real network calls are used.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parent.parent
MODELS = ["MiniMax-M3.1-Flash", "MiniMax-M3"]


class MiniMaxRouting(unittest.TestCase):
    def setUp(self):
        # Keep all test artifacts inside this checkout.
        self.temp = tempfile.TemporaryDirectory(prefix=".minimax-test-", dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.capture = self.work / "requests.jsonl"
        curl = self.work / "curl"
        curl.write_text('''#!/usr/bin/python3
import json, os, pathlib, sys
args = sys.argv[1:]
headers = []
for i, arg in enumerate(args):
    if arg == "-H":
        value = args[i + 1]
        headers.append(pathlib.Path(value[1:]).read_text().strip()
                       if value.startswith("@") else value)
request = {"args": args, "headers": headers}
if "-d" in args:
    request["body"] = json.loads(args[args.index("-d") + 1])
with open(os.environ["CAPTURE"], "a") as target:
    target.write(json.dumps(request) + "\\n")
if os.environ.get("CURL_FAIL"):
    sys.exit(22)
if "-o" not in args:
    print(json.dumps({"choices": [{"message": {"content": "offline reply"}}]}))
''')
        curl.chmod(0o755)
        # Prevent host CLI probes; these are unrelated to the routing under test.
        for name in ("codex", "gemini", "ollama", "cursor-agent"):
            stub = self.work / name
            stub.write_text("#!/bin/sh\nexit 1\n")
            stub.chmod(0o755)
        self.env = {
            "PATH": f"{self.work}:/usr/bin:/bin",
            "HOME": str(self.work), "LANG": "C.UTF-8",
            "CAPTURE": str(self.capture),
        }
        self.defaults = yaml.safe_load((ROOT / "configs/auto-route-defaults.yaml").read_text())

    def detect(self, **extra):
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/detect-providers.sh")],
            env={**self.env, **extra}, capture_output=True, text=True, check=True,
        )
        return {p["name"]: p for p in json.loads(result.stdout)["providers"]}

    def requests(self):
        return [json.loads(line) for line in self.capture.read_text().splitlines()]

    def dispatch(self, skill, endpoint, model, prompt="Offline council member prompt"):
        # Execute the real Bash block used by the coordinator, not a copied builder.
        text = (ROOT / skill).read_text()
        template = re.search(r'```bash\n(curl -sS -X POST "\{base_url\}/chat/completions".*?\n)```', text, re.S)
        self.assertIsNotNone(template, skill)
        script = template.group(1).replace("{base_url}", endpoint).replace("{model}", model).replace("{full prompt}", prompt)
        result = subprocess.run(
            ["bash", "-o", "pipefail", "-c", script],
            env={**self.env, "api_key_env": "MINIMAX_API_KEY", "MINIMAX_API_KEY": "offline-fixture"},
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.strip(), "offline reply")
        request = self.requests()[-1]
        self.assertIn(endpoint + "/chat/completions", request["args"])
        self.assertEqual(request["body"], {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are operating as a council member in a structured deliberation."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7, "max_tokens": 1200,
        })
        # Exact payload equality also excludes disabled thinking, none effort,
        # service_tier, and reasoning_split overrides rejected by direct Flash.
        self.assertIn("Authorization: Bearer offline-fixture", request["headers"])
        return request

    def test_detection_regions_and_missing_or_failed_credentials(self):
        self.assertFalse(self.detect()["minimax"]["available"])
        for region in ("global", "cn", "cn_zh", "CN"):
            with self.subTest(region=region):
                provider = self.detect(MINIMAX_API_KEY="offline-fixture", MINIMAX_REGION=region)["minimax"]
                self.assertTrue(provider["available"])
                self.assertEqual(provider["models"], MODELS)
                self.assertEqual(provider["exec_method"], "openai_compatible_api")
                host = "api.minimax.io" if region == "global" else "api.minimaxi.com"
                self.assertEqual(provider["binary"], f"https://{host}/v1")
        self.assertFalse(self.detect(MINIMAX_API_KEY="offline-fixture", CURL_FAIL="1")["minimax"]["available"])
        for request in self.requests():
            self.assertNotIn("offline-fixture", " ".join(request["args"]))

    def test_defaults_examples_and_nim_suggestions(self):
        self.assertEqual(list(self.defaults["provider_models"]["minimax"].values()), MODELS)
        self.assertEqual(self.defaults["chairman_defaults"]["minimax"], MODELS[0])
        example = yaml.safe_load((ROOT / "configs/provider-model-slots.minimax.example.yaml").read_text())
        self.assertEqual(example["fallback"]["model"], MODELS[0])
        seats = [s for s in example["seats"].values() if s["provider"] == "minimax"]
        self.assertEqual({s["model"] for s in seats}, set(MODELS))
        for seat in seats:
            self.dispatch("SKILL.md", seat["base_url"], seat["model"])
        nim = self.detect(NVIDIA_API_KEY="nvapi-offline-fixture")["nvidia_nim"]
        self.assertEqual(nim["models"], ["deepseek-ai/deepseek-v4-pro", "moonshotai/kimi-k2.6", "z-ai/glm-5.1", "qwen/qwen3.5-397b-a17b"])
        nim_example = yaml.safe_load((ROOT / "configs/provider-model-slots.nim.example.yaml").read_text())
        self.assertEqual(nim_example["seats"]["lao-tzu"]["provider"], "anthropic")
        self.assertEqual(len(nim_example["seats"]), 8)

    def test_detected_defaults_reach_http_boundary_in_both_regions(self):
        for region in ("global", "cn"):
            provider = self.detect(MINIMAX_API_KEY="offline-fixture", MINIMAX_REGION=region)["minimax"]
            for skill in ("SKILL.md", "SKILL.opencode.md"):
                for model in self.defaults["provider_models"]["minimax"].values():
                    with self.subTest(region=region, skill=skill, model=model):
                        self.dispatch(skill, provider["binary"], model)

    def test_explicit_saved_legacy_and_custom_models_are_not_rewritten(self):
        for model in ("MiniMax-M2.7", "minimaxai/minimax-m2.7", "private/custom-model"):
            for skill in ("SKILL.md", "SKILL.opencode.md"):
                self.dispatch(skill, "https://custom.invalid/v1", model)

    def test_quick_mode_offline_request_sequence(self):
        # Exercise two member rounds and Chairman synthesis at the HTTP boundary.
        # This is an offline routing smoke test, not a live host-agent deliberation.
        for phase in ("quick round 1", "quick round 2", "quick Chairman synthesis"):
            self.dispatch("SKILL.md", "https://api.minimax.io/v1", MODELS[0], phase)
        self.assertEqual(len(self.requests()), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
