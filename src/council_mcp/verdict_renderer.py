"""
Council of High Intelligence — Verdict Renderer.

Renders structured verdict outputs using the canonical templates from
SKILL.md for Full, Quick, and Duo modes, plus the Session Metadata block.
"""

from __future__ import annotations

from typing import Any, Optional

from .models import (
    ChairmanSelection,
    DeliberationMode,
    SessionMetadata,
    VoteTally,
)


def render_full_verdict(
    *,
    problem: str,
    council_composition: str,
    chairman: ChairmanSelection | None = None,
    provider_routing: str = "Default models (single provider).",
    acceptable_compromises: str = "",
    kill_criteria: str = "",
    concrete_next_step: str = "",
    unresolved_questions: str = "",
    recommended_next_steps: str = "",
    consensus: str = "",
    vote_tally: VoteTally | None = None,
    key_insights: dict[str, str] | None = None,
    points_of_disagreement: str = "",
    minority_report: str = "",
    epistemic_diversity: dict[str, Any] | None = None,
    session_metadata: SessionMetadata | None = None,
) -> str:
    """Render the full Council Verdict template."""
    chairman_text = _render_chairman(chairman)
    tally_text = _render_vote_tally(vote_tally) if vote_tally else "N/A"
    insights_text = _render_key_insights(key_insights)
    diversity_text = _render_epistemic_diversity(epistemic_diversity)
    metadata_text = (
        render_session_metadata(session_metadata) if session_metadata else ""
    )

    return f"""## Council Verdict

### Problem
{problem}

### Council Composition
{council_composition}

### Chairman
{chairman_text}

### Provider Routing
{provider_routing}

### Acceptable Compromises
{acceptable_compromises or 'N/A — no significant trade-offs identified.'}

### Kill Criteria
{kill_criteria or 'N/A — no kill criteria defined.'}

### Concrete Next Step
{concrete_next_step or 'N/A — pending council deliberation.'}

### Unresolved Questions
{unresolved_questions or 'None identified.'}

### Recommended Next Steps
{recommended_next_steps or 'N/A — see Concrete Next Step.'}

### Consensus & Agreement
{consensus or 'Pending deliberation.'}

### Vote Tally
{tally_text}

### Key Insights by Member
{insights_text}

### Points of Disagreement
{points_of_disagreement or 'None identified.'}

### Minority Report
{minority_report or 'No dissenting positions with DEALBREAKER: yes.'}

### Epistemic Diversity Scorecard
{diversity_text}

### Follow-Up
After acting on this verdict, revisit: Was this verdict useful? Was the recommended action taken? What happened?

{metadata_text}"""


def render_quick_verdict(
    *,
    problem: str,
    panel: str,
    chairman: ChairmanSelection | None = None,
    recommended_action: str = "",
    kill_criteria: str = "",
    concrete_next_step: str = "",
    acceptable_compromises: str = "",
    positions: dict[str, str] | None = None,
    consensus: str = "",
    vote_tally: VoteTally | None = None,
    key_disagreement: str = "",
    session_metadata: SessionMetadata | None = None,
) -> str:
    """Render the Quick Verdict template."""
    chairman_text = _render_chairman(chairman)
    tally_text = _render_vote_tally(vote_tally) if vote_tally else "N/A"
    positions_text = _render_positions(positions)
    metadata_text = (
        render_session_metadata(session_metadata) if session_metadata else ""
    )

    compromises_section = ""
    if acceptable_compromises:
        compromises_section = (
            f"\n### Acceptable Compromises (optional)\n{acceptable_compromises}\n"
        )

    return f"""## Quick Council Verdict

### Problem
{problem}

### Panel
{panel}

### Chairman
{chairman_text}

### Recommended Action
{recommended_action or 'Pending deliberation.'}

### Kill Criteria
{kill_criteria or 'N/A'}

### Concrete Next Step
{concrete_next_step or 'N/A'}
{compromises_section}
### Positions
{positions_text}

### Consensus
{consensus or 'Pending deliberation.'}

### Vote Tally
{tally_text}

### Key Disagreement
{key_disagreement or 'None identified.'}

### Follow-Up
After acting on this verdict, revisit: Was this useful? What happened?

{metadata_text}"""


