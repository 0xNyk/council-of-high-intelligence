"""
Council of High Intelligence — Deliberation Engine.

Generates the structured prompts for every round of every deliberation
mode (full / quick / duo), handles Round 2 anonymization, runs the
post-round enforcement scan, parses STANCE lines, and computes the
weighted vote tally.

This module does **not** execute LLM calls — it produces the prompts
and protocol artefacts that an MCP client uses to orchestrate the
actual calls.
"""

from __future__ import annotations

import re
import string
from typing import Any, Optional

from .council_registry import CouncilRegistry
from .models import (
    AnonymizationMapping,
    ChairmanSelection,
    Confidence,
    CouncilMember,
    DeliberationMode,
    EnforcementResult,
    RoundName,
    RoundPrompt,
    RoutingSlot,
    RoutingTable,
    SessionMetadata,
    StanceLine,
    VoteOption,
    VoteTally,
)

# ---------------------------------------------------------------------------
# Identity inlining helper
# ---------------------------------------------------------------------------


def _build_identity_preamble(member: CouncilMember) -> str:
    """
    Build a self-contained identity preamble for non-subagent providers.

    Extracts *Identity*, *Grounding Protocol*, and *Output Format* sections
    from the member profile so the prompt works on any LLM without
    requiring access to agent ``.md`` files.
    """
    parts = [f"## Identity\n\n{member.identity}"]
    if member.grounding_protocol:
        parts.append(f"## Grounding Protocol\n\n{member.grounding_protocol}")
    if member.output_format_standalone:
        parts.append(
            f"## Output Format (Standalone)\n\n{member.output_format_standalone}"
        )
    if member.output_format_round2:
        parts.append(
            f"## Output Format (Council Round 2)\n\n{member.output_format_round2}"
        )
    return "\n\n".join(parts)


def _build_prompt_for_member(
    member: CouncilMember,
    routing_table: RoutingTable,
    body: str,
) -> RoundPrompt:
    """
    Wrap a prompt body into a ``RoundPrompt`` with identity and routing info.
    """
    slot = routing_table.get_slot(member.short_name)
    exec_method = slot.exec_method if slot else "subagent"
    model = slot.model if slot else member.model_tier
    timeout = slot.timeout_seconds if slot else 60

    preamble = _build_identity_preamble(member)

    full_prompt = (
        f"You are operating as a council member in a structured deliberation.\n\n"
        f"{preamble}\n\n"
        f"{body}"
    )

    return RoundPrompt(
        member_name=member.short_name,
        prompt_text=full_prompt,
        exec_method=exec_method,
        model=model,
        timeout_seconds=timeout,
        identity_preamble=preamble,
    )


# ---------------------------------------------------------------------------
# Anonymization (STEP 3 / Quick STEP 2)
# ---------------------------------------------------------------------------

_LABELS = list(string.ascii_uppercase)  # A, B, C, …, Z


def build_anonymization_mapping(
    member_names: list[str],
) -> AnonymizationMapping:
    """
    Create a stable label mapping: Member A → first member, etc.

    The order follows the panel order as given.
    """
    label_to_member: dict[str, str] = {}
    member_to_label: dict[str, str] = {}
    for idx, name in enumerate(member_names):
        label = f"Member {_LABELS[idx]}" if idx < 26 else f"Member {idx + 1}"
        label_to_member[label] = name
        member_to_label[name] = label
    return AnonymizationMapping(
        label_to_member=label_to_member,
        member_to_label=member_to_label,
    )


def anonymize_output(
    text: str,
    real_name: str,
    mapping: AnonymizationMapping,
) -> str:
    """
    Strip a member's identity from their Round 1 output.

    - Replaces self-references (e.g. "As Socrates, I…") with the
      anonymized label.
    - Replaces other member names with their labels.
    """
    result = text
    for member_name, label in mapping.member_to_label.items():
        # Case-insensitive replacement of member names
        pattern = re.compile(re.escape(member_name), re.IGNORECASE)
        result = pattern.sub(label, result)
        # Also handle "council-{name}" references
        full_pattern = re.compile(
            rf"council-{re.escape(member_name)}", re.IGNORECASE
        )
        result = full_pattern.sub(label, result)
    return result


