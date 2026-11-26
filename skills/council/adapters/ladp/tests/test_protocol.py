"""Shared YAML contract tests without any agent/provider process."""
import copy
import os
import tempfile
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADAPTER))
sys.path.insert(0, str(ADAPTER.parents[1] / "core"))
import policy
import protocol


class SharedProtocolTest(unittest.TestCase):
    def setUp(self):
        self.config = protocol.load()

    def test_default_canonical_and_native_compatibility(self):
        self.assertEqual(protocol.transport_phases(self.config, "full"),
                         ("lobby", "restate", "commit", "reveal", "debate", "enforce", "position", "synthesis"))
        self.assertEqual(protocol.transport_phases(self.config, "quick"),
                         ("lobby", "commit", "reveal", "position", "synthesis"))
        self.assertEqual(protocol.transport_phases(self.config, "duo"),
                         ("lobby", "commit", "reveal", "debate", "position", "synthesis"))
        self.assertEqual(self.config["word_limits"]["full"]["analysis"], 400)
        for host in ("codex", "gemini"):
            self.assertEqual(self.config["native_hosts"][host]["word_limits"]["full"]["analysis"], 300)
            self.assertTrue(self.config["native_hosts"][host]["separate_restatement"])
        self.assertFalse(self.config["native_hosts"]["opencode"]["confidence_weighting"])

    def test_all_native_skills_reference_single_configuration(self):
        repo = ADAPTER.parents[3]
        for host, name in (("claude", "SKILL.md"), ("codex", "SKILL.codex.md"),
                           ("gemini", "SKILL.gemini.md"), ("opencode", "SKILL.opencode.md")):
            with self.subTest(host=host):
                text = (repo / name).read_text(encoding="utf-8")
                for key in ("configs/discussion-protocol.yaml", "voting.expert_weight",
                            "voting.member_weight", "voting.consensus_threshold",
                            "voting.confidence_weights", "enforcement.agreement_percent",
                            "word_limits", "modes.<mode>", f"native_hosts.{host}"):
                    self.assertIn(key, text)
                for obsolete in ("2/3", "1.5×", "0.75", ">70%", ">80%"):
                    self.assertNotIn(obsolete, text)

    def test_reject_invalid_schema_and_weights(self):
        cases = [
            ("schema version", lambda c: c.update(schema_version=2)),
            ("unknown field", lambda c: c.update(typo=True)),
            ("duplicate stages", lambda c: c["modes"]["full"]["stages"].insert(1, "restatement")),
            ("wrong order", lambda c: c["modes"]["quick"]["stages"].reverse()),
            ("missing phase", lambda c: c["modes"]["duo"]["stages"].remove("analysis")),
            ("unsupported mode", lambda c: c["modes"].update(other={})),
            ("invalid threshold", lambda c: c["voting"]["consensus_threshold"].update(numerator=1)),
            ("zero denominator", lambda c: c["voting"]["consensus_threshold"].update(denominator=0)),
            ("boolean weight", lambda c: c["voting"].update(member_weight=True)),
            ("infinite weight", lambda c: c["voting"].update(expert_weight=float("inf"))),
            ("huge weight", lambda c: c["voting"].update(expert_weight=10**1000)),
            ("inverted weights", lambda c: c["voting"].update(expert_weight=0.5)),
            ("invalid host override", lambda c: c["native_hosts"]["codex"].update(parallel_rounds="true")),
            ("unknown confidence", lambda c: c["voting"]["confidence_weights"].update(other=1)),
        ]
        for label, mutate in cases:
            with self.subTest(label=label):
                c = copy.deepcopy(self.config)
                mutate(c)
                with self.assertRaisesRegex(ValueError, "invalid discussion protocol"):
                    protocol.validate(c)

    def test_custom_weights_use_exact_rational_arithmetic(self):
        config = copy.deepcopy(self.config)
        config["voting"].update(member_weight=0.7, expert_weight=1.1)
        config["voting"]["confidence_weights"]["med"] = 0.6
        protocol.validate(config)
        state = {"protocol": config, "mode": "quick", "panel": ["ada", "feynman", "torvalds"],
                 "expert": "ada", "withdrawals": {},
                 "members": {seat: {"seat": seat, "active": True}
                             for seat in ("ada", "feynman", "torvalds")},
                 "votes": {
                     "ada": {"stance": "A", "confidence": "med", "dealbreaker": "no"},
                     "feynman": {"stance": "A", "confidence": "high", "dealbreaker": "no"},
                     "torvalds": {"stance": "B", "confidence": "high", "dealbreaker": "no"},
                 }}
        tally = policy.tally(state, [])
        scale = int(tally["unit"].split("/")[1].split()[0])
        self.assertEqual(Fraction(tally["scores"]["a"], scale), Fraction("1.36"))
        self.assertEqual(Fraction(tally["scores"]["b"], scale), Fraction("0.7"))
        self.assertEqual(Fraction(tally["total_units"], scale), Fraction("2.5"))
        self.assertIsNone(tally["consensus"])

    def test_config_introspection_does_not_create_storage(self):
        with tempfile.TemporaryDirectory(prefix="ladp-introspection-") as tmp:
            root = Path(tmp) / "absent"
            env = dict(os.environ, COUNCIL_LADP_HOME=str(root), PYTHONDONTWRITEBYTECODE="1")
            for command in ("protocol", "roster"):
                result = subprocess.run([sys.executable, str(ADAPTER / "adapter.py"), command],
                                        env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(root.exists())

    def test_core_has_no_pyyaml_dependency(self):
        proc = subprocess.run([sys.executable, "-S", "-B", "-c",
                               "import sys; sys.path.insert(0,sys.argv[1]); "
                               "from ladp_core.metadata import DiscussionStore; "
                               "from ladp_core.sessions import SessionStore; "
                               "assert 'yaml' not in sys.modules",
                               str(ADAPTER.parents[1] / "core")],
                              text=True, capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = subprocess.run([sys.executable, "-S", "-B", str(ADAPTER / "adapter.py"), "protocol"],
                              text=True, capture_output=True, timeout=10)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("LADP requires PyYAML", proc.stderr)


if __name__ == "__main__":
    unittest.main()
