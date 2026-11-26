#!/usr/bin/env python3
"""Opt-in Council transport for independently running local Agent sessions."""
import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import uuid
from pathlib import Path

import policy
import resources
from core.metadata import DiscussionStore, checksum
from core.sessions import SessionStore
from core.storage import LockTimeout, ProtocolError, require

VERSION = "1.0.0"
MAX_CONTENT = 256 * 1024


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def identity(name, seat):
    require(name.strip() and len(name) <= 100, "invalid session name")
    actor, token = uuid.uuid4().hex, secrets.token_hex(32)
    return actor, token, {"name": name, "seat": seat, "token_hash": token_hash(token)}


def authenticate(state, actor, session, discussion):
    member = state["members"].get(actor)
    token = session.token(discussion, actor) if member else None
    require(member and member["active"] and token and
            hmac.compare_digest(member["token_hash"], token_hash(token)),
            "unknown or unavailable local identity")
    return member


def status(state, discussion):
    return {"discussion": discussion, **{k: state[k] for k in
            ("title", "topic", "mode", "panel", "expert", "phase", "policy_hash",
             "last_seq", "updated_at", "fallback", "result", "verdict_seq",
             "enforcement_checks")},
            "members": [{k: m[k] for k in ("seat", "name", "active")}
                        for m in state["members"].values()],
            "pending": policy.pending_seats(state)}


def read_content(content):
    if content == "-":
        content = sys.stdin.read()
    require(content is not None and content.strip() and
            len(content.encode("utf-8")) <= MAX_CONTENT, "content must be non-empty and <=256 KiB")
    return content


def view(records, actor, sessions, discussion):
    state = policy.reconstruct(records)
    member = authenticate(state, actor, sessions, discussion)
    phase, mode, seat = state["phase"], state["mode"], member["seat"]
    config = records[0]["data"]
    resource = config["resources"]
    require(checksum(resource) == state["policy_hash"], "pinned policy checksum mismatch")
    chair, host = seat == "chairman", seat == "coordinator"
    result = status(state, discussion)
    result.update({"self": {"actor": actor, "seat": seat, "name": member["name"]},
                   "persona": resource["personas"].get(seat),
                   "reference": resources.rules_for(resource, mode, phase, host),
                   "eligible": seat in policy.pending_seats(state)})
    if phase == "debate" and mode == "full" and len(state["panel"]) <= 4:
        result["eligible"] = bool(result["eligible"] and
                                  seat == policy.pending_seats(state)[0])
    if seat in state["followups"] and phase == "enforce":
        result["followup"] = state["followups"][seat]
    # Participants never receive peer analysis before the reveal barrier.
    # During anonymous phases the adapter returns only stable randomized labels,
    # not author IDs. The raw file is an audit log, not an access-control boundary.
    permitted = set()
    if phase in ("commit", "reveal"):
        permitted.add("restate")
    elif phase == "debate":
        permitted.update(("restate", "reveal"))
        if mode == "full" and len(state["panel"]) <= 4:
            permitted.add("debate")
    elif phase == "enforce":
        permitted.update(("restate", "reveal", "debate", "enforce"))
    elif phase == "position":
        permitted.update(("restate", "reveal", "debate", "enforce"))
    elif phase in ("synthesis", "closed", "aborted"):
        permitted.update(("restate", "reveal", "debate", "enforce", "position", "synthesis"))
    if host:
        permitted.update(("restate", "reveal", "debate", "enforce", "position", "synthesis"))
    if chair and phase not in ("synthesis", "closed", "aborted"):
        permitted.clear()
    anonymous = not (host or chair) and (
        (mode == "full" and phase in ("debate", "enforce")) or
        (mode == "quick" and phase == "position"))
    transcript = []
    for record in records:
        if record["type"] != "submission":
            continue
        data = record["data"]
        if data["phase"] not in permitted:
            continue
        author = state["members"][record["actor"]]["seat"]
        content = data["content"]
        label = author
        if anonymous and author in config["labels"]:
            label = config["labels"][author]
            content = resources.anonymize(content, author, resource["personas"][author], label)
        item = {"seq": record["seq"], "phase": data["phase"], "member": label,
                "content": content}
        if not anonymous and "stance" in data:
            item.update({k: data[k] for k in ("stance", "confidence", "dealbreaker")})
        transcript.append(item)
    result["transcript"] = transcript
    if state["phase"] == "closed":
        closed = records[-1]["data"]
        if "fallback_verdict" in closed:
            result["verdict"] = closed["fallback_verdict"]
        else:
            result["verdict"] = records[state["verdict_seq"] - 1]["data"]["content"]
    if state["phase"] == "aborted":
        result["abort_reason"] = records[-1]["data"]["reason"]
    return result