def anonymize_all_outputs(
    outputs: dict[str, str],
    mapping: AnonymizationMapping,
) -> dict[str, str]:
    """
    Anonymize all Round 1 outputs using the given mapping.

    Returns a dict of ``{label: anonymized_text}``.
    """
    anonymized: dict[str, str] = {}
    for member_name, text in outputs.items():
        label = mapping.member_to_label.get(member_name, member_name)
        anonymized[label] = anonymize_output(text, member_name, mapping)
    return anonymized


# ---------------------------------------------------------------------------
# Prompt generation: FULL MODE
# ---------------------------------------------------------------------------


def generate_restate_prompts(
    members: list[CouncilMember],
    problem: str,
    routing_table: RoutingTable,
) -> list[RoundPrompt]:
    """
    Generate Problem Restate Gate prompts (STEP 1.5).

    Each member restates the problem in TWO parts before analysis.
    """
    body = (
        f"The problem under deliberation:\n{problem}\n\n"
        "Before you begin analysis, restate this problem in TWO parts:\n"
        "1. **Your restatement**: One sentence capturing the core question "
        "through your analytical lens.\n"
        "2. **Alternative framing**: One sentence reframing the problem in a "
        "way the original statement may have missed.\n\n"
        "Do NOT begin your analysis yet. Just the restatement and "
        "alternative framing. 50 words maximum total."
    )
    return [
        _build_prompt_for_member(m, routing_table, body) for m in members
    ]


def generate_round1_prompts(
    members: list[CouncilMember],
    problem: str,
    restatements: dict[str, str],
    routing_table: RoutingTable,
) -> list[RoundPrompt]:
    """
    Generate Round 1 — Independent Analysis prompts (STEP 2).

    Blind-first: each member sees only the problem and all restatements.
    """
    restate_block = "\n".join(
        f"- **{name}**: {text}" for name, text in restatements.items()
    )

    body = (
        f"The problem under deliberation:\n{problem}\n\n"
        f"Here is how each member reframed the problem:\n{restate_block}\n\n"
        "Produce your independent analysis using your Output Format "
        "(Standalone).\n"
        "Do NOT try to anticipate what other members will say.\n"
        "Limit: 400 words maximum."
    )
    return [
        _build_prompt_for_member(m, routing_table, body) for m in members
    ]


def generate_round2_prompts(
    members: list[CouncilMember],
    anonymized_outputs: dict[str, str],
    routing_table: RoutingTable,
    batch_a_outputs: dict[str, str] | None = None,
) -> list[RoundPrompt]:
    """
    Generate Round 2 — Cross-Examination prompts (STEP 3).

    Outputs are anonymized. Includes anti-conformity directive.
    """
    analyses_block = "\n\n---\n\n".join(
        f"### {label}\n\n{text}"
        for label, text in anonymized_outputs.items()
    )

    batch_b_block = ""
    if batch_a_outputs:
        batch_b_block = (
            "\n\nHere are Round 2 responses from earlier members "
            "(same labels):\n"
            + "\n\n".join(
                f"### {label}\n\n{text}"
                for label, text in batch_a_outputs.items()
            )
        )

    prompts: list[RoundPrompt] = []
    for member in members:
        body = (
            f"You are council-{member.short_name} in Round 2 of a "
            "structured deliberation.\n\n"
            "**Identity is masked in this round.** The Round 1 analyses "
            "below are labeled Member A, Member B, … — you do not know "
            "which colleague produced which. One of them is your own "
            "Round 1 output (anonymized along with the rest). Evaluate by "
            "argument quality, not by source. Do not try to guess "
            "identities and do not reference any council member by their "
            "real name in this round; use the labels.\n\n"
            f"Here are the (anonymized) Round 1 analyses from all council "
            f"members:\n\n{analyses_block}"
            f"{batch_b_block}\n\n"
            "**Anti-conformity directive.** If your Round 1 position was "
            "correct, defend it. Do not update merely because peers "
            "disagree, because consensus is forming, or because a "
            "position is repeated by multiple members. Update only when "
            "presented with sound, validity-aligned reasoning that exposes "
            "a specific flaw in your earlier argument. Naming that flaw is "
            "required when you update; if you cannot name it, you should "
            "not update.\n\n"
            "Now respond using your Output Format (Council Round 2):\n"
            "1. Which member's position do you most disagree with, and "
            "why? Engage their specific claims. Refer to them as "
            '"Member X".\n'
            "2. Which member's insight strengthens your position? How? "
            'Refer to them as "Member Y".\n'
            "3. Restate your position in light of this exchange, noting "
            "any changes.\n"
            "4. Label your key claims: empirical | mechanistic | "
            "strategic | ethical | heuristic\n\n"
            "Limit: 300 words maximum. You MUST engage at least 2 other "
            "members by label."
        )
        prompts.append(
            _build_prompt_for_member(member, routing_table, body)
        )
    return prompts


