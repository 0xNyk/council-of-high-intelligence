"""Council's shared YAML rules and their transport-independent validation.

Native Skills read the same file directly. Only this adapter needs PyYAML.
The validated configuration is ordinary JSON-compatible data, pinned per room.
"""
import math
from fractions import Fraction
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[2] / "configs/discussion-protocol.yaml"
MODES = ("full", "quick", "duo")
CONFIDENCES = ("high", "med", "low")
STAGES = ("restatement", "analysis", "debate", "enforcement", "position", "synthesis")
TRANSPORT_STAGES = {
    "restatement": ("restate",), "analysis": ("commit", "reveal"),
    "debate": ("debate",), "enforcement": ("enforce",),
    "position": ("position",), "synthesis": ("synthesis",),
}


def check(condition, message):
    if not condition:
        raise ValueError("invalid discussion protocol: " + message)


def keys(data, required, optional=(), context="mapping"):
    check(isinstance(data, dict) and set(required) <= set(data)
          and set(data) <= set(required) | set(optional), context + " has missing/unknown keys")


def integer(value, low, high, name):
    check(type(value) is int and low <= value <= high, name + " out of range")


def fraction(value, name):
    check(type(value) in (int, float) and -100 <= value <= 100 and math.isfinite(value),
          name + " must be a finite number within [-100, 100]")
    f = Fraction(str(value))
    check(f.denominator <= 10000, name + " rational denominator exceeds 10000")
    return f


