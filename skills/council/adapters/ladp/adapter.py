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

# Resolve the adjacent in-tree Core package, independent of caller cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "core"))
import policy
import resources
import protocol
from ladp_core import API_VERSION
from ladp_core.metadata import CommittedRequest, DiscussionStore, checksum
from ladp_core.sessions import SessionStore
from ladp_core.storage import ID_RE, LockTimeout, ProtocolError, require

VERSION = "1.2.0"
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


def pseudonymous_phase(state):
    if len(policy.active_panel(state)) < 3:
        return False
    return policy.anonymous_stage(state) and not (
        state["phase"] in ("debate", "enforce") and policy.sequential_debate(state))



def status(state, discussion, public=True):
    result = {"discussion": discussion, **{k: state[k] for k in
            ("title", "topic", "mode", "panel", "expert", "phase", "policy_hash",
             "last_seq", "updated_at", "fallback", "result", "verdict_seq",
             "enforcement_checks", "withdrawals", "protocol_hash")},
            "members": [{k: m[k] for k in ("seat", "name", "active")}
                        for m in state["members"].values()],
            "pending": policy.pending_seats(state),
            "chairman_joined": "chairman" in policy.occupied(state),
            "decision_key": decision_key(state["result"])}
    if public and pseudonymous_phase(state):
        result["pending_count"] = len(result.pop("pending"))
        result.pop("enforcement_checks", None)
        result.pop("withdrawals", None)
    return result


def decision_key(result):
    if result is None:
        return None
    if result["kind"] == "dialectic":
        return "dialectic"
    return ("consensus:" + result["consensus"] if result["consensus"] is not None
            else "no-consensus")


def request_hash(args, content=None):
    fields = {k: v for k, v in vars(args).items() if k not in ("request_id", "content")}
    return checksum({"arguments": fields, "content": content})


def receipt(state, args, fingerprint, actor=None):
    prior = state["requests"].get(args.request_id)
    if prior is None:
        return None
    require(prior["hash"] == fingerprint and (actor is None or prior["actor"] == actor),
            "request ID already used for a different operation")
    return CommittedRequest({"seq": prior["seq"], "type": prior["type"],
                             "actor": prior["actor"]})