def render_duo_verdict(
    *,
    problem: str,
    member_a: str,
    member_a_lens: str,
    member_b: str,
    member_b_lens: str,
    chairman: ChairmanSelection | None = None,
    what_this_means: str = "",
    position_a: str = "",
    position_b: str = "",
    where_they_agree: str = "",
    core_tension: str = "",
    concrete_next_step: str = "",
    kill_criteria: str = "",
    session_metadata: SessionMetadata | None = None,
) -> str:
    """Render the Duo Verdict template."""
    chairman_text = _render_chairman(chairman)
    metadata_text = (
        render_session_metadata(session_metadata) if session_metadata else ""
    )

    kill_section = ""
    if kill_criteria:
        kill_section = (
            f"\n### Kill Criteria (encouraged)\n{kill_criteria}\n"
        )

    return f"""## Duo Verdict

### Problem
{problem}

### The Dialectic
**{member_a}** ({member_a_lens}) vs **{member_b}** ({member_b_lens})

### Chairman
{chairman_text}

### What This Means for Your Decision
{what_this_means or 'Pending dialectic.'}

### {member_a}'s Position
{position_a or 'Pending deliberation.'}

### {member_b}'s Position
{position_b or 'Pending deliberation.'}

### Where They Agree
{where_they_agree or 'No convergence identified.'}

### The Core Tension
{core_tension or 'Pending dialectic.'}

### Concrete Next Step
{concrete_next_step or 'N/A'}
{kill_section}
### Follow-Up
After deciding, revisit: Which perspective proved more useful? What happened?

{metadata_text}"""


# ---------------------------------------------------------------------------
# Verdict template (blank) retrieval
# ---------------------------------------------------------------------------


def get_verdict_template(mode: DeliberationMode) -> str:
    """
    Return the blank verdict template for a given mode.

    Useful for clients that want to see the expected output structure
    before running a deliberation.
    """
    templates = {
        DeliberationMode.FULL: _FULL_TEMPLATE,
        DeliberationMode.QUICK: _QUICK_TEMPLATE,
        DeliberationMode.DUO: _DUO_TEMPLATE,
    }
    return templates.get(mode, _FULL_TEMPLATE)


# ---------------------------------------------------------------------------
# Session Metadata rendering
# ---------------------------------------------------------------------------


def render_session_metadata(metadata: SessionMetadata) -> str:
    """Render the Session Metadata block appended to every verdict."""
    fallbacks = (
        "\n".join(f"  - {f}" for f in metadata.fallbacks_triggered)
        if metadata.fallbacks_triggered
        else "none"
    )

    return f"""---

### Session Metadata
```
schema_version: {metadata.schema_version}
mode: {metadata.mode}
panel_size: {metadata.panel_size}
rounds_run: {metadata.rounds_run}
chairman_failed_fallback: {'yes' if metadata.chairman_failed_fallback else 'no'}
tools_used: {'yes' if metadata.tools_used else 'no'}
input_tokens_estimate: {metadata.input_tokens_estimate or '~unknown'}
output_tokens_estimate: {metadata.output_tokens_estimate or '~unknown'}
duration_seconds: {metadata.duration_seconds or '~unknown'}
provider_count: {metadata.provider_count}
fallbacks_triggered: {fallbacks}
```"""


# ---------------------------------------------------------------------------
# Internal renderers
# ---------------------------------------------------------------------------


def _render_chairman(chairman: ChairmanSelection | None) -> str:
    if not chairman:
        return "N/A — chairman not selected."
    return (
        f"Chairman: {chairman.name} ({chairman.provider} · {chairman.model}). "
        f"Selection rationale: {chairman.rationale}"
    )


def _render_vote_tally(tally: VoteTally) -> str:
    if not tally.options:
        return "No votes recorded."

    lines: list[str] = []
    for opt in tally.options:
        backers_str = ", ".join(opt.backers)
        dw_mark = ""
        if opt.domain_weight_member:
            dw_mark = f" [{opt.domain_weight_member} 1.5×, domain]"
        cleared = "✅" if opt.weight >= tally.threshold else ""
        lines.append(
            f"- `{opt.label}` — {opt.weight} ({backers_str}{dw_mark}) "
            f"{cleared}"
        )

    consensus_line = (
        f"**{tally.consensus_option} carries**"
        if tally.consensus_reached
        else "**No option cleared threshold → escalated to user**"
    )

    lines.append(
        f"- W_total {tally.w_total} · threshold {tally.threshold:.3f} · "
        f"{consensus_line}"
    )
    return "\n".join(lines)


