"""Council-specific state projection and phase contract.

The LADP core calls this module through its projection interface; it has no
knowledge of Council, roles or deliberation modes.
"""
import hashlib
from core.storage import require

VERSION = 1
TERMINAL = ("closed", "aborted")
PHASES = {
    "full": ("lobby", "restate", "commit", "reveal", "debate", "enforce", "position", "synthesis"),
    "quick": ("lobby", "commit", "reveal", "position", "synthesis"),
    "duo": ("lobby", "commit", "reveal", "debate", "position", "synthesis"),
}
CONFIDENCE = {"high": 4, "med": 3, "low": 2}


def digest(content, nonce):
    return hashlib.sha256((nonce + "\0" + content).encode("utf-8")).hexdigest()


def initial(first):
    d = first["data"]
    require(first["type"] == "created" and d.get("policy_version") == VERSION,
            "unsupported Council local protocol")
    return {"policy_version": VERSION, "title": d["title"], "topic": d["topic"],
            "mode": d["mode"], "panel": d["panel"], "expert": d["expert"],
            "policy_hash": d["policy_hash"], "coordinator": first["actor"],
            "members": {}, "phase": "lobby", "submissions": {}, "commits": {},
            "votes": {}, "followups": {}, "enforcement_checks": None,
            "fallback": None, "result": None, "verdict_seq": None,
            "last_seq": 0, "updated_at": first["at"]}


def apply(state, record):
    require(record["seq"] == state["last_seq"] + 1, "non-contiguous event")
    kind, actor, data = record["type"], record["actor"], record["data"]
    if kind in ("created", "joined"):
        state["members"][actor] = dict(data["member"], active=True)
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
        if data["phase"] == "position" and state["mode"] != "duo":
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
    if state.get("policy_version") != VERSION:
        raise ValueError("incompatible state cache")
    return state


def occupied(state):
    return {member["seat"]: actor for actor, member in state["members"].items()
            if member["active"]}


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
    return [seat for seat in required if seats.get(seat) not in state["submissions"]]


def can_submit(state, actor):
    member = state["members"][actor]
    seat = member["seat"]
    phase = state["phase"]
    require(phase not in TERMINAL and phase != "lobby", "no submission in this phase")
    require(seat in pending_seats(state), "not eligible or already submitted")
    if phase == "debate" and state["mode"] == "full" and len(state["panel"]) <= 4:
        require(seat == pending_seats(state)[0], "wait for earlier cross-examination seat")
    return seat


def normalize(label):
    return " ".join(label.casefold().split())


def tally(state, aliases):
    if state["mode"] == "duo":
        require(not aliases, "duo does not use weighted voting")
        return {"kind": "dialectic", "consensus": None}
    labels = {normalize(v["stance"]) for v in state["votes"].values()}
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
    weights = {seat: 6 if seat == state["expert"] else 4 for seat in state["panel"]}
    total = sum(weights.values()) * 4
    scores, ballots = {}, []
    for actor, vote in state["votes"].items():
        seat = state["members"][actor]["seat"]
        label = normalize(vote["stance"])
        canonical = mapping.get(label, label)
        units = weights[seat] * CONFIDENCE[vote["confidence"]]
        ballots.append(dict(vote, seat=seat, canonical=canonical,
                            units=units if canonical != "abstain" else 0))
        if canonical != "abstain":
            scores[canonical] = scores.get(canonical, 0) + units
    winners = [label for label, units in scores.items() if units * 3 >= total * 2]
    return {"kind": "weighted", "unit": "1/16 vote", "total_units": total,
            "threshold_fraction": "2/3", "scores": scores, "ballots": ballots,
            "aliases": mapping, "consensus": winners[0] if len(winners) == 1 else None}


def advance(state, args):
    phase, mode = state["phase"], state["mode"]
    require(phase in PHASES[mode] and phase != "synthesis", "cannot advance from " + phase)
    require(not pending_seats(state), "pending seats: " + ", ".join(pending_seats(state)))
    require(not args.fallback_reason or phase == "lobby", "start fallback belongs in lobby")
    require(not args.followup or (mode == "full" and phase == "debate"),
            "enforcement follow-ups belong after full cross-examination")
    require(not args.enforcement or (mode == "full" and phase == "debate"),
            "enforcement scan belongs after full cross-examination")
    require(not args.alias or phase == "position", "stance aliases belong after final positions")
    if phase == "lobby":
        chair_joined = "chairman" in occupied(state)
        require(chair_joined or args.fallback_reason, "chairman must join or record explicit fallback")
        require(not (chair_joined and args.fallback_reason), "a chairman is already seated")
        return {"phase": "restate" if mode == "full" else "commit",
                "fallback": args.fallback_reason}
    if phase == "debate" and mode == "full":
        require(args.enforcement and args.enforcement.strip(), "record the upstream enforcement scan")
        followups = {}
        for item in args.followup or []:
            seat, sep, reason = item.partition("=")
            require(sep and seat in state["panel"] and reason.strip() and seat not in followups,
                    "followup must be a unique panel seat=instruction")
            followups[seat] = reason
        return {"phase": "enforce" if followups else "position", "followups": followups,
                "enforcement_checks": args.enforcement}
    if phase == "position":
        return {"phase": "synthesis", "result": tally(state, args.alias)}
    return {"phase": PHASES[mode][PHASES[mode].index(phase) + 1]}