def with_request(mutation, args, fingerprint):
    kind, actor, data = mutation
    return kind, actor, dict(data, _request={"id": args.request_id, "hash": fingerprint})


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
    sequential = policy.sequential_debate(state)
    anonymous = not (host or chair) and pseudonymous_phase(state)
    named_peer_phase = not pseudonymous_phase(state) and (
        (mode == "full" and phase in ("debate", "enforce"))
        or (mode == "quick" and phase == "position"))
    result = status(state, discussion, public=False)
    reference = resources.rules_for(resource, mode, phase, host)
    if named_peer_phase:
        reference = ("LOCAL TRANSPORT OVERRIDE: this peer view is NAMED under the configured rule or local anonymity limitations. "
                     "Use seat names, not Member labels; ignore the upstream anonymity instructions. "
                     "All other analytical and anti-conformity rules remain in force.\n\n" + reference)
    if phase == "synthesis":
        reference = ("LOCAL TRANSPORT OVERRIDE: report the authoritative decision_key and result separately; "
                     "submit the same decision_key using --decision. The report is non-authoritative analysis. "
                     "Do not replace the computed outcome or votes.\n\n" + reference)
    result["protocol"] = state["protocol"]
    result["business_stage"] = protocol.business_stage(phase)
    result["transport_phases"] = policy.phases(state)
    if reference:
        reference = ("Use the pinned protocol object in this view as the authoritative rules. "
                     "Resolve word limits and enforcement counts from that object; do not read a newer local configuration. "
                     "Canonical rules apply, not native host overrides.\n\n" + reference)
    result.update({"self": {"actor": actor, "seat": seat, "name": member["name"]},
                   "persona": resource["personas"].get(seat), "reference": reference,
                   "eligible": seat in policy.pending_seats(state),
                   "peer_view": "pseudonymous" if anonymous else "named"})
    if host:
        result["members"] = [dict(actor=mid, seat=m["seat"], name=m["name"], active=m["active"])
                             for mid, m in state["members"].items()]
    if sequential and phase == "debate":
        pending = policy.pending_seats(state)
        result["eligible"] = bool(result["eligible"] and seat == pending[0])
    if seat in state["followups"] and phase == "enforce":
        result["followup"] = state["followups"][seat]
    permitted = set()
    if phase in ("commit", "reveal"):
        permitted.add("restate")
    elif phase == "debate":
        permitted.update(("restate", "reveal"))
        if sequential:
            permitted.add("debate")
    elif phase == "enforce":
        permitted.update(("restate", "reveal", "debate"))
        if sequential:
            permitted.add("enforce")
    elif phase == "position":
        permitted.update(("restate", "reveal", "debate", "enforce"))
    elif phase in ("synthesis", "closed", "aborted"):
        permitted.update(("restate", "reveal", "debate", "enforce", "position", "synthesis"))
    if host:
        permitted.update(("restate", "reveal", "debate", "enforce", "position", "synthesis"))
    if chair and phase not in ("synthesis", "closed", "aborted"):
        permitted.clear()
    if anonymous:
        # Restatements were previously named. Re-publishing them with labels,
        # log sequence numbers or arrival order would reveal the mapping.
        permitted.discard("restate")
        result["pending_count"] = len(result.pop("pending"))
        result.pop("enforcement_checks", None)
        result.pop("withdrawals", None)
    transcript = []
    for record in records:
        if record["type"] != "submission":
            continue
        data = record["data"]
        if data["phase"] not in permitted:
            continue
        author = state["members"][record["actor"]]["seat"]
        content, label = data["content"], author
        if anonymous and author in config["labels"]:
            label = config["labels"][author]
            content = resources.anonymize(content, author, resource["personas"][author], label)
        item = {"phase": data["phase"], "member": label, "content": content}
        if not anonymous:
            item["seq"] = record["seq"]
            if "stance" in data:
                item.update({k: data[k] for k in ("stance", "confidence", "dealbreaker")})
        transcript.append(item)
    if anonymous:
        transcript.sort(key=lambda item: (item["phase"], item["member"]))
    result["transcript"] = transcript
    if state["phase"] == "closed":
        closed = records[-1]["data"]
        if "fallback_verdict" in closed:
            report = closed["fallback_verdict"]
        else:
            report = records[state["verdict_seq"] - 1]["data"]["content"]
        # Never return the LLM prose as the authoritative decision.
        result["publication"] = {
            "decision": state["result"], "decision_key": decision_key(state["result"]),
            "analysis_report": report, "synthesizer": "coordinator" if state["fallback"] else "chairman",
            "fallback_reason": state["fallback"]}
    if state["phase"] == "aborted":
        result["abort_reason"] = records[-1]["data"]["reason"]
    return result