def generate_round3_prompts(
    members: list[CouncilMember],
    routing_table: RoutingTable,
) -> list[RoundPrompt]:
    """
    Generate Round 3 — Final Crystallization prompts (STEP 5).
    """
    prompts: list[RoundPrompt] = []
    for member in members:
        socrates_note = ""
        if member.short_name == "socrates":
            socrates_note = (
                "Socrates: you get exactly ONE question. Make it count. "
                "Then state your position.\n"
            )

        body = (
            "Final round. State your position declaratively in 100 words "
            "or less.\n"
            f"{socrates_note}"
            "No new arguments — only crystallization of your stance.\n\n"
            "Then, on the LAST line, emit your structured stance EXACTLY "
            "in this format so the council can tally it:\n"
            "STANCE: <one short option label> | CONFIDENCE: high|med|low "
            "| DEALBREAKER: yes|no\n\n"
            "- STANCE must be a terse label for the option you back "
            '(e.g. "monorepo", "ship now", "do not ship"). Use the SAME '
            "wording as peers where you agree — matching labels are what "
            "make the tally countable. If you genuinely back no option, "
            "write STANCE: abstain.\n"
            "- DEALBREAKER: yes means you consider the opposing option "
            "actively harmful, not merely sub-optimal — surfaced in the "
            "Minority Report even if you're outvoted."
        )
        prompts.append(
            _build_prompt_for_member(member, routing_table, body)
        )
    return prompts


# ---------------------------------------------------------------------------
# Prompt generation: QUICK MODE
# ---------------------------------------------------------------------------


def generate_quick_round1_prompts(
    members: list[CouncilMember],
    problem: str,
    routing_table: RoutingTable,
) -> list[RoundPrompt]:
    """
    Generate Quick Mode Round 1 — Rapid Analysis prompts.

    Combines restate + analysis in one prompt. 200 words maximum.
    """
    body = (
        f"The problem under deliberation:\n{problem}\n\n"
        "First, in ONE sentence, restate this problem through your "
        "analytical lens. Then produce a condensed analysis:\n"
        "- Essential Question (1-2 sentences)\n"
        "- Your core analysis (key insight only)\n"
        "- Verdict (direct recommendation)\n"
        "- Confidence (High/Medium/Low)\n\n"
        "Limit: 200 words maximum. Be decisive."
    )
    return [
        _build_prompt_for_member(m, routing_table, body) for m in members
    ]