def validate(config):
    keys(config, ("schema_version", "modes", "panel", "voting", "enforcement",
                  "word_limits", "native_hosts"), context="root")
    check(type(config["schema_version"]) is int and config["schema_version"] == 1,
          "unsupported schema_version")
    panel = config["panel"]
    keys(panel, ("min_active", "max_manual_members"), context="panel")
    integer(panel["min_active"], 2, 26, "panel.min_active")
    integer(panel["max_manual_members"], panel["min_active"], 26, "panel.max_manual_members")
    modes = config["modes"]
    keys(modes, MODES, context="modes")
    for mode, rule in modes.items():
        keys(rule, ("stages", "voting", "anonymous_stages", "sequential_debate_max_panel"),
             ("panel_size", "optional_batch_min_panel"), "mode " + mode)
        stages = rule["stages"]
        check(isinstance(stages, list) and all(isinstance(s, str) and s in STAGES for s in stages)
              and stages == [s for s in STAGES if s in stages], mode + " stages must be unique and in supported order")
        check({"analysis", "position", "synthesis"} <= set(stages), mode + " missing required stages")
        # Prompt templates exist for these mode/stage combinations. The optional
        # enforcement gate can be disabled without changing executable code.
        if mode == "full":
            check({"restatement", "debate"} <= set(stages), "full requires restatement and debate")
        elif mode == "quick":
            check(not set(stages) & {"restatement", "debate", "enforcement"},
                  "quick embeds restatement and has no debate or enforcement")
        else:
            check("debate" in stages and not set(stages) & {"restatement", "enforcement"},
                  "duo embeds restatement and requires debate")
        check(rule["voting"] == ("dialectic" if mode == "duo" else "weighted"),
              mode + " has unsupported voting mode")
        anon = rule["anonymous_stages"]
        allowed_anon = {"full": {"debate", "enforcement"}, "quick": {"position"}, "duo": set()}[mode]
        check(isinstance(anon, list) and all(isinstance(s, str) and s in allowed_anon and s in stages
              for s in anon) and len(anon) == len(set(anon)), mode + " has unsupported anonymous stages")
        integer(rule["sequential_debate_max_panel"], 0, 26, mode + " sequential debate limit")
        if "optional_batch_min_panel" in rule:
            check(mode == "full", "batch debate only supported in full")
            integer(rule["optional_batch_min_panel"], 2, 26, "optional batch minimum")
        if mode == "duo":
            check("panel_size" in rule, "duo requires panel_size")
            integer(rule["panel_size"], panel["min_active"], 2, "duo panel_size")
        else:
            check("panel_size" not in rule, "fixed panel_size only supported in duo")
    voting = config["voting"]
    keys(voting, ("member_weight", "expert_weight", "consensus_threshold", "confidence_weights"),
         context="voting")
    member = fraction(voting["member_weight"], "member_weight")
    expert = fraction(voting["expert_weight"], "expert_weight")
    check(0 < member <= expert <= 100, "weights must satisfy 0 < member <= expert <= 100")
    threshold = voting["consensus_threshold"]
    keys(threshold, ("numerator", "denominator"), context="consensus_threshold")
    integer(threshold["denominator"], 2, 10000, "threshold denominator")
    integer(threshold["numerator"], 1, threshold["denominator"], "threshold numerator")
    check(2 * threshold["numerator"] > threshold["denominator"], "consensus threshold must exceed one half")
    factors = voting["confidence_weights"]
    keys(factors, CONFIDENCES, context="confidence_weights")
    high, med, low = (fraction(factors[c], c + " confidence") for c in CONFIDENCES)
    check(0 <= low <= med <= high <= 1, "confidence weights must be ordered within [0, 1]")
    enforcement = config["enforcement"]
    counts = ("min_dissenters", "min_new_claims", "counterfactual_seats", "max_pair_messages",
              "min_peer_engagements", "dissent_words", "anti_recursion_words")
    keys(enforcement, (*counts, "agreement_percent", "monoculture_percent"), context="enforcement")
    for name in counts:
        integer(enforcement[name], 1, 10000, name)
    for name in ("agreement_percent", "monoculture_percent"):
        integer(enforcement[name], 1, 100, name)
    limits = config["word_limits"]
    keys(limits, ("restatement", *MODES), context="word_limits")
    integer(limits["restatement"], 1, 10000, "restatement word limit")
    for mode in MODES:
        names = ("analysis", "position") if mode == "quick" else ("analysis", "debate", "position")
        keys(limits[mode], names, context=mode + " word_limits")
        for name, value in limits[mode].items():
            integer(value, 1, 10000, mode + " " + name + " word limit")
    hosts = config["native_hosts"]
    keys(hosts, ("claude", "codex", "gemini", "opencode"), context="native_hosts")
    for host, override in hosts.items():
        keys(override, (), ("separate_restatement", "parallel_rounds", "confidence_weighting", "word_limits"),
             host + " overrides")
        for name in ("separate_restatement", "parallel_rounds", "confidence_weighting"):
            if name in override:
                check(type(override[name]) is bool, host + " " + name + " must be boolean")
        if "word_limits" in override:
            keys(override["word_limits"], (), MODES, host + " word_limits")
            for mode, values in override["word_limits"].items():
                keys(values, (), tuple(limits[mode]), host + " " + mode + " word_limits")
                for name, value in values.items():
                    integer(value, 1, 10000, host + " " + mode + " " + name)
    return config


def load(path=None):
    try:
        import yaml
    except ImportError as exc:
        raise ValueError("LADP requires PyYAML; install the adapter's requirements.txt "
                         "in the Python environment used to invoke adapter.py") from exc

    class UniqueSafeLoader(yaml.SafeLoader):
        pass

    def mapping(loader, node):
        values = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node)
            check(isinstance(key, str) and key not in values, "duplicate/non-string YAML key")
            values[key] = loader.construct_object(value_node)
        return values

    UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    with Path(path or CONFIG).open(encoding="utf-8") as handle:
        text = handle.read(128 * 1024 + 1)
    check(len(text) <= 128 * 1024, "configuration too large")
    try:
        # Reject aliases/anchors: the compact configuration has no need for
        # recursive objects or merge-key semantics.
        check(not any(isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
                      for token in yaml.scan(text)), "YAML anchors and aliases are not supported")
        value = yaml.load(text, Loader=UniqueSafeLoader)
    except yaml.YAMLError as exc:
        raise ValueError("invalid discussion protocol YAML: " + str(exc)) from exc
    return validate(value)


def transport_phases(config, mode):
    return ("lobby",) + tuple(phase for stage in config["modes"][mode]["stages"]
                              for phase in TRANSPORT_STAGES[stage])


def business_stage(phase):
    return next((stage for stage, phases in TRANSPORT_STAGES.items() if phase in phases), phase)
