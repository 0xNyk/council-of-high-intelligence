"""Council-specific state projection and phase contract.

The LADP core calls this module through its projection interface; it has no
knowledge of Council, roles or deliberation modes.
"""
import hashlib
import math
from fractions import Fraction
from pathlib import Path
from ladp_core.storage import require
from ladp_core.metadata import checksum
import protocol

VERSION = 3
TERMINAL = ("closed", "aborted")


def implementation_hash():
    """Pin executable policy, not merely its prose inputs."""
    digest = hashlib.sha256()
    for name in ("policy.py", "adapter.py", "resources.py", "protocol.py"):
        digest.update(name.encode("ascii"))
        digest.update(Path(__file__).with_name(name).read_bytes())
    return digest.hexdigest()


def check_version(data):
    require(data.get("policy_version") == VERSION
            and data.get("implementation_hash") == implementation_hash(),
            "incompatible Council policy; use the adapter version that created this room")


def rules(state):
    return state["protocol"]["modes"][state["mode"]]


def phases(state):
    return protocol.transport_phases(state["protocol"], state["mode"])


def weighted(state):
    return rules(state)["voting"] == "weighted"


def sequential_debate(state):
    return len(state["panel"]) <= rules(state)["sequential_debate_max_panel"]


def anonymous_stage(state):
    return protocol.business_stage(state["phase"]) in rules(state)["anonymous_stages"]


def digest(content, nonce):
    return hashlib.sha256((nonce + "\0" + content).encode("utf-8")).hexdigest()


def initial(first):
    d = first["data"]
    require(first["type"] == "created", "missing creation event")
    check_version(d)
    require(checksum(d["resources"]) == d["policy_hash"], "pinned policy checksum mismatch")
    config = protocol.validate(d["resources"]["protocol"])
    return {"policy_version": VERSION, "title": d["title"], "topic": d["topic"],
            "mode": d["mode"], "panel": d["panel"], "expert": d["expert"],
            "protocol": config, "protocol_hash": checksum(config),
            "policy_hash": d["policy_hash"], "implementation_hash": d["implementation_hash"],
            "coordinator": first["actor"],
            "members": {}, "phase": "lobby", "submissions": {}, "commits": {},
            "votes": {}, "followups": {}, "enforcement_checks": None,
            "fallback": None, "result": None, "verdict_seq": None,
            "withdrawals": {}, "requests": {}, "last_seq": 0, "updated_at": first["at"]}


def apply(state, record):
    require(record["seq"] == state["last_seq"] + 1, "non-contiguous event")
    kind, actor, data = record["type"], record["actor"], record["data"]
    if kind in ("created", "joined"):
        state["members"][actor] = dict(data["member"], active=True)
    elif kind == "withdrawn":
        target = data["target"]
        state["members"][target]["active"] = False
        if state["phase"] != "lobby":
            seat = state["members"][target]["seat"]
            state["withdrawals"][seat] = data["reason"]
            if seat == "chairman" and not state["verdict_seq"]:
                state["fallback"] = data["reason"]
    elif kind == "phase":
        state["phase"] = data["phase"]
        state["submissions"] = {}
        if "fallback" in data:
            state["fallback"] = data["fallback"]
        if "followups" in data:
            state["followups"] = data["followups"]
        if "enforcement_checks" in data:
            state["enforcement_checks"] = data["enforcement_checks"]
        if "result" in data:
            state["result"] = data["result"]
    elif kind == "commit":
        state["commits"][actor] = data["digest"]
        state["submissions"][actor] = record["seq"]
    elif kind == "submission":
        state["submissions"][actor] = record["seq"]
        if data["phase"] == "position" and weighted(state):
            state["votes"][actor] = {k: data[k] for k in ("stance", "confidence", "dealbreaker")}
        if data["phase"] == "synthesis":
            state["verdict_seq"] = record["seq"]
    elif kind == "closed":
        state["phase"] = "closed"
        state["verdict_seq"] = data.get("verdict_seq", record["seq"])
        state["fallback"] = data.get("fallback", state["fallback"])
    elif kind == "aborted":
        state["phase"] = "aborted"
    else:
        require(False, "unknown event type: " + kind)
    if "_request" in data:
        req = data["_request"]
        require(req["id"] not in state["requests"], "duplicate request in history")
        state["requests"][req["id"]] = {"hash": req["hash"], "actor": actor,
                                         "seq": record["seq"], "type": kind}
    state["last_seq"] = record["seq"]
    state["updated_at"] = record["at"]


def reconstruct(records):
    state = initial(records[0])
    for record in records:
        apply(state, record)
    return state


def export_state(state):
    return state


def import_state(state):
    if (state.get("policy_version") != VERSION
            or state.get("implementation_hash") != implementation_hash()):
        raise ValueError("incompatible state cache")
    return state


def occupied(state):
    return {member["seat"]: actor for actor, member in state["members"].items()
            if member["active"]}


def active_panel(state):
    seats = occupied(state)
    return [seat for seat in state["panel"] if seat in seats]


