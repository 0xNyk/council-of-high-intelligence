"""
Council of High Intelligence — MCP Server.

A comprehensive Model Context Protocol server that exposes all CoHI
features as tools and resources.  Any MCP-compatible client (Antigravity
IDE, Claude Desktop, Cursor, etc.) can discover council members, set up
panels, generate round prompts, run enforcement scans, compute vote
tallies, select a chairman, and render verdicts — without requiring
direct access to the agent files or shell scripts.

Run directly::

    python server.py                         # stdio transport (default)
    python server.py --transport sse         # SSE transport

Or point your MCP client config at this file.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from .config_loader import (
    load_auto_route_defaults,
    load_model_slots,
    resolve_project_root,
)
from .council_registry import CouncilRegistry
from .deliberation_engine import (
    anonymize_all_outputs,
    build_anonymization_mapping,
    compute_vote_tally,
    generate_chairman_prompt,
    generate_duo_round1_prompts,
    generate_duo_round2_prompts,
    generate_duo_round3_prompts,
    generate_quick_round1_prompts,
    generate_quick_round2_prompts,
    generate_restate_prompts,
    generate_round1_prompts,
    generate_round2_prompts,
    generate_round3_prompts,
    parse_all_stances,
    run_enforcement_scan,
)
from .models import (
    DeliberationMode,
    PanelSelection,
    RoutingTable,
    SessionMetadata,
)
from .provider_detection import (
    detect_providers as _detect_providers,
    fallback_anthropic_only,
)
from .routing_engine import (
    auto_route,
    manual_route,
    no_route,
    select_chairman,
)
from .verdict_renderer import (
    get_verdict_template,
    render_duo_verdict,
    render_full_verdict,
    render_quick_verdict,
    render_session_metadata,
)

# ---------------------------------------------------------------------------
# Server initialisation
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "CouncilOfHighIntelligence",
    instructions=(
        "Council of High Intelligence (CoHI) — 18 AI personas deliberate "
        "your hardest decisions through structured multi-round protocols. "
        "This MCP server exposes the full council knowledge base, panel "
        "selection, provider routing, prompt generation, enforcement, "
        "vote tallying, and verdict rendering."
    ),
)

# Singleton registry — lazily loaded on first tool call.
_registry = CouncilRegistry()


def _get_members_by_names(names: list[str]):
    """Resolve a list of short names to CouncilMember objects."""
    members = []
    for name in names:
        m = _registry.get_member(name)
        if m:
            members.append(m)
    return members


# ═══════════════════════════════════════════════════════════════════════════
# TOOLS — 18 tools covering all CoHI features
# ═══════════════════════════════════════════════════════════════════════════


# ---------------------------------------------------------------------------
# 1. list_members
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_members() -> str:
    """
    List all 18 council members with their figure, domain, polarity,
    model tier, and polarity pairs.

    Returns a structured overview of every council member available for
    panel selection.
    """
    members = _registry.list_members()
    result = []
    for m in members:
        result.append({
            "name": m.short_name,
            "figure": m.council.figure,
            "domain": m.council.domain,
            "polarity": m.council.polarity,
            "model_tier": m.model_tier,
            "polarity_pairs": m.council.polarity_pairs,
            "triads": m.council.triads,
            "profiles": m.council.profiles,
        })
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# 2. get_member
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_member(name: str) -> str:
    """
    Get a specific council member's full profile including identity,
    grounding protocol, analytical method, and output formats.

    Args:
        name: Member short name (e.g. "socrates", "feynman", "karpathy").
    """
    member = _registry.get_member(name)
    if not member:
        return json.dumps({"error": f"Member '{name}' not found."})

    return json.dumps({
        "name": member.short_name,
        "figure": member.council.figure,
        "domain": member.council.domain,
        "polarity": member.council.polarity,
        "model_tier": member.model_tier,
        "polarity_pairs": member.council.polarity_pairs,
        "provider_affinity": member.council.provider_affinity,
        "triads": member.council.triads,
        "duo_keywords": member.council.duo_keywords,
        "profiles": member.council.profiles,
        "identity": member.identity,
        "grounding_protocol": member.grounding_protocol,
        "analytical_method": member.analytical_method,
        "what_you_see": member.what_you_see,
        "what_you_miss": member.what_you_miss,
        "when_deliberating": member.when_deliberating,
        "output_format_round2": member.output_format_round2,
        "output_format_standalone": member.output_format_standalone,
    }, indent=2)


# ---------------------------------------------------------------------------
# 3. list_triads
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_triads() -> str:
    """
    List all 20 pre-defined domain triads with their members and rationale.

    Each triad is a 3-member combination optimised for a specific domain
    (e.g. "architecture", "ai-safety", "decision", "design").
    """
    triads = _registry.list_triads()
    result = [
        {
            "domain": t.domain,
            "members": t.members,
            "rationale": t.rationale,
        }
        for t in triads
    ]
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# 4. list_duo_pairs
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_duo_pairs() -> str:
    """
    List all 13 duo polarity pairs with their domain keywords and tensions.

    Duo pairs are used in --duo mode for focused 2-member dialectics.
    A default pair (Socrates vs Feynman) is used when no keywords match.
    """
    pairs = _registry.list_duo_pairs()
    result = [
        {
            "domain_keywords": p.domain_keywords,
            "member_a": p.member_a,
            "member_b": p.member_b,
            "tension": p.tension,
        }
        for p in pairs
    ]
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# 5. list_profiles
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_profiles() -> str:
    """
    List all council profiles (classic, exploration-orthogonal, execution-lean).

    Each profile defines a fixed member roster and profile-specific triads
    for different deliberation needs.
    """
    profiles = _registry.list_profiles()
    result = []
    for p in profiles:
        result.append({
            "name": p.name,
            "description": p.description,
            "members": p.members,
            "member_count": len(p.members),
            "triads": {
                k: {"members": v.members, "rationale": v.rationale}
                for k, v in p.triads.items()
            },
        })
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# 6. select_panel
# ---------------------------------------------------------------------------

@mcp.tool()
async def select_panel(
    problem: str,
    mode: str = "full",
    triad: str | None = None,
    members: str | None = None,
    profile: str | None = None,
    use_full_panel: bool = False,
) -> str:
    """
    Select panel members for a deliberation (STEP 0).

    Determines which council members to convene based on the mode and
    selection flags, and designates the domain-weight seat (1.5×).

    Args:
        problem: The problem statement to deliberate.
        mode: Deliberation mode — "full", "quick", or "duo".
        triad: Domain keyword for a pre-defined triad (e.g. "architecture").
        members: Comma-separated member names (e.g. "socrates,feynman,ada").
        profile: Profile name (e.g. "exploration-orthogonal").
        use_full_panel: If True, use all 18 members.

    Returns:
        Panel selection with members, mode, domain-weight seat, and rationale.
    """
    delib_mode = DeliberationMode(mode)
    selected_names: list[str] = []
    rationale = ""

    if delib_mode == DeliberationMode.DUO:
        # Duo mode: select a polarity pair
        if members:
            pair_names = [n.strip() for n in members.split(",")]
            if len(pair_names) != 2:
                return json.dumps({
                    "error": "Duo mode requires exactly 2 members."
                })
            selected_names = pair_names
            rationale = f"Manual duo selection: {pair_names[0]} vs {pair_names[1]}"
        else:
            duo_pair = _registry.match_duo_pair(problem)
            selected_names = [duo_pair.member_a, duo_pair.member_b]
            rationale = (
                f"Auto-selected duo pair: {duo_pair.member_a} vs "
                f"{duo_pair.member_b} — {duo_pair.tension}"
            )
    elif use_full_panel:
        selected_names = [m.short_name for m in _registry.list_members()]
        rationale = "Full panel: all 18 members."
    elif members:
        selected_names = [n.strip() for n in members.split(",")]
        rationale = f"Manual selection: {', '.join(selected_names)}"
    elif profile:
        p = _registry.get_profile(profile)
        if not p:
            return json.dumps({"error": f"Profile '{profile}' not found."})
        selected_names = list(p.members)
        if triad and triad in p.triads:
            selected_names = list(p.triads[triad].members)
            rationale = (
                f"Profile '{profile}' triad '{triad}': "
                f"{', '.join(selected_names)}"
            )
        else:
            rationale = f"Profile '{profile}': {len(selected_names)} members."
    elif triad:
        t = _registry.get_triad(triad)
        if not t:
            return json.dumps({"error": f"Triad '{triad}' not found."})
        selected_names = list(t.members)
        rationale = f"Triad '{triad}': {t.rationale}"
    else:
        # Auto-select triad based on problem
        t = _registry.auto_select_triad(problem)
        selected_names = list(t.members)
        rationale = (
            f"Auto-selected triad '{t.domain}': {t.rationale}. "
            f"Members: {', '.join(t.members)}"
        )

    # Validate selected members
    validation = _registry.validate_panel(selected_names)
    if not validation["valid"]:
        return json.dumps({
            "error": "Invalid panel",
            "details": validation["errors"],
        })

    # Designate domain-weight seat
    domain_weight_member = None
    domain_weight_rationale = ""
    problem_lower = problem.lower()

    best_score = 0
    candidates: list[tuple[str, int]] = []
    for name in selected_names:
        m = _registry.get_member(name)
        if not m:
            continue
        score = 0
        for word in m.council.domain.lower().split():
            if len(word) > 3 and word in problem_lower:
                score += 1
        candidates.append((name, score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    if len(candidates) >= 2 and candidates[0][1] > candidates[1][1] > 0:
        domain_weight_member = candidates[0][0]
        m = _registry.get_member(domain_weight_member)
        domain_weight_rationale = (
            f"{domain_weight_member} (1.5×) — domain '{m.council.domain}' "
            f"most directly matches the problem."
        )
    elif candidates and candidates[0][1] > 0:
        domain_weight_member = candidates[0][0]
        m = _registry.get_member(domain_weight_member)
        domain_weight_rationale = (
            f"{domain_weight_member} (1.5×) — domain '{m.council.domain}' "
            f"matches the problem."
        )
    else:
        domain_weight_rationale = "No domain-weight seat (ambiguous match)."

    result = PanelSelection(
        members=selected_names,
        mode=delib_mode,
        domain_weight_member=domain_weight_member,
        domain_weight_rationale=domain_weight_rationale,
        selection_rationale=rationale,
    )
    return json.dumps(result.model_dump(), indent=2)


# ---------------------------------------------------------------------------
# 7. detect_providers
# ---------------------------------------------------------------------------

@mcp.tool()
async def detect_providers() -> str:
    """
    Detect available LLM providers on the system.

    Runs the detect-providers.sh script and returns structured info
    about each provider (Anthropic, OpenAI/Codex, Google/Agy, Ollama,
    NVIDIA NIM, Cursor CLI) including availability and supported models.
    """
    try:
        providers = _detect_providers()
    except (FileNotFoundError, RuntimeError) as exc:
        providers = fallback_anthropic_only()
        return json.dumps({
            "warning": f"Detection failed: {exc}. Using Anthropic-only fallback.",
            "providers": [p.model_dump() for p in providers],
        }, indent=2)

    return json.dumps({
        "providers": [p.model_dump() for p in providers],
        "available_count": sum(1 for p in providers if p.available),
        "multi_provider": sum(1 for p in providers if p.available) >= 2,
    }, indent=2)


# ---------------------------------------------------------------------------
# 8. compute_routing
# ---------------------------------------------------------------------------

@mcp.tool()
async def compute_routing(
    member_names: str,
    models_config_path: str | None = None,
    no_auto_route: bool = False,
) -> str:
    """
    Compute the member-to-provider routing table (STEP 1).

    Supports three routing paths:
      - Auto-routing (default): detects providers, applies polarity
        separation, spread, affinity, and tier matching.
      - Manual routing: loads a YAML seat mapping file.
      - No routing: all members on Anthropic with frontmatter defaults.

    Args:
        member_names: Comma-separated member short names.
        models_config_path: Path to a provider-model-slots YAML file
                            for manual routing. Relative paths resolve
                            against the configs/ directory.
        no_auto_route: If True, skip detection and use Claude-only defaults.

    Returns:
        Routing table with member → provider → model → exec_method slots.
    """
    names = [n.strip() for n in member_names.split(",")]
    members = _get_members_by_names(names)

    if not members:
        return json.dumps({"error": "No valid members found."})

    if no_auto_route:
        table = no_route(members)
    elif models_config_path:
        config = load_model_slots(models_config_path)
        table = manual_route(members, config)
    else:
        try:
            providers = _detect_providers()
        except (FileNotFoundError, RuntimeError):
            providers = fallback_anthropic_only()
        table = auto_route(members, providers, _registry)

    return json.dumps(table.model_dump(), indent=2)


# ---------------------------------------------------------------------------
# 9. preview_routing
# ---------------------------------------------------------------------------

@mcp.tool()
async def preview_routing(
    problem: str,
    mode: str = "full",
    triad: str | None = None,
    members: str | None = None,
    profile: str | None = None,
) -> str:
    """
    Preview the routing table without running a deliberation (--dry-route).

    Combines panel selection and routing into a single preview output
    showing which member goes to which provider/model.

    Args:
        problem: The problem statement (used for auto-selection).
        mode: Deliberation mode — "full", "quick", or "duo".
        triad: Optional domain keyword for triad selection.
        members: Optional comma-separated member names.
        profile: Optional profile name.
    """
    # Select panel
    panel_json = await select_panel(
        problem=problem, mode=mode, triad=triad, members=members,
        profile=profile,
    )
    panel = json.loads(panel_json)
    if "error" in panel:
        return panel_json

    # Compute routing
    routing_json = await compute_routing(
        member_names=",".join(panel["members"])
    )
    routing = json.loads(routing_json)

    return json.dumps({
        "panel": panel,
        "routing": routing,
        "note": "Dry-route preview — no deliberation was run.",
    }, indent=2)


# ---------------------------------------------------------------------------
# 10. select_chairman_tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def select_chairman_tool(
    panel_members: str,
    chairman_override: str | None = None,
) -> str:
    """
    Select the Chairman for verdict synthesis (STEP 1.7).

    The Chairman is a synthesizer who did NOT participate in the
    deliberation. Selection follows the algorithm:
    1. Explicit override (--chairman flag)
    2. Config override (auto-route-defaults.yaml)
    3. Auto-select (highest-tier non-panel provider)
    4. Single-provider fallback

    Args:
        panel_members: Comma-separated panel member short names.
        chairman_override: Optional explicit chairman provider or model.
    """
    names = [n.strip() for n in panel_members.split(",")]

    try:
        providers = _detect_providers()
    except (FileNotFoundError, RuntimeError):
        providers = fallback_anthropic_only()

    chairman = select_chairman(
        panel_members=names,
        available_providers=providers,
        chairman_override=chairman_override,
    )
    return json.dumps(chairman.model_dump(), indent=2)


# ---------------------------------------------------------------------------
# 11. generate_round_prompt
# ---------------------------------------------------------------------------

@mcp.tool()
async def generate_round_prompt(
    mode: str,
    round_name: str,
    problem: str,
    member_names: str,
    previous_outputs: str | None = None,
    restatements: str | None = None,
    opponent_outputs: str | None = None,
) -> str:
    """
    Generate prompts for a specific round of deliberation.

    This is the core tool that produces ready-to-use prompts for each
    council member at each stage of the protocol. The prompts include
    inlined member identities, grounding protocols, and output formats
    so they work on any LLM without access to agent files.

    Args:
        mode: "full", "quick", or "duo".
        round_name: Round identifier — one of:
            Full mode: "restate", "analysis", "cross_examination", "final"
            Quick mode: "quick_analysis", "quick_final"
            Duo mode: "duo_opening", "duo_response", "duo_final"
        problem: The problem statement.
        member_names: Comma-separated member short names.
        previous_outputs: JSON string of {member_name: output_text} from
                         the previous round (required for cross_examination,
                         quick_final, duo_response).
        restatements: JSON string of {member_name: restatement_text} from
                     the restate gate (used in analysis round).
        opponent_outputs: JSON string of {member_name: output_text} for
                         duo_response round (member_a's and member_b's
                         Round 1 outputs).

    Returns:
        JSON with prompts for each member, plus anonymization mapping
        if applicable.
    """
    names = [n.strip() for n in member_names.split(",")]
    members = _get_members_by_names(names)
    if not members:
        return json.dumps({"error": "No valid members found."})

    # Default routing (Claude-only) for prompt generation
    routing = no_route(members)

    prev = json.loads(previous_outputs) if previous_outputs else {}
    restates = json.loads(restatements) if restatements else {}

    result: dict[str, Any] = {"round": round_name, "mode": mode, "prompts": {}}

    if round_name == "restate":
        prompts = generate_restate_prompts(members, problem, routing)
        for p in prompts:
            result["prompts"][p.member_name] = {
                "prompt_text": p.prompt_text,
                "exec_method": p.exec_method,
                "model": p.model,
                "timeout_seconds": p.timeout_seconds,
            }

    elif round_name == "analysis":
        prompts = generate_round1_prompts(members, problem, restates, routing)
        for p in prompts:
            result["prompts"][p.member_name] = {
                "prompt_text": p.prompt_text,
                "exec_method": p.exec_method,
                "model": p.model,
                "timeout_seconds": p.timeout_seconds,
            }

    elif round_name == "cross_examination":
        mapping = build_anonymization_mapping(names)
        anonymized = anonymize_all_outputs(prev, mapping)
        prompts = generate_round2_prompts(members, anonymized, routing)
        result["anonymization_mapping"] = {
            "label_to_member": mapping.label_to_member,
            "member_to_label": mapping.member_to_label,
        }
        for p in prompts:
            result["prompts"][p.member_name] = {
                "prompt_text": p.prompt_text,
                "exec_method": p.exec_method,
                "model": p.model,
                "timeout_seconds": p.timeout_seconds,
            }

    elif round_name == "final":
        prompts = generate_round3_prompts(members, routing)
        for p in prompts:
            result["prompts"][p.member_name] = {
                "prompt_text": p.prompt_text,
                "exec_method": p.exec_method,
                "model": p.model,
                "timeout_seconds": p.timeout_seconds,
            }

    elif round_name == "quick_analysis":
        prompts = generate_quick_round1_prompts(members, problem, routing)
        for p in prompts:
            result["prompts"][p.member_name] = {
                "prompt_text": p.prompt_text,
                "exec_method": p.exec_method,
                "model": p.model,
                "timeout_seconds": p.timeout_seconds,
            }

    elif round_name == "quick_final":
        mapping = build_anonymization_mapping(names)
        anonymized = anonymize_all_outputs(prev, mapping)
        prompts = generate_quick_round2_prompts(members, anonymized, routing)
        result["anonymization_mapping"] = {
            "label_to_member": mapping.label_to_member,
            "member_to_label": mapping.member_to_label,
        }
        for p in prompts:
            result["prompts"][p.member_name] = {
                "prompt_text": p.prompt_text,
                "exec_method": p.exec_method,
                "model": p.model,
                "timeout_seconds": p.timeout_seconds,
            }

    elif round_name == "duo_opening":
        if len(members) != 2:
            return json.dumps({"error": "Duo mode requires exactly 2 members."})
        prompts = generate_duo_round1_prompts(
            members[0], members[1], problem, routing,
        )
        for p in prompts:
            result["prompts"][p.member_name] = {
                "prompt_text": p.prompt_text,
                "exec_method": p.exec_method,
                "model": p.model,
                "timeout_seconds": p.timeout_seconds,
            }

    elif round_name == "duo_response":
        if len(members) != 2:
            return json.dumps({"error": "Duo mode requires exactly 2 members."})
        opp = json.loads(opponent_outputs) if opponent_outputs else prev
        output_a = opp.get(members[0].short_name, "")
        output_b = opp.get(members[1].short_name, "")
        prompts = generate_duo_round2_prompts(
            members[0], members[1], output_a, output_b, routing,
        )
        for p in prompts:
            result["prompts"][p.member_name] = {
                "prompt_text": p.prompt_text,
                "exec_method": p.exec_method,
                "model": p.model,
                "timeout_seconds": p.timeout_seconds,
            }

    elif round_name == "duo_final":
        if len(members) != 2:
            return json.dumps({"error": "Duo mode requires exactly 2 members."})
        prompts = generate_duo_round3_prompts(
            members[0], members[1], routing,
        )
        for p in prompts:
            result["prompts"][p.member_name] = {
                "prompt_text": p.prompt_text,
                "exec_method": p.exec_method,
                "model": p.model,
                "timeout_seconds": p.timeout_seconds,
            }

    else:
        return json.dumps({
            "error": f"Unknown round_name '{round_name}'.",
            "valid_rounds": {
                "full": ["restate", "analysis", "cross_examination", "final"],
                "quick": ["quick_analysis", "quick_final"],
                "duo": ["duo_opening", "duo_response", "duo_final"],
            },
        })

    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# 12. anonymize_round_outputs
# ---------------------------------------------------------------------------

@mcp.tool()
async def anonymize_round_outputs(
    member_names: str,
    outputs: str,
) -> str:
    """
    Anonymize member outputs for cross-examination rounds.

    Builds a stable label mapping (Member A, Member B, …), strips
    self-references, and replaces all member names with labels.

    Args:
        member_names: Comma-separated member short names (defines label order).
        outputs: JSON string of {member_name: output_text}.

    Returns:
        Anonymized outputs keyed by label, plus the bidirectional mapping.
    """
    names = [n.strip() for n in member_names.split(",")]
    raw_outputs = json.loads(outputs)

    mapping = build_anonymization_mapping(names)
    anonymized = anonymize_all_outputs(raw_outputs, mapping)

    return json.dumps({
        "anonymized_outputs": anonymized,
        "mapping": {
            "label_to_member": mapping.label_to_member,
            "member_to_label": mapping.member_to_label,
        },
    }, indent=2)


# ---------------------------------------------------------------------------
# 13. run_enforcement_scan_tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def run_enforcement_scan_tool(
    round2_outputs: str,
    round1_outputs: str | None = None,
) -> str:
    """
    Run the post-Round 2 enforcement scan (STEP 4).

    Checks dissent quota, novelty gate, agreement threshold (>70%),
    evidence label distribution, monoculture detection, and
    anti-recursion rules. Returns any remediation prompts for members
    that need re-prompting.

    Args:
        round2_outputs: JSON string of {member_name: round2_output_text}.
        round1_outputs: JSON string of {member_name: round1_output_text}
                       (required for novelty gate comparison).

    Returns:
        Enforcement scan results with pass/fail for each check and
        any remediation prompts.
    """
    r2 = json.loads(round2_outputs)
    r1 = json.loads(round1_outputs) if round1_outputs else None

    result = run_enforcement_scan(r2, r1)
    return json.dumps(result.model_dump(), indent=2)


# ---------------------------------------------------------------------------
# 14. parse_stances_and_tally
# ---------------------------------------------------------------------------

@mcp.tool()
async def parse_stances_and_tally(
    final_round_outputs: str,
    domain_weight_member: str | None = None,
) -> str:
    """
    Parse STANCE lines and compute the weighted vote tally (STEP 5+6).

    Extracts structured stance lines from each member's final round output,
    normalises option labels, and computes the weighted tally with 2/3
    consensus threshold.

    Args:
        final_round_outputs: JSON string of {member_name: final_output_text}.
        domain_weight_member: The member receiving 1.5× weight (from
                             panel selection). None if no domain-weight seat.

    Returns:
        Parsed stances, any unparseable members (need re-prompting),
        and the complete vote tally.
    """
    outputs = json.loads(final_round_outputs)
    stances, unparseable = parse_all_stances(outputs)

    tally = compute_vote_tally(stances, domain_weight_member)

    return json.dumps({
        "stances": [s.model_dump() for s in stances],
        "unparseable_members": unparseable,
        "vote_tally": tally.model_dump(),
    }, indent=2)


# ---------------------------------------------------------------------------
# 15. generate_chairman_synthesis_prompt
# ---------------------------------------------------------------------------

@mcp.tool()
async def generate_chairman_synthesis_prompt(
    problem: str,
    mode: str,
    round_outputs: str,
    vote_tally: str | None = None,
) -> str:
    """
    Generate the Chairman's synthesis prompt (STEP 7 / Quick 3 / Duo 4).

    Produces the complete prompt for the Chairman to synthesize the
    final verdict, including the full deliberation transcript with
    de-anonymized names, the vote tally, and the verdict template.

    Args:
        problem: The original problem statement.
        mode: "full", "quick", or "duo".
        round_outputs: JSON string of {round_label: {member_name: output_text}}.
        vote_tally: Optional JSON string of the vote tally from
                    parse_stances_and_tally.
    """
    delib_mode = DeliberationMode(mode)
    rounds = json.loads(round_outputs)

    tally = None
    if vote_tally:
        tally_data = json.loads(vote_tally)
        tally = VoteTally(**tally_data)

    prompt = generate_chairman_prompt(
        problem=problem,
        mode=delib_mode,
        round_outputs=rounds,
        vote_tally=tally,
    )
    return json.dumps({"chairman_prompt": prompt}, indent=2)


# ---------------------------------------------------------------------------
# 16. render_verdict
# ---------------------------------------------------------------------------

@mcp.tool()
async def render_verdict(
    mode: str,
    verdict_data: str,
) -> str:
    """
    Render the final verdict from structured data.

    Takes the mode and a JSON object with the verdict fields, and
    produces the formatted markdown verdict using the canonical
    template from SKILL.md.

    Args:
        mode: "full", "quick", or "duo".
        verdict_data: JSON string with the verdict fields matching the
                     template for the given mode.

    Returns:
        Formatted markdown verdict string.
    """
    data = json.loads(verdict_data)
    delib_mode = DeliberationMode(mode)

    metadata = None
    if "session_metadata" in data:
        metadata = SessionMetadata(**data["session_metadata"])

    if delib_mode == DeliberationMode.FULL:
        verdict = render_full_verdict(
            problem=data.get("problem", ""),
            council_composition=data.get("council_composition", ""),
            provider_routing=data.get("provider_routing", ""),
            acceptable_compromises=data.get("acceptable_compromises", ""),
            kill_criteria=data.get("kill_criteria", ""),
            concrete_next_step=data.get("concrete_next_step", ""),
            unresolved_questions=data.get("unresolved_questions", ""),
            recommended_next_steps=data.get("recommended_next_steps", ""),
            consensus=data.get("consensus", ""),
            key_insights=data.get("key_insights"),
            points_of_disagreement=data.get("points_of_disagreement", ""),
            minority_report=data.get("minority_report", ""),
            epistemic_diversity=data.get("epistemic_diversity"),
            session_metadata=metadata,
        )
    elif delib_mode == DeliberationMode.QUICK:
        verdict = render_quick_verdict(
            problem=data.get("problem", ""),
            panel=data.get("panel", ""),
            recommended_action=data.get("recommended_action", ""),
            kill_criteria=data.get("kill_criteria", ""),
            concrete_next_step=data.get("concrete_next_step", ""),
            acceptable_compromises=data.get("acceptable_compromises", ""),
            positions=data.get("positions"),
            consensus=data.get("consensus", ""),
            key_disagreement=data.get("key_disagreement", ""),
            session_metadata=metadata,
        )
    elif delib_mode == DeliberationMode.DUO:
        verdict = render_duo_verdict(
            problem=data.get("problem", ""),
            member_a=data.get("member_a", ""),
            member_a_lens=data.get("member_a_lens", ""),
            member_b=data.get("member_b", ""),
            member_b_lens=data.get("member_b_lens", ""),
            what_this_means=data.get("what_this_means", ""),
            position_a=data.get("position_a", ""),
            position_b=data.get("position_b", ""),
            where_they_agree=data.get("where_they_agree", ""),
            core_tension=data.get("core_tension", ""),
            concrete_next_step=data.get("concrete_next_step", ""),
            kill_criteria=data.get("kill_criteria", ""),
            session_metadata=metadata,
        )
    else:
        return json.dumps({"error": f"Unknown mode '{mode}'."})

    return verdict


# ---------------------------------------------------------------------------
# 17. validate_panel
# ---------------------------------------------------------------------------

@mcp.tool()
async def validate_panel(member_names: str) -> str:
    """
    Validate a custom member panel for correctness.

    Checks member existence, count limits (2-18), duplicates, and
    identifies active polarity pairs. Returns warnings for panels
    without natural tensions.

    Args:
        member_names: Comma-separated member short names.
    """
    names = [n.strip() for n in member_names.split(",")]
    result = _registry.validate_panel(names)
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# 18. get_deliberation_protocol
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_deliberation_protocol(mode: str = "full") -> str:
    """
    Get the complete step-by-step deliberation protocol for a given mode.

    Returns the full protocol specification including all steps,
    prompt templates, enforcement rules, and the verdict template.
    Useful for understanding the deliberation flow before running one.

    Args:
        mode: "full", "quick", or "duo".
    """
    delib_mode = DeliberationMode(mode)
    template = get_verdict_template(delib_mode)

    protocols = {
        DeliberationMode.FULL: {
            "mode": "full",
            "description": (
                "3-round structured deliberation: independent analysis → "
                "cross-examination → final positions."
            ),
            "steps": [
                {"step": "0", "name": "Parse Mode and Select Panel",
                 "description": "Determine mode, select panel members, designate domain-weight seat (1.5×)."},
                {"step": "1", "name": "Provider Detection & Routing",
                 "description": "Auto-detect providers, assign members to providers (polarity separation, spread, affinity, tier matching)."},
                {"step": "1.5", "name": "Problem Restate Gate",
                 "description": "Each member restates the problem in TWO parts before analysis. Catches wrong-question failures."},
                {"step": "1.7", "name": "Chairman Selection",
                 "description": "Select the Chairman (synthesizer, does NOT deliberate). Highest-tier non-panel provider preferred."},
                {"step": "2", "name": "Round 1 — Independent Analysis (PARALLEL, BLIND-FIRST)",
                 "description": "All members analyze in parallel. Each sees only the problem + restatements. 400 words max."},
                {"step": "3", "name": "Round 2 — Cross-Examination (ANONYMIZED)",
                 "description": "Members challenge each other's anonymized Round 1 outputs. Anti-conformity directive. 300 words max."},
                {"step": "4", "name": "Post-Round Enforcement Scan",
                 "description": "Single-pass enforcement: dissent quota, novelty gate, agreement check (>70%), evidence labels, anti-recursion."},
                {"step": "5", "name": "Round 3 — Final Crystallization (PARALLEL)",
                 "description": "100-word position statements + structured STANCE line. Socrates gets ONE question."},
                {"step": "6", "name": "Tie-Breaking",
                 "description": "Weighted vote tally: W_option ≥ (2/3) × W_total. Domain-weight seat = 1.5×. No forced consensus."},
                {"step": "7", "name": "Synthesize Verdict (CHAIRMAN)",
                 "description": "Chairman synthesizes the final verdict from the full transcript. Leads with Unresolved Questions."},
                {"step": "8", "name": "Append Session Metadata",
                 "description": "Append schema_version 1 telemetry block to the verdict."},
            ],
            "rounds": 3,
            "word_limits": {
                "restate": 50,
                "round1": 400,
                "round2": 300,
                "round3": 100,
            },
            "enforcement": {
                "dissent_quota": "≥2 members must articulate non-overlapping objections.",
                "novelty_gate": "Each R2 response must have ≥1 new claim vs R1.",
                "agreement_check": ">70% agreement triggers counterfactual prompt to 2 dissenters.",
                "evidence_labels": "Claims tagged: empirical | mechanistic | strategic | ethical | heuristic.",
                "anti_recursion": "Socrates hemlock rule (3-level depth limit, 1 question in R3).",
            },
        },
        DeliberationMode.QUICK: {
            "mode": "quick",
            "description": (
                "2-round rapid analysis for simpler decisions. "
                "No cross-examination."
            ),
            "steps": [
                {"step": "0", "name": "Select Panel", "description": "Same as full mode."},
                {"step": "0.5", "name": "Problem Restate Gate", "description": "Embedded in Round 1 prompt."},
                {"step": "1", "name": "Round 1 — Rapid Analysis (PARALLEL)", "description": "Restate + condensed analysis. 200 words max."},
                {"step": "2", "name": "Round 2 — Final Positions (PARALLEL, ANONYMIZED)", "description": "Anonymized, anti-conformity. 75 words max + STANCE line."},
                {"step": "3", "name": "Synthesize Quick Verdict (CHAIRMAN)", "description": "Chairman produces Quick Verdict."},
            ],
            "rounds": 2,
            "word_limits": {"round1": 200, "round2": 75},
        },
        DeliberationMode.DUO: {
            "mode": "duo",
            "description": (
                "2-member dialectic for rapid opposing perspectives. "
                "No anonymization (identity is known)."
            ),
            "steps": [
                {"step": "0", "name": "Select Pair", "description": "Match problem to duo polarity pairs table. Default: Socrates vs Feynman."},
                {"step": "0.5", "name": "Problem Restate Gate", "description": "Embedded in Round 1 prompt."},
                {"step": "1", "name": "Round 1 — Opening Positions (PARALLEL)", "description": "Each member states position. 300 words max."},
                {"step": "2", "name": "Round 2 — Direct Response (PARALLEL)", "description": "Each responds to opponent. Anti-conformity. 200 words max."},
                {"step": "3", "name": "Round 3 — Final Statements (PARALLEL)", "description": "50 words max. No new arguments."},
                {"step": "4", "name": "Synthesize Duo Verdict (CHAIRMAN)", "description": "Chairman produces Duo Verdict. Must NOT be either duo member."},
            ],
            "rounds": 3,
            "word_limits": {"round1": 300, "round2": 200, "round3": 50},
        },
    }

    protocol = protocols.get(delib_mode, protocols[DeliberationMode.FULL])
    protocol["verdict_template"] = template

    return json.dumps(protocol, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# RESOURCES — 5 resources for static/semi-static content
# ═══════════════════════════════════════════════════════════════════════════


@mcp.resource("council://overview")
async def council_overview() -> str:
    """Project description, philosophy, and how the council works."""
    return (
        "# Council of High Intelligence (CoHI)\n\n"
        "18 AI personas deliberate your hardest decisions across multiple "
        "LLM providers through structured multi-round protocols.\n\n"
        "## Why This Works\n\n"
        "A single LLM gives you one reasoning path dressed up as confidence. "
        "The council gives you structured disagreement instead:\n\n"
        "- **Genuinely different perspectives** — polarity pairs force real tension\n"
        "- **Catch wrong questions early** — Problem Restate Gate\n"
        "- **Know what the council can't answer** — verdicts lead with "
        "Unresolved Questions\n"
        "- **Prevent groupthink** — dissent quotas, novelty gates, "
        "counterfactual prompts\n\n"
        "## Three Modes\n\n"
        "- **Full mode**: 3-round structured deliberation (all 18 or triad)\n"
        "- **Quick mode**: 2-round rapid analysis, no cross-examination\n"
        "- **Duo mode**: 2-member dialectic using polarity pairs\n\n"
        "## Supported Providers\n\n"
        "Anthropic (Claude), OpenAI (Codex), Google (Agy), Ollama, "
        "NVIDIA NIM, Cursor CLI\n\n"
        "## MCP Tools Available\n\n"
        "This server exposes 18 tools covering panel selection, provider "
        "detection, routing, prompt generation, enforcement, vote tallying, "
        "chairman selection, and verdict rendering."
    )


@mcp.resource("council://members")
async def council_members_resource() -> str:
    """All 18 council members as structured JSON data."""
    return await list_members()


@mcp.resource("council://config/routing")
async def routing_config_resource() -> str:
    """Current auto-route-defaults.yaml content."""
    try:
        config = load_auto_route_defaults()
        return json.dumps(config, indent=2, default=str)
    except FileNotFoundError:
        return json.dumps({"error": "auto-route-defaults.yaml not found."})


@mcp.resource("council://protocol/{mode}")
async def protocol_resource(mode: str) -> str:
    """Full protocol specification for each deliberation mode."""
    return await get_deliberation_protocol(mode)


@mcp.resource("council://demos")
async def demos_resource() -> str:
    """Demo session pack with copy-paste prompts and expected outputs."""
    try:
        root = resolve_project_root()
        demos_path = root / "demos" / "session-pack.md"
        if demos_path.is_file():
            return demos_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        pass
    return (
        "# Demo Session Pack\n\n"
        "Demo session pack file not found. Check your installation.\n\n"
        "Example prompts:\n\n"
        "```\n"
        "Full mode:  /council --triad strategy Should we open-source our agent framework?\n"
        "Quick mode: /council --quick Should we add caching here?\n"
        "Duo mode:   /council --duo Should we use microservices or monolith?\n"
        "```"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    transport = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]

    mcp.run(transport=transport)