def generate_quick_round2_prompts(
    members: list[CouncilMember],
    anonymized_outputs: dict[str, str],
    routing_table: RoutingTable,
) -> list[RoundPrompt]:
    """
    Generate Quick Mode Round 2 — Final Positions prompts.

    Anonymized, with anti-conformity directive. 75 words maximum.
    """
    analyses_block = "\n\n---\n\n".join(
        f"### {label}\n\n{text}"
        for label, text in anonymized_outputs.items()
    )

    prompts: list[RoundPrompt] = []
    for member in members:
        body = (
            "Here are the (anonymized) Round 1 analyses from the other "
            f"members:\n\n{analyses_block}\n\n"
            "**Identity is masked.** Evaluate by argument quality, not by "
            "source. Refer to peers as \"Member X\" — do not use real "
            "council member names in this round.\n\n"
            "**Anti-conformity directive.** If your Round 1 position was "
            "correct, defend it. Do not update merely because peers "
            "disagree or because consensus is forming. Update only when "
            "presented with sound reasoning that exposes a specific flaw "
            "in your earlier argument; if you cannot name the flaw, do "
            "not update.\n\n"
            "State your final position in 75 words or less. Note any key "
            "disagreement (call out the specific Member whose position "
            "you push back on). Be direct.\n\n"
            "Then, on the LAST line, emit your structured stance EXACTLY "
            "in this format:\n"
            "STANCE: <one short option label> | CONFIDENCE: high|med|low "
            "| DEALBREAKER: yes|no\n"
            "Use the SAME label as peers where you agree; write "
            "STANCE: abstain if you back no option."
        )
        prompts.append(
            _build_prompt_for_member(member, routing_table, body)
        )
    return prompts


# ---------------------------------------------------------------------------
# Prompt generation: DUO MODE
# ---------------------------------------------------------------------------


def generate_duo_round1_prompts(
    member_a: CouncilMember,
    member_b: CouncilMember,
    problem: str,
    routing_table: RoutingTable,
) -> list[RoundPrompt]:
    """
    Generate Duo Mode Round 1 — Opening Positions prompts.

    300 words maximum, includes problem restatement.
    """
    body = (
        "You are operating as one half of a structured dialectic with "
        "one opponent.\n\n"
        f"The problem under deliberation:\n{problem}\n\n"
        "First, in ONE sentence, restate this problem through your "
        "analytical lens. Then state your position using your "
        "Output Format (Standalone).\n"
        "Limit: 300 words maximum."
    )
    return [
        _build_prompt_for_member(member_a, routing_table, body),
        _build_prompt_for_member(member_b, routing_table, body),
    ]


def generate_duo_round2_prompts(
    member_a: CouncilMember,
    member_b: CouncilMember,
    output_a: str,
    output_b: str,
    routing_table: RoutingTable,
) -> list[RoundPrompt]:
    """
    Generate Duo Mode Round 2 — Direct Response prompts.

    No anonymization in duo mode. 200 words maximum.
    """
    def _make_body(opponent_name: str, opponent_output: str) -> str:
        return (
            f"Your opponent ({opponent_name}) argued:\n\n"
            f"{opponent_output}\n\n"
            "**Anti-conformity directive.** If your Round 1 position was "
            "correct, defend it. Concede only what is specifically and "
            "validly disproved — not what merely sounds forceful. Name "
            "the flaw in your earlier argument when conceding; if you "
            "cannot name it, the concession is not warranted.\n\n"
            "Respond directly:\n"
            "1. Where are they wrong? Engage their specific claims.\n"
            "2. Where are they right? Concede what deserves conceding.\n"
            "3. Restate your position, strengthened by this exchange.\n\n"
            "Limit: 200 words maximum."
        )

    return [
        _build_prompt_for_member(
            member_a,
            routing_table,
            _make_body(member_b.council.figure, output_b),
        ),
        _build_prompt_for_member(
            member_b,
            routing_table,
            _make_body(member_a.council.figure, output_a),
        ),
    ]


def generate_duo_round3_prompts(
    member_a: CouncilMember,
    member_b: CouncilMember,
    routing_table: RoutingTable,
) -> list[RoundPrompt]:
    """
    Generate Duo Mode Round 3 — Final Statements prompts.

    50 words maximum. No new arguments.
    """
    body = (
        "Final statement. 50 words maximum. State your position. "
        "No new arguments."
    )
    return [
        _build_prompt_for_member(member_a, routing_table, body),
        _build_prompt_for_member(member_b, routing_table, body),
    ]


