"""Executable transport tests. No model/provider processes or network calls."""
import concurrent.futures
import fcntl
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ADAPTER = Path(__file__).resolve().parents[1]
CLI = ADAPTER / "adapter.py"
sys.path.insert(0, str(ADAPTER))
import policy
import resources
from core.metadata import DiscussionStore, DiscussionMetadata


class AdapterTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="council-ladp-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = dict(os.environ, COUNCIL_LADP_HOME=str(self.root),
                        PYTHONDONTWRITEBYTECODE="1")
        self.store = DiscussionStore(self.root, policy)

    def raw(self, *args, cli=CLI):
        return subprocess.run([sys.executable, str(cli), *map(str, args)],
                              env=self.env, capture_output=True, text=True, timeout=12)

    def call(self, *args, ok=True, cli=CLI):
        p = self.raw(*args, cli=cli)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr)
            return json.loads(p.stdout)
        self.assertNotEqual(p.returncode, 0)
        return p.stderr

    def create(self, mode="full", members="ada,feynman,torvalds", expert=None):
        args = ["create", "--name", "host", "--title", "Repository design",
                "--topic", "Choose a repository structure.", "--mode", mode,
                "--members", members]
        if expert:
            args += ["--expert", expert]
        return self.call(*args)

    def join(self, room, seat):
        return self.call("join", room["discussion"], "--seat", seat, "--name", "session-" + seat)

    def act(self, room, actor, action, *args, ok=True):
        return self.call(action, room["discussion"], "--actor", actor["actor"], *args, ok=ok)

    def status(self, room):
        return self.call("status", room["discussion"])

    def view(self, room, actor):
        return self.act(room, actor, "view")

    def panel(self, mode, members, expert=None, chairman=True):
        room = self.create(mode, ",".join(members), expert)
        seats = [self.join(room, s) for s in members]
        chair = self.join(room, "chairman") if chairman else None
        self.act(room, room, "advance", *([] if chairman else
                                          ["--fallback-reason", "user-selected fallback"]))
        return room, seats, chair

    def commit_reveal(self, room, members):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(members)) as pool:
            list(pool.map(lambda m: self.act(room, m, "commit", "--content",
                        "Private analysis by " + m["seat"]), members))
        self.assertNotIn("Private analysis", self.store.path(room["discussion"]).read_text())
        self.act(room, room, "advance")
        self.act(room, members[0], "reveal")
        self.assertFalse(any(x["phase"] == "reveal" for x in
                             self.view(room, members[1])["transcript"]))
        for member in members[1:]:
            self.act(room, member, "reveal")
        self.act(room, room, "advance")

    def vote(self, room, who, stance, confidence="high", dealbreaker="no"):
        self.act(room, who, "submit", "--stance", stance, "--confidence", confidence,
                 "--dealbreaker", dealbreaker, "--content", "Final rationale")

    def finish(self, room, chair):
        self.assertEqual(self.status(room)["phase"], "synthesis")
        if chair:
            view = self.view(room, chair)
            self.assertIn("Concrete Next Step", view["reference"])
            self.assertTrue(any(x["phase"] == "position" for x in view["transcript"]))
            self.act(room, chair, "submit", "--content", "Independent verdict")
            self.act(room, room, "close", "--content", "replacement", ok=False)
            self.act(room, room, "close")
            self.assertEqual(self.view(room, room)["verdict"], "Independent verdict")
        else:
            self.act(room, room, "close", "--content", "Explicit fallback verdict")
            self.assertEqual(self.view(room, room)["verdict"], "Explicit fallback verdict")
        self.assertEqual(self.status(room)["phase"], "closed")

    def test_full_mode_restate_sequential_anonymous_and_enforcement(self):
        room, members, chair = self.panel("full", ["ada", "feynman", "torvalds"], "ada")
        a, b, c = members
        self.assertEqual(self.status(room)["phase"], "restate")
        self.act(room, chair, "submit", "--content", "premature verdict", ok=False)
        self.act(room, room, "advance", ok=False)
        for member in members:
            self.act(room, member, "submit", "--content", "Restate and reframe")
        self.act(room, room, "advance")
        self.commit_reveal(room, members)
        self.assertEqual(self.status(room)["phase"], "debate")
        bv = self.view(room, b)
        self.assertFalse(bv["eligible"])
        self.assertTrue(all(x["member"].startswith("Member ") for x in bv["transcript"]))
        self.assertEqual(self.view(room, chair)["transcript"], [])
        self.act(room, b, "submit", "--content", "out of order", ok=False)
        self.act(room, a, "submit", "--content", "First cross-examination")
        self.assertTrue(self.view(room, b)["eligible"])
        self.assertTrue(any(x["phase"] == "debate" for x in self.view(room, b)["transcript"]))
        for member in (b, c):
            self.act(room, member, "submit", "--content", "Specific counterargument")
        self.act(room, room, "advance", ok=False)
        self.act(room, room, "advance", "--enforcement", "Scanned all upstream checks",
                 "--followup", "ada=state the strongest counterexample")
        self.assertEqual(self.status(room)["phase"], "enforce")
        self.assertIn("counterexample", self.view(room, a)["followup"])
        self.act(room, b, "submit", "--content", "unsolicited", ok=False)
        self.act(room, a, "submit", "--content", "Counterexample")
        self.act(room, room, "advance")
        self.vote(room, a, "monorepo")
        self.vote(room, b, "single repo")
        self.vote(room, c, "polyrepo", dealbreaker="yes")
        self.act(room, room, "advance", "--alias", "single repo=monorepo")
        result = self.status(room)["result"]
        self.assertEqual(result["total_units"], 56)
        self.assertEqual(result["scores"]["monorepo"], 40)
        self.assertEqual(result["consensus"], "monorepo")
        self.assertTrue(any(x["dealbreaker"] == "yes" for x in result["ballots"]))
        self.finish(room, chair)
        state = self.store.state(room["discussion"])
        self.assertEqual(state, policy.reconstruct(self.store.read(room["discussion"])))

    def test_quick_mode_skips_debate_and_keeps_split(self):
        room, members, chair = self.panel("quick", ["ada", "feynman"])
        self.assertEqual(self.status(room)["phase"], "commit")
        self.commit_reveal(room, members)
        self.assertEqual(self.status(room)["phase"], "position")
        v = self.view(room, members[0])
        self.assertEqual(len(v["transcript"]), 2)
        self.assertTrue(all(x["member"].startswith("Member ") for x in v["transcript"]))
        self.act(room, members[0], "submit", "--content", "missing vote", ok=False)
        self.vote(room, members[0], "A")
        self.assertFalse(any(x["phase"] == "position" for x in self.view(room, members[1])["transcript"]))
        self.vote(room, members[1], "B", confidence="med")
        self.act(room, room, "advance")
        self.assertIsNone(self.status(room)["result"]["consensus"])
        self.finish(room, chair)

    def test_duo_mode_named_direct_response_without_vote(self):
        room, members, chair = self.panel("duo", ["ada", "torvalds"])
        self.commit_reveal(room, members)
        v = self.view(room, members[0])
        self.assertEqual({x["member"] for x in v["transcript"]}, {"ada", "torvalds"})
        for m in members:
            self.act(room, m, "submit", "--content", "Direct response")
        self.act(room, room, "advance")
        for m in members:
            self.act(room, m, "submit", "--content", "Final statement")
        self.act(room, room, "advance")
        self.assertEqual(self.status(room)["result"]["kind"], "dialectic")
        self.finish(room, chair)

    def test_large_full_panel_can_cross_examine_in_parallel(self):
        room, members, chair = self.panel("full", ["ada", "feynman", "torvalds",
                                                   "socrates", "taleb"])
        for member in members:
            self.act(room, member, "submit", "--content", "Restatement")
        self.act(room, room, "advance")
        self.commit_reveal(room, members)
        self.assertTrue(all(self.view(room, m)["eligible"] for m in members))
        self.act(room, members[-1], "submit", "--content", "Last seat first")
        self.assertFalse(any(x["phase"] == "debate" for x in
                             self.view(room, members[0])["transcript"]))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda m: self.act(room, m, "submit", "--content",
                                             "Independent cross-examination"), members[:-1]))
        self.act(room, room, "advance", "--enforcement", "No follow-up")
        self.assertEqual(self.status(room)["phase"], "position")
        self.act(room, room, "abort", "--content", "scenario complete")

    def test_incomplete_tail_repaired_complete_corruption_rejected(self):
        room = self.create("quick", "ada,feynman")
        d = room["discussion"]
        path = self.store.path(d)
        with path.open("ab") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(b'{"seq":')
        self.assertEqual(self.status(room)["last_seq"], 1)
        self.join(room, "ada")
        self.assertEqual(self.status(room)["last_seq"], 2)
        with path.open("ab") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(b'not-json\n')
        original = path.read_bytes()
        self.call("status", d, ok=False)
        self.call("join", d, "--seat", "feynman", "--name", "other", ok=False)
        self.assertEqual(path.read_bytes(), original)

    def test_all_upstream_members_and_invalid_seats(self):
        seats = resources.roster()
        self.assertGreaterEqual(len(seats), 18)
        r = self.create("full", ",".join(seats))
        self.assertEqual(len(self.status(r)["panel"]), len(seats))
        self.call("join", r["discussion"], "--seat", "../../etc", "--name", "bad", ok=False)
        self.call("create", "--title", "x", "--topic", "x", "--name", "x",
                  "--members", "ada,ada", ok=False)
        self.call("create", "--title", "x", "--topic", "x", "--name", "x",
                  "--members", "ada,unknown", ok=False)

    def test_missing_seats_and_explicit_chairman_fallback(self):
        r = self.create("quick", "ada,feynman")
        a = self.join(r, "ada")
        self.act(r, r, "advance", "--fallback-reason", "no chair", ok=False)
        self.call("join", r["discussion"], "--seat", "ada", "--name", "duplicate", ok=False)
        b = self.join(r, "feynman")
        self.act(r, r, "advance", ok=False)
        self.act(r, r, "advance", "--fallback-reason", "user accepted fallback")
        self.commit_reveal(r, [a, b])
        for m in (a, b):
            self.vote(r, m, "abstain")
        self.act(r, r, "advance")
        self.assertIsNone(self.status(r)["result"]["consensus"])
        self.finish(r, None)

    def test_concurrent_duplicate_seat_and_commit(self):
        r = self.create("quick", "ada,feynman")
        def join(i):
            return self.raw("join", r["discussion"], "--seat", "ada", "--name", str(i))
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            values = list(pool.map(join, range(6)))
        successes = [p for p in values if p.returncode == 0]
        self.assertEqual(len(successes), 1)
        a = json.loads(successes[0].stdout)
        self.join(r, "feynman")
        self.join(r, "chairman")
        self.act(r, r, "advance")
        def commit(i):
            return self.raw("commit", r["discussion"], "--actor", a["actor"],
                            "--content", "candidate " + str(i))
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(sum(p.returncode == 0 for p in pool.map(commit, range(6))), 1)
        self.assertEqual(self.status(r)["pending"], ["feynman"])

    def test_snapshot_recovery_after_real_process_exit(self):
        r = self.create("quick", "ada,feynman")
        d = r["discussion"]
        previous = self.store.meta_path(d).read_bytes()
        code = """
import os,sys
sys.path.insert(0,sys.argv[1])
from core.metadata import DiscussionMetadata
import adapter
DiscussionMetadata.publish=lambda *args: os._exit(73)
sys.argv=['adapter']+sys.argv[2:]
adapter.main()
"""
        p = subprocess.run([sys.executable, "-c", code, str(ADAPTER),
                            "join", d, "--name", "lost response", "--seat", "ada"],
                           env=self.env, capture_output=True, timeout=12)
        self.assertEqual(p.returncode, 73, p.stderr)
        self.assertEqual(self.store.meta_path(d).read_bytes(), previous)
        rows = self.call("sessions", d)
        self.assertTrue(any(x["seat"] == "ada" for x in rows))
        self.assertEqual(self.store.state(d), policy.reconstruct(self.store.read(d)))
        self.store.meta_path(d).write_text("corrupt")
        self.assertEqual(self.store.state(d)["last_seq"], 2)
        self.store.meta_path(d).unlink()
        self.assertEqual(self.store.state(d)["last_seq"], 2)

    def test_lock_timeout_cursor_and_metadata_hot_path(self):
        r = self.create("quick", "ada,feynman")
        d = r["discussion"]
        with open(self.store.path(d).with_suffix(".lock"), "r+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            v = self.call("wait", d, "--after", 1, "--timeout", "0.1")
            self.assertTrue(v["lock_busy"])
            self.assertEqual(v["cursor"], 1)
        with patch("core.metadata.decode", side_effect=AssertionError("unexpected replay")):
            self.assertEqual(self.store.state(d)["phase"], "lobby")
        self.join(r, "ada")
        self.assertEqual(self.call("wait", d, "--after", 1, "--timeout", 0)["cursor"], 2)

    def test_pinned_resources_and_private_session_recovery(self):
        r = self.create("quick", "ada,feynman")
        d = r["discussion"]
        a = self.join(r, "ada")
        b = self.join(r, "feynman")
        self.join(r, "chairman")
        self.act(r, r, "advance")
        self.act(r, a, "commit", "--content", "As Ada Lovelace, first draft")
        self.act(r, b, "commit", "--content", "other")
        self.act(r, r, "advance")
        # New CLI processes recover both identity and private draft.
        self.act(r, a, "reveal")
        self.act(r, b, "reveal")
        self.act(r, r, "advance")
        # Source files are not consulted when resuming an existing room.
        from core.sessions import SessionStore
        session = SessionStore(self.root, root=self.root / ".sessions")
        from adapter import view
        with patch("resources.source", side_effect=AssertionError("source changed")):
            v = view(self.store.read(d), a["actor"], session, d)
            self.assertEqual(v["policy_hash"], r["policy_hash"])
            self.assertIn("Formal systems", v["persona"])
            self.assertNotIn("As Ada Lovelace", json.dumps(v["transcript"]))
        self.assertNotIn("token", json.dumps(self.call("sessions", d)))


if __name__ == "__main__":
    unittest.main()