def run(args):
    require(API_VERSION == 1, "incompatible LADP Core API")
    command = args.command
    if command == "roster":
        return resources.roster()
    if command == "protocol":
        return protocol.load()
    root = Path(os.environ.get("COUNCIL_LADP_HOME", str(Path.home() / ".ladp" /
                                                        "council" / "discussions"))).expanduser()
    store = DiscussionStore(root, policy)
    sessions = SessionStore(root, root=root / ".sessions")
    if command == "create":
        require(ID_RE.fullmatch(args.request_id), "request ID must be 32 lowercase hex characters")
        discussion = args.request_id
        fingerprint = request_hash(args)

        def existing():
            state = store.state(discussion)
            previous = receipt(state, args, fingerprint)
            require(previous is not None and previous.receipt["type"] == "created",
                    "discussion ID already exists")
            actor = previous.receipt["actor"]
            authenticate(state, actor, sessions, discussion)
            return {"discussion": discussion, "actor": actor, "seat": "coordinator",
                    "phase": state["phase"], "policy_hash": state["policy_hash"],
                    "protocol_hash": state["protocol_hash"], "replayed": True}

        if store.path(discussion).exists():
            return existing()
        seats = [s.strip() for s in args.members.split(",")] if args.members else resources.roster()
        config = protocol.load()
        mode_rule = config["modes"][args.mode]
        minimum = config["panel"]["min_active"]
        require(minimum <= len(seats) <= min(len(resources.roster()), 26),
                f"select at least {minimum} distinct members within the available roster (maximum 26 labels)")
        require("panel_size" not in mode_rule or len(seats) == mode_rule["panel_size"],
                "incorrect panel size for mode")
        require(not args.expert or args.expert in seats, "expert must be a panel seat")
        require(mode_rule["voting"] == "weighted" or not args.expert, "dialectic has no weighted seat")
        require(args.title.strip() and args.topic.strip(), "title and topic required")
        resource = resources.pin(seats, policy.VERSION, config)
        labels = ["Member " + chr(ord("A") + i) for i in range(len(seats))]
        secrets.SystemRandom().shuffle(labels)
        actor, token, member = identity(args.name, "coordinator")
        sessions.save_identity(discussion, actor, token)
        try:
            store.create(discussion, actor, {"policy_version": policy.VERSION,
                "implementation_hash": policy.implementation_hash(),
                "title": args.title, "topic": args.topic, "mode": args.mode, "panel": seats,
                "expert": args.expert, "policy_hash": checksum(resource), "resources": resource,
                "labels": dict(zip(seats, labels)), "member": member,
                "_request": {"id": args.request_id, "hash": fingerprint}})
        except FileExistsError:
            # Another exact retry published the room atomically.
            return existing()
        return {"discussion": discussion, "actor": actor, "seat": "coordinator",
                "phase": "lobby", "policy_hash": checksum(resource),
                "protocol_hash": checksum(config), "replayed": False}
    if command in ("list", "sessions"):
        rows = []
        for d in ([args.discussion] if command == "sessions" and args.discussion else store.ids()):
            try:
                state = store.state(d)
                if command == "list":
                    if args.all or state["phase"] not in policy.TERMINAL:
                        rows.append(status(state, d))
                else:
                    for actor in sessions.actors(d):
                        try:
                            member = state["members"].get(actor)
                            token = sessions.token(d, actor)
                            if member and member["active"] and token and hmac.compare_digest(member["token_hash"], token_hash(token)):
                                rows.append({"discussion": d, "actor": actor, "seat": member["seat"],
                                             "name": member["name"], "phase": state["phase"]})
                        except (ProtocolError, OSError, ValueError, KeyError, TypeError) as exc:
                            rows.append({"discussion": d, "actor": actor, "error": str(exc)})
            except (ProtocolError, OSError, ValueError, KeyError, TypeError) as exc:
                rows.append({"discussion": d, "error": str(exc)})
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
                        "phase": state["phase"], "pending_count": len(policy.pending_seats(state))}
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"cursor": args.after, "timed_out": True, "phase": state["phase"]}
            time.sleep(min(interval, remaining))
            interval = min(1, interval * 1.5)
    if command == "join":
        require(ID_RE.fullmatch(args.request_id), "request ID must be 32 lowercase hex characters")
        fingerprint = request_hash(args)
        actor, token, member = identity(args.name, args.seat)
        def join(state):
            previous = receipt(state, args, fingerprint)
            if previous:
                return previous
            require(state["phase"] == "lobby", "enrollment closed; resume existing identity")
            require(args.seat in state["panel"] or args.seat == "chairman", "seat is not selected")
            require(args.seat not in policy.occupied(state), "seat is occupied")
            require(all(m["name"] != args.name or not m["active"] for m in state["members"].values()),
                    "session name is already in use")
            sessions.save_identity(discussion, actor, token)
            return with_request(("joined", actor, {"member": member}), args, fingerprint)
        record = store.append(discussion, join)
        return {"discussion": discussion, "actor": record["actor"], "seat": args.seat,
                "seq": record["seq"], "replayed": record.get("replayed", False)}
    content = read_content(args.content) if getattr(args, "content", None) is not None else None

    require(ID_RE.fullmatch(args.request_id), "request ID must be 32 lowercase hex characters")
    fingerprint = request_hash(args, content)

    def perform(state, member):
        actor = args.actor
        require(state["phase"] not in policy.TERMINAL, "discussion ended")
        phase = state["phase"]
        require(args.expect_phase == phase, "stale phase: expected " + args.expect_phase + ", actual " + phase)
        if command in ("leave", "remove"):
            require(command == "leave" or member["seat"] == "coordinator", "coordinator operation")
            target = actor if command == "leave" else args.target
            selected = state["members"].get(target)
            require(selected and selected["active"] and selected["seat"] != "coordinator",
                    "target must be an active non-coordinator member")
            require(phase != "synthesis" or selected["seat"] == "chairman",
                    "panel is frozen after final tally")
            return "withdrawn", actor, {"target": target, "reason": content}
        if command in ("advance", "close", "abort"):
            require(member["seat"] == "coordinator", "coordinator operation")
            if command == "advance":
                return "phase", actor, policy.advance(state, args)
            if command == "abort":
                return "aborted", actor, {"reason": content}
            require(phase == "synthesis", "finish deliberation before closing")
            if state["verdict_seq"] is not None:
                require(not content and not args.fallback_reason and not args.decision, "cannot replace chairman verdict")
                return "closed", actor, {"verdict_seq": state["verdict_seq"]}
            reason = args.fallback_reason or state["fallback"]
            require(reason and reason.strip() and content, "chairman pending; explicit fallback required")
            require(args.decision == decision_key(state["result"]), "decision does not match authoritative result")
            return "closed", actor, {"fallback": reason, "fallback_verdict": content,
                                     "decision_ack": args.decision}
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
        if phase == "synthesis":
            require(args.decision == decision_key(state["result"]), "decision does not match authoritative result")
            data["decision_ack"] = args.decision
        else:
            require(args.decision is None, "decision acknowledgement belongs in synthesis")
        if phase == "position" and policy.weighted(state):
            require(args.stance and policy.normalize(args.stance) and
                    len(args.stance) <= 200 and args.confidence in state["protocol"]["voting"]["confidence_weights"] and args.dealbreaker,
                    "position requires --stance, --confidence and --dealbreaker")
            data.update(stance=args.stance, confidence=args.confidence, dealbreaker=args.dealbreaker)
        else:
            require(not (args.stance or args.confidence or args.dealbreaker),
                    "structured votes only in full/quick final positions")
        return "submission", actor, data

    def mutate(state):
        # An identical retry returns its original receipt, even after a phase change.
        # Authentication still uses the caller's own saved local identity.
        member = state["members"].get(args.actor)
        token = sessions.token(discussion, args.actor) if member else None
        require(member and token and hmac.compare_digest(member["token_hash"], token_hash(token)),
                "unknown local identity")
        previous = receipt(state, args, fingerprint, args.actor)
        if previous:
            return previous
        require(member["active"], "inactive local identity")
        return with_request(perform(state, member), args, fingerprint)

    record = store.append(discussion, mutate)
    return {"discussion": discussion, "seq": record["seq"], "type": record["type"],
            "replayed": record.get("replayed", False)}


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--version", action="version", version="Council LADP " + VERSION)
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("roster")
    commands.add_parser("protocol", help="validate and display the canonical YAML rules")
    create = commands.add_parser("create")
    create.add_argument("--request-id", required=True, help="stable 32-hex ID for the new discussion")
    create.add_argument("--title", required=True)
    create.add_argument("--topic", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--mode", choices=protocol.MODES, default="full")
    create.add_argument("--members", help="comma-separated upstream persona slugs; omit for all")
    create.add_argument("--expert", help="domain-weight seat, fixed before analysis")
    commands.add_parser("list").add_argument("--all", action="store_true")
    commands.add_parser("sessions").add_argument("discussion", nargs="?")
    for action in ("join", "status", "view", "wait", "advance", "commit",
                   "reveal", "submit", "close", "abort", "leave", "remove"):
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
        if action not in ("status", "view", "wait"):
            c.add_argument("--request-id", required=True, help="unique 32-hex ID; reuse only for exact retries")
        if action not in ("status", "view", "wait", "join"):
            c.add_argument("--expect-phase", required=True, help="phase observed before preparing this action")
        if action in ("submit", "close"):
            c.add_argument("--decision", help="acknowledge the authoritative decision_key during synthesis")
        if action == "remove":
            c.add_argument("--target", required=True, help="exact active actor ID from coordinator view")
        if action in ("submit", "commit", "abort", "close", "leave", "remove"):
            c.add_argument("--content", required=action != "close")
        if action in ("advance", "close"):
            c.add_argument("--fallback-reason")
        if action == "advance":
            c.add_argument("--enforcement", help="summary of all full-mode enforcement checks")
            c.add_argument("--followup", action="append", help="seat=targeted enforcement instruction")
            c.add_argument("--alias", action="append", help="submitted label=canonical label")
        if action == "submit":
            c.add_argument("--stance")
            c.add_argument("--confidence", choices=protocol.CONFIDENCES)
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