# ---------------------------------------------------------------------------
# Chairman synthesis prompt
# ---------------------------------------------------------------------------


def generate_chairman_prompt(
    problem: str,
    mode: DeliberationMode,
    round_outputs: dict[str, dict[str, str]],
    vote_tally: VoteTally | None = None,
    chairman: ChairmanSelection | None = None,
    anonymization_mapping: AnonymizationMapping | None = None,
) -> str:
    """
    Generate the Chairman's synthesis prompt (STEP 7 / Quick 3 / Duo 4).

    ``round_outputs`` is keyed by round name (e.g. "round1", "round2",
    "round3") → dict of member_name → output text.

    For full and quick modes, Round 2 outputs should be provided with
    real names restored (de-anonymized for the chairman's audit).
    """
    # Build transcript
    transcript_parts: list[str] = []
    for round_label, outputs in round_outputs.items():
        section = f"### {round_label}\n\n"
        for member, text in outputs.items():
            section += f"**{member}**:\n{text}\n\n"
        transcript_parts.append(section)

    transcript = "\n---\n\n".join(transcript_parts)

    # Vote tally summary
    tally_text = ""
    if vote_tally:
        tally_lines = []
        for opt in vote_tally.options:
            backers = ", ".join(opt.backers)
            dw = ""
            if opt.domain_weight_member:
                dw = f" [{opt.domain_weight_member} 1.5×]"
            tally_lines.append(
                f"  - {opt.label} — {opt.weight} ({backers}{dw})"
            )
        tally_text = (
            f"\n\nVote Tally:\n"
            + "\n".join(tally_lines)
            + f"\n  W_total: {vote_tally.w_total} · "
            f"Threshold: {vote_tally.threshold:.2f} · "
            f"Consensus: {'YES' if vote_tally.consensus_reached else 'NO'}"
        )

    # Mode-specific template name
    template_name = {
        DeliberationMode.FULL: "Council Verdict (Full Mode)",
        DeliberationMode.QUICK: "Quick Verdict",
        DeliberationMode.DUO: "Duo Verdict",
    }.get(mode, "Council Verdict")

    return (
        "You are the Chairman of the Council of High Intelligence. You did "
        "not deliberate in this session — you are the synthesizer.\n\n"
        f"The original problem under deliberation:\n{problem}\n\n"
        "The full deliberation transcript follows. Member names are now "
        "visible (Round 2 was anonymized for the members but the audit "
        "transcript restores real names for synthesis).\n\n"
        f"{transcript}"
        f"{tally_text}\n\n"
        "Your job:\n"
        "- Weigh arguments by validity, not by repetition or seniority.\n"
        "- Surface genuine disagreement; do not invent positions no member "
        "held.\n"
        "- Lead with what the council does NOT know (Unresolved Questions).\n"
        f"- Produce the {template_name} using the standard template. "
        "Do not add, remove, or rename sections. Fill each section "
        'faithfully or write "N/A — {reason}" if the section is genuinely '
        "empty in this session."
    )


# ---------------------------------------------------------------------------
# Enforcement scan (STEP 4)
# ---------------------------------------------------------------------------