def pending_seats(state):
    phase = state["phase"]
    seats = occupied(state)
    if phase in TERMINAL:
        return []
    if phase == "lobby":
        return [seat for seat in state["panel"] if seat not in seats]
    if phase == "synthesis":
        return [] if state["fallback"] or state["verdict_seq"] else ["chairman"]
    required = list(state["followups"]) if phase == "enforce" else state["panel"]
    return [seat for seat in required if seat in seats and
            seats[seat] not in state["submissions"]]


def can_submit(state, actor):
    member = state["members"][actor]
    seat = member["seat"]
    phase = state["phase"]
    require(phase not in TERMINAL and phase != "lobby", "no submission in this phase")
    require(seat in pending_seats(state), "not eligible or already submitted")
    if phase == "debate" and sequential_debate(state):
        require(seat == pending_seats(state)[0], "wait for earlier cross-examination seat")
    return seat


def normalize(label):
    return " ".join(label.casefold().split())


def tally(state, aliases):
    if not weighted(state):
        require(not aliases, "duo does not use weighted voting")
        return {"kind": "dialectic", "consensus": None}
    active = occupied(state)
    labels = {normalize(v["stance"]) for actor, v in state["votes"].items()
              if actor in active.values()}
    mapping = {}
    for entry in aliases or []:
        old, sep, new = entry.partition("=")
        old, new = normalize(old), normalize(new)
        require(sep and old in labels and new and old != "abstain" and new != "abstain",
                "alias must map a submitted non-abstain label to a canonical label")
        require(old not in mapping, "duplicate alias")
        mapping[old] = new
    require(not any(new in mapping and mapping[new] != new for new in mapping.values()),
            "alias chains are not supported")
    voting = state["protocol"]["voting"]
    base = Fraction(str(voting["member_weight"]))
    expert = Fraction(str(voting["expert_weight"]))
    confidence = {k: Fraction(str(v)) for k, v in voting["confidence_weights"].items()}
    weights = {seat: expert if seat == state["expert"] else base for seat in state["panel"]}
    # Preserve the existing 1/16 vote display unit for default rules, expanding
    # to an exact common denominator for other configured rational weights.
    scale = math.lcm(16, *(w.denominator for w in weights.values()),
                    *((w * factor).denominator for w in weights.values() for factor in confidence.values()))
    total = int(sum(weights.values()) * scale)
    scores, ballots = {}, []
    for actor, vote in state["votes"].items():
        seat = state["members"][actor]["seat"]
        if not state["members"][actor]["active"]:
            ballots.append(dict(vote, seat=seat, canonical=None, units=0, withdrawn=True))
            continue
        label = normalize(vote["stance"])
        canonical = mapping.get(label, label)
        units = int(weights[seat] * confidence[vote["confidence"]] * scale)
        ballots.append(dict(vote, seat=seat, canonical=canonical,
                            units=units if canonical != "abstain" else 0))
        if canonical != "abstain":
            scores[canonical] = scores.get(canonical, 0) + units
    threshold = voting["consensus_threshold"]
    numerator, denominator = threshold["numerator"], threshold["denominator"]
    winners = [label for label, units in scores.items() if units * denominator >= total * numerator]
    return {"kind": "weighted", "unit": f"1/{scale} vote", "total_units": total,
            "threshold_fraction": f"{numerator}/{denominator}", "scores": scores, "ballots": ballots,
            "aliases": mapping, "withdrawals": dict(state["withdrawals"]),
            "consensus": winners[0] if len(winners) == 1 else None}


def advance(state, args):
    phase = state["phase"]
    sequence = phases(state)
    require(phase in sequence and phase != "synthesis", "cannot advance from " + phase)
    next_phase = sequence[sequence.index(phase) + 1]
    enforcement_gate = phase == "debate" and next_phase == "enforce"
    require(not pending_seats(state), "pending seats: " + ", ".join(pending_seats(state)))
    minimum = state["protocol"]["panel"]["min_active"]
    require(len(active_panel(state)) >= minimum, f"fewer than {minimum} active panel seats; abort the room")
    require(not args.fallback_reason or phase == "lobby", "start fallback belongs in lobby")
    require(args.fallback_reason is None or args.fallback_reason.strip(), "fallback reason must not be blank")
    require(not args.followup or enforcement_gate,
            "enforcement follow-ups belong after full cross-examination")
    require(not args.enforcement or enforcement_gate,
            "enforcement scan belongs after full cross-examination")
    require(not args.alias or phase == "position", "stance aliases belong after final positions")
    if phase == "lobby":
        chair_joined = "chairman" in occupied(state)
        require(chair_joined or args.fallback_reason, "chairman must join or record explicit fallback")
        require(not (chair_joined and args.fallback_reason), "a chairman is already seated")
        return {"phase": next_phase,
                "fallback": args.fallback_reason}
    if enforcement_gate:
        require(args.enforcement and args.enforcement.strip(), "record the upstream enforcement scan")
        followups = {}
        for item in args.followup or []:
            seat, sep, reason = item.partition("=")
            require(sep and seat in active_panel(state) and reason.strip() and seat not in followups,
                    "followup must be a unique panel seat=instruction")
            followups[seat] = reason
        return {"phase": next_phase if followups else sequence[sequence.index(next_phase) + 1], "followups": followups,
                "enforcement_checks": args.enforcement}
    if phase == "position":
        return {"phase": next_phase, "result": tally(state, args.alias)}
    return {"phase": next_phase}