def _render_key_insights(insights: dict[str, str] | None) -> str:
    if not insights:
        return "N/A — pending deliberation."
    return "\n".join(
        f"- **{name}**: {text}" for name, text in insights.items()
    )


def _render_positions(positions: dict[str, str] | None) -> str:
    if not positions:
        return "N/A — pending deliberation."
    return "\n".join(
        f"- **{name}**: {text}" for name, text in positions.items()
    )


def _render_epistemic_diversity(data: dict[str, Any] | None) -> str:
    if not data:
        return (
            "- Perspective spread (1-5): ~pending\n"
            "- Provider spread (1-5): ~pending\n"
            "- Evidence mix: ~pending\n"
            "- Convergence risk: ~pending"
        )
    return "\n".join(f"- {k}: {v}" for k, v in data.items())


# ---------------------------------------------------------------------------
# Blank templates (canonical from SKILL.md)
# ---------------------------------------------------------------------------

_FULL_TEMPLATE = """## Council Verdict

### Problem
{Original problem statement}

### Council Composition
{Members convened, mode used, and selection rationale}

### Chairman
{Chairman: <name> (<provider> · <model>). Selection rationale.}

### Provider Routing
{Routing table: member → provider → model. Note any fallbacks triggered.}

### Acceptable Compromises
{What this verdict gives up, named explicitly.}

### Kill Criteria
{Observable conditions that would falsify this verdict. Format: "If <X> observed by <date>, the verdict is invalidated and we should <Y>."}

### Concrete Next Step
{Exactly one action. Format: "<verb> <object> by <date>."}

### Unresolved Questions
{Questions the council could not answer.}

### Recommended Next Steps
{Additional concrete actions beyond the Concrete Next Step.}

### Consensus & Agreement
{The position that survived deliberation — or "No consensus reached".}

### Vote Tally
{Weighted tally: option → weight (backers). Threshold and result.}

### Key Insights by Member
- **{Name}**: {Their most valuable contribution}
- ...

### Points of Disagreement
{Where positions remained irreconcilable}

### Minority Report
{Dissenting positions with DEALBREAKER: yes}

### Epistemic Diversity Scorecard
- Perspective spread (1-5): {score}
- Provider spread (1-5): {score}
- Evidence mix: {% empirical / mechanistic / strategic / ethical / heuristic}
- Convergence risk: {Low/Medium/High with reason}

### Follow-Up
After acting on this verdict, revisit: Was this verdict useful? Was the recommended action taken? What happened?
"""

_QUICK_TEMPLATE = """## Quick Council Verdict

### Problem
{Original problem statement}

### Panel
{Members and selection rationale}

### Chairman
{Chairman: <name> (<provider> · <model>). Selection rationale.}

### Recommended Action
{Single concrete recommendation}

### Kill Criteria
{Observable conditions that would falsify this verdict.}

### Concrete Next Step
{Exactly one action.}

### Positions
- **{Name}**: {Core position in 1-2 sentences}
- ...

### Consensus
{Majority position or "Split" with explanation}

### Vote Tally
{Weighted tally.}

### Key Disagreement
{The most important point of divergence}

### Follow-Up
After acting on this verdict, revisit: Was this useful? What happened?
"""

_DUO_TEMPLATE = """## Duo Verdict

### Problem
{Original problem statement}

### The Dialectic
**{Member A}** ({their lens}) vs **{Member B}** ({their lens})

### Chairman
{Chairman: <name> (<provider> · <model>). Must not be either duo member.}

### What This Means for Your Decision
{How to use these opposing perspectives — the user decides}

### {Member A}'s Position
{Core argument in 2-3 sentences}

### {Member B}'s Position
{Core argument in 2-3 sentences}

### Where They Agree
{Unexpected convergence, if any}

### The Core Tension
{The irreducible disagreement and what drives it}

### Concrete Next Step
{Exactly one action.}

### Kill Criteria (encouraged)
{Observable conditions that would tip the balance.}

### Follow-Up
After deciding, revisit: Which perspective proved more useful? What happened?
"""