def run_enforcement_scan(
    round2_outputs: dict[str, str],
    round1_outputs: dict[str, str] | None = None,
    member_names: list[str] | None = None,
) -> EnforcementResult:
    """
    Run all post-Round 2 enforcement checks in a single pass.

    Checks:
      - Dissent quota (≥2 members articulate non-overlapping objections)
      - Novelty gate (each response has ≥1 new claim vs Round 1)
      - Agreement check (>70% convergence triggers counterfactual)
      - Evidence labels (confirm tagging, detect monoculture)
      - Anti-recursion (Socrates re-asking, pair message limit)

    Returns an ``EnforcementResult`` with scan findings and any
    remediation prompts.
    """
    all_members = member_names or list(round2_outputs.keys())
    remediation: dict[str, str] = {}

    # --- Dissent quota ---
    dissent_members: list[str] = []
    disagree_pattern = re.compile(
        r"(?:disagree|challenge|wrong|flawed|reject|object)", re.IGNORECASE
    )
    for member, text in round2_outputs.items():
        if disagree_pattern.search(text):
            dissent_members.append(member)
    dissent_met = len(dissent_members) >= 2

    if not dissent_met:
        # Pick members who agreed too readily
        agreeing = [m for m in all_members if m not in dissent_members]
        for member in agreeing[:2]:
            remediation[member] = (
                "Your Round 2 response agreed with the emerging consensus. "
                "The council requires dissent for quality.\n"
                "State your strongest objection to the majority position "
                "in 150 words. What are they getting wrong?"
            )

    # --- Novelty gate ---
    novelty_passed: dict[str, bool] = {}
    if round1_outputs:
        for member in all_members:
            r1 = round1_outputs.get(member, "")
            r2 = round2_outputs.get(member, "")
            # Simple heuristic: check if R2 has substantial content
            # not present in R1 (word-level set difference)
            r1_words = set(r1.lower().split())
            r2_words = set(r2.lower().split())
            new_words = r2_words - r1_words
            # At least 10% new content is a reasonable novelty signal
            novelty_passed[member] = len(new_words) > max(5, len(r2_words) * 0.1)

            if not novelty_passed[member] and member not in remediation:
                remediation[member] = (
                    "Your Round 2 response restated your Round 1 position "
                    "without engaging the challenges raised.\n"
                    "Address the challenges to your position directly. "
                    "What changes?"
                )
    else:
        novelty_passed = {m: True for m in all_members}

    # --- Agreement check ---
    # Heuristic: look for convergent language
    positions: list[str] = []
    for text in round2_outputs.values():
        # Extract the Position Update section if present
        pos_match = re.search(
            r"(?:position update|restated? (?:my )?position)(.*?)(?:###|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        positions.append(
            pos_match.group(1).strip() if pos_match else text[:200]
        )

    # Simple agreement ratio: fraction of members whose position update
    # contains similar key terms
    agreement_ratio = 0.0
    if len(positions) >= 2:
        # Use word overlap between all pairs
        total_pairs = 0
        agreement_sum = 0.0
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                w_i = set(positions[i].lower().split())
                w_j = set(positions[j].lower().split())
                if w_i and w_j:
                    overlap = len(w_i & w_j) / min(len(w_i), len(w_j))
                    agreement_sum += overlap
                total_pairs += 1
        if total_pairs > 0:
            agreement_ratio = agreement_sum / total_pairs

    agreement_exceeded = agreement_ratio > 0.70

    if agreement_exceeded:
        # Trigger counterfactual for 2 most-likely dissenters
        for member in dissent_members[:2] or all_members[:2]:
            if member not in remediation:
                remediation[member] = (
                    "Assume the current consensus is wrong. What is the "
                    "strongest alternative and what evidence would flip "
                    "the decision?"
                )

    # --- Evidence labels ---
    label_pattern = re.compile(
        r"\b(empirical|mechanistic|strategic|ethical|heuristic)\b",
        re.IGNORECASE,
    )
    evidence_labels: dict[str, list[str]] = {}
    all_labels: list[str] = []
    for member, text in round2_outputs.items():
        found = [m.group(1).lower() for m in label_pattern.finditer(text)]
        evidence_labels[member] = found
        all_labels.extend(found)

    monoculture = False
    if all_labels:
        from collections import Counter

        counts = Counter(all_labels)
        most_common_pct = counts.most_common(1)[0][1] / len(all_labels)
        monoculture = most_common_pct > 0.80

    # --- Anti-recursion ---
    anti_recursion: list[str] = []
    if "socrates" in round2_outputs:
        # Check for repeated questioning without position
        socrates_text = round2_outputs["socrates"]
        questions = re.findall(r"\?", socrates_text)
        position_indicators = re.findall(
            r"\b(?:my position|I (?:believe|argue|hold|conclude))\b",
            socrates_text,
            re.IGNORECASE,
        )
        if len(questions) > 4 and len(position_indicators) == 0:
            anti_recursion.append("socrates")
            remediation["socrates"] = (
                "Hemlock rule triggered. You must immediately state your "
                "strongest position in 50 words or less."
            )

    return EnforcementResult(
        dissent_quota_met=dissent_met,
        dissent_count=len(dissent_members),
        novelty_gate_passed=novelty_passed,
        agreement_ratio=round(agreement_ratio, 3),
        agreement_threshold_exceeded=agreement_exceeded,
        evidence_labels=evidence_labels,
        evidence_monoculture=monoculture,
        anti_recursion_triggered=anti_recursion,
        remediation_prompts=remediation,
    )