def run(args):
    root = Path(os.environ.get("COUNCIL_LADP_HOME", str(Path.home() / ".ladp" /
                                                        "council" / "discussions"))).expanduser()
    store = DiscussionStore(root, policy)
    sessions = SessionStore(root, root=root / ".sessions")
    command = args.command
    if command == "roster":
        return resources.roster()
    if command == "create":
        seats = [s.strip() for s in args.members.split(",")] if args.members else resources.roster()
        require(2 <= len(seats) <= len(resources.roster()), "select at least two distinct members")
        require(args.mode != "duo" or len(seats) == 2, "duo requires exactly two seats")
        require(not args.expert or args.expert in seats, "expert must be a panel seat")
        require(args.mode != "duo" or not args.expert, "duo has no weighted seat")
        require(args.title.strip() and args.topic.strip(), "title and topic required")
        resource = resources.pin(seats)
        labels = ["Member " + chr(ord("A") + i) for i in range(len(seats))]
        secrets.SystemRandom().shuffle(labels)
        discussion = uuid.uuid4().hex
        actor, token, member = identity(args.name, "coordinator")
        sessions.save_identity(discussion, actor, token)
        store.create(discussion, actor, {"policy_version": policy.VERSION,
            "title": args.title, "topic": args.topic, "mode": args.mode, "panel": seats,
            "expert": args.expert, "policy_hash": checksum(resource), "resources": resource,
            "labels": dict(zip(seats, labels)), "member": member})
        return {"discussion": discussion, "actor": actor, "seat": "coordinator",
                "phase": "lobby", "policy_hash": checksum(resource)}
    if command in ("list", "sessions"):
        rows = []
        for d in ([args.discussion] if command == "sessions" and args.discussion else store.ids()):
            state = store.state(d)
            if command == "list":
                if args.all or state["phase"] not in policy.TERMINAL:
                    rows.append(status(state, d))
            else:
                for actor in sessions.actors(d):
                    member = state["members"].get(actor)
                    token = sessions.token(d, actor)
                    if member and token and hmac.compare_digest(member["token_hash"], token_hash(token)):
                        rows.append({"discussion": d, "actor": actor, "seat": member["seat"],
                                     "name": member["name"], "phase": state["phase"]})
        return rows

    discussion = args.discussion
    if command == "status":
        return status(store.state(discussion), discussion)
    if command == "view":
        return view(store.read(discussion), args.actor, sessions, discussion)
    if command == "wait":
        require(0 <= args.timeout <= 60 and args.after >= 0, "invalid timeout or cursor")
        reader = store.reader(discussion)
        deadline, interval = time.monotonic() + args.timeout, 0.25
        state = None
        while True:
            try:
                changed = reader.refresh(deadline)
            except LockTimeout:
                return {"cursor": args.after, "timed_out": True, "lock_busy": True}
            if changed or state is None:
                state = policy.reconstruct(reader.records)
            require(args.after <= state["last_seq"], "cursor exceeds history")
            if state["last_seq"] > args.after or state["phase"] in policy.TERMINAL:
                return {"cursor": state["last_seq"], "timed_out": False,
                        "phase": state["phase"], "pending": policy.pending_seats(state)}
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"cursor": args.after, "timed_out": True, "phase": state["phase"]}
            time.sleep(min(interval, remaining))
            interval = min(1, interval * 1.5)
    if command == "join":
        actor, token, member = identity(args.name, args.seat)
        def join(state):
            require(state["phase"] == "lobby", "enrollment closed; resume existing identity")
            require(args.seat in state["panel"] or args.seat == "chairman", "seat is not selected")
            require(args.seat not in policy.occupied(state), "seat is occupied")
            require(all(m["name"] != args.name for m in state["members"].values()),
                    "session name is already in use")
            sessions.save_identity(discussion, actor, token)
            return "joined", actor, {"member": member}
        store.append(discussion, join)
        return {"discussion": discussion, "actor": actor, "seat": args.seat}
    content = read_content(args.content) if getattr(args, "content", None) is not None else None

    def mutate(state):
        actor = args.actor
        member = authenticate(state, actor, sessions, discussion)
        require(state["phase"] not in policy.TERMINAL, "discussion ended")
        phase = state["phase"]
        if command in ("advance", "close", "abort"):
            require(member["seat"] == "coordinator", "coordinator operation")
            if command == "advance":
                return "phase", actor, policy.advance(state, args)
            if command == "abort":
                return "aborted", actor, {"reason": content}
            require(phase == "synthesis", "finish deliberation before closing")
            if state["verdict_seq"] is not None:
                require(not content and not args.fallback_reason, "cannot replace chairman verdict")
                return "closed", actor, {"verdict_seq": state["verdict_seq"]}
            reason = args.fallback_reason or state["fallback"]
            require(reason and reason.strip() and content, "chairman pending; explicit fallback required")
            return "closed", actor, {"fallback": reason, "fallback_verdict": content}
        seat = policy.can_submit(state, actor)
        if command == "commit":
            require(phase == "commit", "not in blind analysis")
            nonce = secrets.token_hex(32)
            sessions.save_commitment(discussion, actor, content, nonce)
            return "commit", actor, {"digest": policy.digest(content, nonce)}
        if command == "reveal":
            require(phase == "reveal", "not in reveal phase")
            saved = sessions.commitment(discussion, actor)
            require(saved and policy.digest(saved["content"], saved["nonce"]) ==
                    state["commits"].get(actor), "missing or inconsistent private commitment")
            return "submission", actor, {"phase": phase, "content": saved["content"],
                                          "nonce": saved["nonce"]}
        require(command == "submit" and phase not in ("commit", "reveal"),
                "use commit/reveal for independent analysis")
        data = {"phase": phase, "content": content}
        if phase == "position" and state["mode"] != "duo":
            require(args.stance and policy.normalize(args.stance) and
                    len(args.stance) <= 200 and args.confidence and args.dealbreaker,
                    "position requires --stance, --confidence and --dealbreaker")
            data.update(stance=args.stance, confidence=args.confidence, dealbreaker=args.dealbreaker)
        else:
            require(not (args.stance or args.confidence or args.dealbreaker),
                    "structured votes only in full/quick final positions")
        return "submission", actor, data

    record = store.append(discussion, mutate)
    return {"discussion": discussion, "seq": record["seq"], "type": record["type"]}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", action="version", version="Council LADP " + VERSION)
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("roster")
    create = commands.add_parser("create")
    create.add_argument("--title", required=True)
    create.add_argument("--topic", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--mode", choices=policy.PHASES, default="full")
    create.add_argument("--members", help="comma-separated upstream persona slugs; omit for all")
    create.add_argument("--expert", help="domain-weight seat, fixed before analysis")
    commands.add_parser("list").add_argument("--all", action="store_true")
    commands.add_parser("sessions").add_argument("discussion", nargs="?")
    for action in ("join", "status", "view", "wait", "advance", "commit",
                   "reveal", "submit", "close", "abort"):
        c = commands.add_parser(action)
        c.add_argument("discussion")
        if action == "join":
            c.add_argument("--name", required=True)
            c.add_argument("--seat", required=True)
        if action not in ("join", "status", "wait"):
            c.add_argument("--actor", required=True)
        if action == "wait":
            c.add_argument("--after", type=int, required=True)
            c.add_argument("--timeout", type=float, default=20)
        if action in ("submit", "commit", "abort", "close"):
            c.add_argument("--content", required=action != "close")
        if action in ("advance", "close"):
            c.add_argument("--fallback-reason")
        if action == "advance":
            c.add_argument("--enforcement", help="summary of all full-mode enforcement checks")
            c.add_argument("--followup", action="append", help="seat=targeted enforcement instruction")
            c.add_argument("--alias", action="append", help="submitted label=canonical label")
        if action == "submit":
            c.add_argument("--stance")
            c.add_argument("--confidence", choices=policy.CONFIDENCE)
            c.add_argument("--dealbreaker", choices=("yes", "no"))
    return p


def main():
    try:
        result = run(parser().parse_args())
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except (ProtocolError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
