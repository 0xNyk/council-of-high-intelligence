"""Executable transport tests. No model/provider processes or network calls."""
import concurrent.futures
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

ADAPTER = Path(__file__).resolve().parents[1]
CLI = ADAPTER / "adapter.py"
sys.path.insert(0, str(ADAPTER))
import policy
import resources
from ladp_core.metadata import DiscussionStore, DiscussionMetadata


class AdapterTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="council-ladp-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.env = dict(os.environ, COUNCIL_LADP_HOME=str(self.root),
                        PYTHONDONTWRITEBYTECODE="1")
        self.store = DiscussionStore(self.root, policy)

    def raw(self, *args, cli=CLI):
        args = list(args)
        if args[0] in ("create", "join", "advance", "submit", "commit", "reveal", "close", "abort", "leave", "remove"):
            if "--request-id" not in args:
                args += ["--request-id", uuid.uuid4().hex]
            if args[0] not in ("create", "join") and "--expect-phase" not in args:
                phase = self.store.state(args[1])["phase"]
                args += ["--expect-phase", phase]
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
            self.act(room, chair, "submit", "--decision", view["decision_key"], "--content", "Independent verdict")
            self.act(room, room, "close", "--content", "replacement", ok=False)
            self.act(room, room, "close")
            self.assertEqual(self.view(room, room)["publication"]["analysis_report"], "Independent verdict")
        else:
            self.act(room, room, "close", "--decision", self.status(room)["decision_key"], "--content", "Explicit fallback verdict")
            self.assertEqual(self.view(room, room)["publication"]["analysis_report"], "Explicit fallback verdict")
        self.assertEqual(self.status(room)["phase"], "closed")

    def test_full_mode_restate_sequential_named_and_enforcement(self):
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
        self.assertEqual(bv["peer_view"], "named")
        self.assertEqual({x["member"] for x in bv["transcript"]}, {"ada", "feynman", "torvalds"})
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

    def test_two_seat_quick_mode_named_and_keeps_split(self):
        room, members, chair = self.panel("quick", ["ada", "feynman"])
        self.assertEqual(self.status(room)["phase"], "commit")
        self.commit_reveal(room, members)
        self.assertEqual(self.status(room)["phase"], "position")
        v = self.view(room, members[0])
        self.assertEqual(len(v["transcript"]), 2)
        self.assertEqual(v["peer_view"], "named")
        self.assertEqual({x["member"] for x in v["transcript"]}, {"ada", "feynman"})
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
from ladp_core.metadata import DiscussionMetadata
import adapter
DiscussionMetadata.publish=lambda *args: os._exit(73)
sys.argv=['adapter']+sys.argv[2:]
adapter.main()
"""
        request_id = uuid.uuid4().hex
        p = subprocess.run([sys.executable, "-c", code, str(ADAPTER),
                            "join", d, "--name", "lost response", "--seat", "ada", "--request-id", request_id],
                           env=self.env, capture_output=True, timeout=12)
        self.assertEqual(p.returncode, 73, p.stderr)
        self.assertEqual(self.store.meta_path(d).read_bytes(), previous)
        replay = self.call("join", d, "--name", "lost response", "--seat", "ada",
                           "--request-id", request_id)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["seq"], 2)
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
        with patch("ladp_core.metadata.decode", side_effect=AssertionError("unexpected replay")):
            self.assertEqual(self.store.state(d)["phase"], "lobby")
        self.join(r, "ada")
        self.assertEqual(self.call("wait", d, "--after", 1, "--timeout", 0)["cursor"], 2)

    def test_anonymous_view_has_no_prior_named_restatements_or_log_order(self):
        room, members, chair = self.panel("full", ["ada", "feynman", "torvalds",
                                                   "socrates", "taleb"])
        for m in members:
            self.act(room, m, "submit", "--content", "Unique framing " + m["seat"])
        self.act(room, room, "advance")
        before = self.view(room, members[0])
        self.assertEqual({x["member"] for x in before["transcript"]},
                         set(m["seat"] for m in members))
        self.commit_reveal(room, members)
        after = self.view(room, members[0])
        self.assertEqual(after["peer_view"], "pseudonymous")
        self.assertNotIn("pending", after)
        self.assertNotIn("pending", self.status(room))
        self.assertNotIn("enforcement_checks", after)
        self.assertEqual({x["phase"] for x in after["transcript"]}, {"reveal"})
        self.assertTrue(all("seq" not in x for x in after["transcript"]))
        labels = [x["member"] for x in after["transcript"]]
        self.assertEqual(labels, sorted(labels))
        self.assertEqual(len(set(labels)), len(members))

    def test_stale_phase_retry_cannot_become_final_position(self):
        room, members, chair = self.panel("duo", ["ada", "feynman"])
        a, b = members
        self.commit_reveal(room, members)
        request_id = uuid.uuid4().hex
        args = ("--expect-phase", "debate", "--request-id", request_id,
                "--content", "Original challenge")
        original = self.act(room, a, "submit", *args)
        self.act(room, b, "submit", "--content", "Peer challenge")
        self.act(room, room, "advance")
        before = self.status(room)["last_seq"]
        retry = self.act(room, a, "submit", *args)
        self.assertTrue(retry["replayed"])
        self.assertEqual(retry["seq"], original["seq"])
        self.assertEqual(self.status(room)["last_seq"], before)
        error = self.act(room, a, "submit", "--expect-phase", "debate",
                         "--content", "old payload", ok=False)
        self.assertIn("stale phase", error)
        self.act(room, a, "submit", "--expect-phase", "position",
                 "--request-id", request_id, "--content", "changed payload", ok=False)
        self.assertEqual(self.status(room)["pending"], ["ada", "feynman"])
        self.act(room, a, "submit", "--content", "Final statement")

    def test_concurrent_exact_request_replays_once(self):
        room, members, chair = self.panel("quick", ["ada", "feynman"])
        a = members[0]
        request = uuid.uuid4().hex
        args = ("commit", room["discussion"], "--actor", a["actor"],
                "--request-id", request, "--expect-phase", "commit", "--content", "analysis")
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: self.call(*args), range(6)))
        self.assertEqual(len({x["seq"] for x in results}), 1)
        self.assertEqual(sum(not x["replayed"] for x in results), 1)
        self.assertEqual(self.status(room)["pending"], ["feynman"])
        self.store.meta_path(room["discussion"]).unlink()
        self.assertTrue(self.call(*args)["replayed"])

    def test_concurrent_create_exact_retry_has_one_room(self):
        req = uuid.uuid4().hex
        args = ("create", "--request-id", req, "--name", "host", "--title", "test",
                "--topic", "question", "--mode", "quick", "--members", "ada,feynman")
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            values = list(pool.map(lambda _: self.call(*args), range(4)))
        self.assertEqual(len({x["actor"] for x in values}), 1)
        self.assertEqual({x["discussion"] for x in values}, {req})
        self.assertEqual(sum(not x["replayed"] for x in values), 1)
        self.assertEqual(len(self.store.ids()), 1)
        self.assertEqual(len(self.call("sessions", req)), 1)
        self.call(*args[:-1], "ada,torvalds", ok=False)

    def test_join_response_loss_recovers_original_seat(self):
        room = self.create("quick", "ada,feynman")
        args = ("join", room["discussion"], "--seat", "ada",
                "--name", "my-session", "--request-id", uuid.uuid4().hex)
        first = self.call(*args)
        second = self.call(*args)
        self.assertEqual(first["actor"], second["actor"])
        self.assertTrue(second["replayed"])
        self.assertEqual(self.status(room)["last_seq"], 2)

    def test_authoritative_result_cannot_be_replaced_by_chairman(self):
        room, members, chair = self.panel("quick", ["ada", "feynman"])
        self.commit_reveal(room, members)
        for m in members:
            self.vote(room, m, "A")
        self.act(room, room, "advance")
        self.act(room, chair, "submit", "--decision", "consensus:b",
                 "--content", "wrong outcome", ok=False)
        self.act(room, room, "close", "--decision", "consensus:b",
                 "--fallback-reason", "missing chair", "--content", "wrong outcome", ok=False)
        self.act(room, chair, "submit", "--decision", "consensus:a",
                 "--content", "This free-text report incorrectly claims B.")
        self.act(room, room, "close")
        publication = self.view(room, room)["publication"]
        self.assertEqual(publication["decision_key"], "consensus:a")
        self.assertEqual(publication["decision"]["consensus"], "a")
        self.assertIn("claims B", publication["analysis_report"])
        self.assertNotIn("verdict", self.view(room, room))

    def test_member_dropout_freezes_original_vote_denominator(self):
        room, members, chair = self.panel("quick", ["ada", "feynman", "torvalds"], "ada")
        a, b, c = members
        self.act(room, a, "commit", "--content", "will disappear")
        self.act(room, b, "commit", "--content", "B")
        self.act(room, c, "commit", "--content", "C")
        self.act(room, room, "advance")
        self.act(room, room, "remove", "--target", a["actor"], "--content", "confirmed offline")
        self.act(room, a, "reveal", ok=False)
        for m in (b, c):
            self.act(room, m, "reveal")
        self.act(room, room, "advance")
        self.assertEqual(self.view(room, b)["peer_view"], "named")
        for m in (b, c):
            self.vote(room, m, "A")
        self.act(room, room, "advance")
        result = self.status(room)["result"]
        self.assertEqual(result["total_units"], 56)
        self.assertEqual(result["scores"]["a"], 32)
        self.assertIsNone(result["consensus"])
        self.assertEqual(result["withdrawals"], {"ada": "confirmed offline"})
        self.finish(room, chair)

    def test_lobby_replacement_and_minimum_active_members(self):
        room = self.create("duo", "ada,feynman")
        a = self.join(room, "ada")
        self.act(room, a, "leave", "--content", "switch session")
        replacement = self.join(room, "ada")
        self.assertNotEqual(replacement["actor"], a["actor"])
        # An old removal target must not remove a replacement in the same lobby.
        self.act(room, room, "remove", "--target", a["actor"], "--content", "stale target", ok=False)
        self.assertTrue(any(x["actor"] == replacement["actor"] and x["active"]
                            for x in self.view(room, room)["members"]))
        b = self.join(room, "feynman")
        self.join(room, "chairman")
        self.act(room, room, "advance")
        self.act(room, b, "leave", "--content", "disconnect")
        self.act(room, replacement, "commit", "--content", "A")
        self.assertIn("fewer than two", self.act(room, room, "advance", ok=False))
        self.act(room, room, "abort", "--content", "not enough members")

    def test_corrupt_room_does_not_break_other_room_discovery(self):
        good = self.create("quick", "ada,feynman")
        bad = self.create("quick", "ada,feynman")
        with self.store.path(bad["discussion"]).open("ab") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(b"invalid\n")
        for result in (self.call("list", "--all"), self.call("sessions")):
            self.assertTrue(any(x["discussion"] == good["discussion"] and "error" not in x for x in result))
            self.assertTrue(any(x["discussion"] == bad["discussion"] and "error" in x for x in result))

    def test_skill_directory_copy_is_self_contained(self):
        source = ADAPTER.parents[1]
        copied = self.root / "portable" / "skills" / "council"
        shutil.copytree(source, copied, symlinks=False)
        cli = copied / "adapters" / "ladp" / "adapter.py"
        self.assertEqual(self.call("roster", cli=cli), resources.roster())
        r = self.call("create", "--name", "host", "--title", "Portable", "--topic", "test",
                      "--mode", "quick", "--members", "ada,feynman", cli=cli)
        self.assertEqual(self.status(r)["phase"], "lobby")

    def test_exported_four_hosts_share_one_room(self):
        repo = ADAPTER.parents[3]
        paths = []
        for host in ("claude", "codex", "gemini", "opencode"):
            dest = self.root / "exports" / host
            proc = subprocess.run([sys.executable, str(repo / "scripts/export-council-skill.py"),
                                   "--output", str(dest), "--host", host],
                                  env=self.env, capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(any(p.is_symlink() for p in dest.rglob("*")))
            self.assertFalse((dest / "adapters/ladp/tests").exists())
            self.assertFalse((dest / "configs/provider-model-slots.local.yaml").exists())
            paths.append(dest / "adapters/ladp/adapter.py")
        room = self.call("create", "--name", "host", "--title", "exported",
                         "--topic", "test", "--mode", "quick", "--members", "ada,feynman",
                         cli=paths[0])
        d = room["discussion"]
        a = self.call("join", d, "--seat", "ada", "--name", "a", cli=paths[1])
        b = self.call("join", d, "--seat", "feynman", "--name", "b", cli=paths[2])
        chair = self.call("join", d, "--seat", "chairman", "--name", "chair", cli=paths[3])
        def act(i, who, command, *args):
            return self.call(command, d, "--actor", who["actor"], *args, cli=paths[i])
        act(0, room, "advance")
        for i, m in ((1, a), (2, b)):
            act(i, m, "commit", "--content", "proposal")
        act(0, room, "advance")
        for i, m in ((1, a), (2, b)):
            act(i, m, "reveal")
        act(0, room, "advance")
        for i, m in ((1, a), (2, b)):
            act(i, m, "submit", "--stance", "A", "--confidence", "high",
                "--dealbreaker", "no", "--content", "position")
        act(0, room, "advance")
        act(3, chair, "submit", "--decision", "consensus:a", "--content", "analysis")
        act(0, room, "close")
        self.assertEqual(act(1, a, "view")["publication"]["decision_key"], "consensus:a")

    def test_full_roster_concurrent_discussion(self):
        seats = resources.roster()
        room = self.create("full", ",".join(seats))
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(seats)) as pool:
            members = list(pool.map(lambda seat: self.join(room, seat), seats))
        chair = self.join(room, "chairman")
        self.act(room, room, "advance")
        def stage(phase, command, *args):
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(seats)) as pool:
                outcomes = list(pool.map(lambda m: self.act(room, m, command,
                      "--expect-phase", phase, *args), members))
            self.assertEqual(len({x["seq"] for x in outcomes}), len(seats))
        stage("restate", "submit", "--content", "frame")
        self.act(room, room, "advance")
        stage("commit", "commit", "--content", "analysis")
        self.act(room, room, "advance")
        stage("reveal", "reveal")
        self.act(room, room, "advance")
        stage("debate", "submit", "--content", "cross examination")
        self.act(room, room, "advance", "--enforcement", "no extra follow-up")
        stage("position", "submit", "--stance", "A", "--confidence", "high",
              "--dealbreaker", "no", "--content", "final")
        self.act(room, room, "advance")
        result = self.status(room)["result"]
        self.assertEqual(result["total_units"], 16 * len(seats))
        self.assertEqual(result["scores"]["a"], result["total_units"])
        self.finish(room, chair)
        records = self.store.read(room["discussion"])
        self.assertEqual([r["seq"] for r in records], list(range(1, len(records)+1)))

    def test_concurrent_stale_phase_advances_only_once(self):
        room = self.create("quick", "ada,feynman")
        for seat in ("ada", "feynman", "chairman"):
            self.join(room, seat)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            values = list(pool.map(lambda _: self.raw("advance", room["discussion"],
                "--actor", room["actor"], "--expect-phase", "lobby"), range(8)))
        self.assertEqual(sum(p.returncode == 0 for p in values), 1)
        self.assertEqual(self.status(room)["phase"], "commit")

    def test_upstream_contract_drift_fails_closed(self):
        source = self.root / "modified-upstream"
        shutil.copytree(resources.source(), source, symlinks=False,
                        ignore=shutil.ignore_patterns(".git", "skills", "__pycache__"))
        path = source / "SKILL.md"
        raw = path.read_text()
        changed = raw.replace("W_option ≥ (2/3) × W_total", "W_option ≥ (1/2) × W_total")
        self.assertNotEqual(raw, changed)
        path.write_text(changed)
        from ladp_core.storage import ProtocolError
        with patch("resources.source", return_value=source):
            with self.assertRaisesRegex(ProtocolError, "upstream Council protocol changed"):
                resources.pin(["ada", "feynman"])

    def test_incompatible_executable_policy_does_not_mutate_history(self):
        room = self.create("quick", "ada,feynman")
        d = room["discussion"]
        original = self.store.path(d).read_bytes()
        from ladp_core.storage import ProtocolError
        with patch("policy.implementation_hash", return_value="different-version"):
            with self.assertRaisesRegex(ProtocolError, "incompatible Council policy"):
                self.store.state(d)
        self.assertEqual(self.store.path(d).read_bytes(), original)
        self.assertEqual(self.status(room)["phase"], "lobby")

    def test_pinned_resources_and_private_session_recovery(self):
        r = self.create("quick", "ada,feynman,torvalds")
        d = r["discussion"]
        a = self.join(r, "ada")
        b = self.join(r, "feynman")
        c = self.join(r, "torvalds")
        self.join(r, "chairman")
        self.act(r, r, "advance")
        self.act(r, a, "commit", "--content", "As Ada Lovelace, first draft")
        self.act(r, b, "commit", "--content", "other")
        self.act(r, c, "commit", "--content", "third")
        self.act(r, r, "advance")
        # New CLI processes recover both identity and private draft.
        self.act(r, a, "reveal")
        self.act(r, b, "reveal")
        self.act(r, c, "reveal")
        self.act(r, r, "advance")
        # Source files are not consulted when resuming an existing room.
        from ladp_core.sessions import SessionStore
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