# ---------------------------------------------------------------------------
# Stance parsing & vote tally (STEP 5 + 6)
# ---------------------------------------------------------------------------

_STANCE_RE = re.compile(
    r"STANCE:\s*(?P<stance>[^|]+)"
    r"\s*\|\s*CONFIDENCE:\s*(?P<conf>high|med|low)"
    r"\s*\|\s*DEALBREAKER:\s*(?P<deal>yes|no)",
    re.IGNORECASE,
)


def parse_stance(member_name: str, text: str) -> StanceLine | None:
    """
    Parse a ``STANCE:`` line from a member's final round output.

    Returns *None* if no parseable stance line is found.
    """
    match = _STANCE_RE.search(text)
    if not match:
        return None

    return StanceLine(
        member=member_name,
        stance=match.group("stance").strip().lower(),
        confidence=Confidence(match.group("conf").lower()),
        dealbreaker=match.group("deal").lower() == "yes",
        raw_line=match.group(0),
    )


def parse_all_stances(
    final_outputs: dict[str, str],
) -> tuple[list[StanceLine], list[str]]:
    """
    Parse STANCE lines from all members' final round outputs.

    Returns (parsed_stances, unparseable_member_names).
    """
    stances: list[StanceLine] = []
    unparseable: list[str] = []

    for member_name, text in final_outputs.items():
        stance = parse_stance(member_name, text)
        if stance:
            stances.append(stance)
        else:
            unparseable.append(member_name)

    return stances, unparseable


def compute_vote_tally(
    stances: list[StanceLine],
    domain_weight_member: str | None = None,
    domain_weight_value: float = 1.5,
) -> VoteTally:
    """
    Compute the weighted vote tally (STEP 6).

    Rules:
    - Each member contributes weight 1.0.
    - The domain-weight seat contributes ``domain_weight_value`` (default 1.5).
    - ``abstain`` stances count toward W_total but no option.
    - Consensus requires ``W_option ≥ (2/3) × W_total``.
    """
    # Compute per-member weights
    member_weight: dict[str, float] = {}
    for stance in stances:
        weight = (
            domain_weight_value
            if stance.member == domain_weight_member
            else 1.0
        )
        member_weight[stance.member] = weight

    w_total = sum(member_weight.values())
    threshold = (2.0 / 3.0) * w_total

    # Tally by option
    option_data: dict[str, VoteOption] = {}
    for stance in stances:
        if stance.stance == "abstain":
            continue
        label = stance.stance
        if label not in option_data:
            option_data[label] = VoteOption(label=label)
        opt = option_data[label]
        opt.weight += member_weight[stance.member]
        opt.backers.append(stance.member)
        if stance.member == domain_weight_member:
            opt.domain_weight_member = stance.member

    # Sort options by weight descending
    sorted_options = sorted(
        option_data.values(), key=lambda o: o.weight, reverse=True
    )

    # Consensus test
    consensus_option: str | None = None
    consensus_reached = False
    if sorted_options and sorted_options[0].weight >= threshold:
        consensus_option = sorted_options[0].label
        consensus_reached = True

    return VoteTally(
        options=sorted_options,
        w_total=w_total,
        threshold=threshold,
        consensus_option=consensus_option,
        consensus_reached=consensus_reached,
        domain_weight_member=domain_weight_member,
        domain_weight_value=domain_weight_value,
    )
