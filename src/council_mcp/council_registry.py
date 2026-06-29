"""
Council of High Intelligence — Council Registry.

Parses agent ``.md`` files and maintains an in-memory registry of all
18 council members, 20 pre-defined triads, 13 duo polarity pairs,
and 3 council profiles.

Usage::

    registry = CouncilRegistry()          # auto-loads from default path
    registry = CouncilRegistry("/custom/agents/dir")

    member  = registry.get_member("socrates")
    triad   = registry.get_triad("architecture")
    pair    = registry.match_duo_pair("Should we use microservices?")
    profile = registry.get_profile("execution-lean")
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

from .config_loader import resolve_agents_dir
from .models import (
    CouncilMember,
    CouncilMetadata,
    CouncilProfile,
    DuoPair,
    Triad,
)

# ---------------------------------------------------------------------------
# Markdown / YAML parsing helpers
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def _parse_sections(text: str) -> dict[str, str]:
    """
    Split a markdown body into ``{heading: content}`` pairs.

    Only ``##``-level headings are considered section delimiters.
    """
    # Strip frontmatter
    body = _FRONTMATTER_RE.sub("", text).strip()

    sections: dict[str, str] = {}
    headings = list(_HEADING_RE.finditer(body))

    for idx, heading_match in enumerate(headings):
        title = heading_match.group(1).strip()
        start = heading_match.end()
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(body)
        sections[title] = body[start:end].strip()

    return sections


def _normalise_section_key(heading: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r"[^a-z0-9 ]+", "", heading.lower()).strip().replace(" ", "_")


def _section_lookup(sections: dict[str, str], *candidates: str) -> str:
    """
    Return the first matching section value, falling back to ``""``.

    Matching is done on normalised keys so ``"What You See That Others Miss"``
    matches candidate ``"what_you_see_that_others_miss"``.
    """
    normalised = {_normalise_section_key(k): v for k, v in sections.items()}
    for candidate in candidates:
        key = _normalise_section_key(candidate)
        if key in normalised:
            return normalised[key]
    return ""


# ---------------------------------------------------------------------------
# Agent file parser
# ---------------------------------------------------------------------------

def parse_agent_file(path: Path) -> CouncilMember:
    """
    Parse a single council agent ``.md`` file into a ``CouncilMember``.

    The file must contain YAML frontmatter (``---`` delimited) with at
    minimum ``name``, ``description``, ``model``, and a ``council:`` block.
    The markdown body is parsed into named sections by ``##``-level headings.
    """
    text = path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    sections = _parse_sections(text)

    council_raw = fm.get("council", {})
    council = CouncilMetadata(**council_raw)

    return CouncilMember(
        name=fm.get("name", path.stem),
        description=fm.get("description", ""),
        model_tier=fm.get("model", "sonnet"),
        color=fm.get("color", ""),
        tools=fm.get("tools", []),
        council=council,
        identity=_section_lookup(sections, "Identity"),
        grounding_protocol=_section_lookup(
            sections,
            "Grounding Protocol",
            "Grounding Protocol — ANTI-RECURSION (CRITICAL)",
            "Grounding Protocol  ANTIRECURSION CRITICAL",
        ),
        analytical_method=_section_lookup(sections, "Analytical Method"),
        what_you_see=_section_lookup(
            sections,
            "What You See That Others Miss",
        ),
        what_you_miss=_section_lookup(sections, "What You Tend to Miss"),
        when_deliberating=_section_lookup(
            sections,
            "When Deliberating in Council",
        ),
        output_format_round2=_section_lookup(
            sections,
            "Output Format (Council Round 2)",
            "Output Format Council Round 2",
        ),
        output_format_standalone=_section_lookup(
            sections,
            "Output Format (Standalone)",
            "Output Format Standalone",
        ),
    )


# ---------------------------------------------------------------------------
# Static data: Triads, Duo Pairs, Profiles
# ---------------------------------------------------------------------------

_TRIADS: list[Triad] = [
    Triad(domain="architecture", members=["aristotle", "ada", "feynman"],
          rationale="Classify + formalize + simplicity-test"),
    Triad(domain="strategy", members=["sun-tzu", "machiavelli", "aurelius"],
          rationale="Terrain + incentives + moral grounding"),
    Triad(domain="ethics", members=["aurelius", "socrates", "lao-tzu"],
          rationale="Duty + questioning + natural order"),
    Triad(domain="debugging", members=["feynman", "socrates", "ada"],
          rationale="Bottom-up + assumption testing + formal verification"),
    Triad(domain="innovation", members=["ada", "lao-tzu", "aristotle"],
          rationale="Abstraction + emergence + classification"),
    Triad(domain="conflict", members=["socrates", "machiavelli", "aurelius"],
          rationale="Expose + predict + ground"),
    Triad(domain="complexity", members=["lao-tzu", "aristotle", "ada"],
          rationale="Emergence + categories + formalism"),
    Triad(domain="risk", members=["sun-tzu", "aurelius", "feynman"],
          rationale="Threats + resilience + empirical verification"),
    Triad(domain="shipping", members=["torvalds", "musashi", "feynman"],
          rationale="Pragmatism + timing + first-principles"),
    Triad(domain="product", members=["torvalds", "machiavelli", "watts"],
          rationale="Ship it + incentives + reframing"),
    Triad(domain="founder", members=["musashi", "sun-tzu", "torvalds"],
          rationale="Timing + terrain + engineering reality"),
    Triad(domain="ai", members=["karpathy", "sutskever", "ada"],
          rationale="Empirical ML + scaling frontier + formal limits"),
    Triad(domain="ai-product", members=["karpathy", "torvalds", "machiavelli"],
          rationale="ML capability + shipping pragmatism + incentives"),
    Triad(domain="ai-safety", members=["sutskever", "aurelius", "socrates"],
          rationale="Safety frontier + moral clarity + assumption destruction"),
    Triad(domain="decision", members=["kahneman", "munger", "aurelius"],
          rationale="Bias detection + inversion + moral clarity"),
    Triad(domain="systems", members=["meadows", "lao-tzu", "aristotle"],
          rationale="Feedback loops + emergence + categories"),
    Triad(domain="uncertainty", members=["taleb", "sun-tzu", "sutskever"],
          rationale="Tail risk + terrain + scaling frontier"),
    Triad(domain="design", members=["rams", "torvalds", "watts"],
          rationale="User clarity + maintainability + reframing"),
    Triad(domain="economics", members=["munger", "machiavelli", "sun-tzu"],
          rationale="Models + incentives + competition"),
    Triad(domain="bias", members=["kahneman", "socrates", "watts"],
          rationale="Cognitive bias + assumption destruction + frame audit"),
]

_DUO_PAIRS: list[DuoPair] = [
    DuoPair(domain_keywords=["architecture", "structure", "categories"],
            member_a="aristotle", member_b="lao-tzu",
            tension="Classification vs emergence"),
    DuoPair(domain_keywords=["shipping", "execution", "release"],
            member_a="torvalds", member_b="musashi",
            tension="Ship now vs wait for timing"),
    DuoPair(domain_keywords=["strategy", "competition", "market"],
            member_a="sun-tzu", member_b="aurelius",
            tension="External victory vs internal governance"),
    DuoPair(domain_keywords=["formalization", "systems", "abstraction"],
            member_a="ada", member_b="machiavelli",
            tension="Formal purity vs human messiness"),
    DuoPair(domain_keywords=["framing", "purpose", "meaning"],
            member_a="socrates", member_b="watts",
            tension="Destroy assumptions vs dissolve the frame"),
    DuoPair(domain_keywords=["engineering", "theory", "pragmatism"],
            member_a="torvalds", member_b="watts",
            tension="Build it vs question if it should exist"),
    DuoPair(domain_keywords=["ai", "ml", "neural", "model", "training"],
            member_a="karpathy", member_b="sutskever",
            tension="Build and iterate vs pause and ensure safety"),
    DuoPair(domain_keywords=["ai-safety", "alignment", "risk"],
            member_a="sutskever", member_b="machiavelli",
            tension="Safety ideals vs industry incentives"),
    DuoPair(domain_keywords=["decision", "bias", "thinking", "judgment"],
            member_a="kahneman", member_b="feynman",
            tension="Your cognition is the error vs trust first-principles"),
    DuoPair(domain_keywords=["systems", "feedback", "complexity", "loops"],
            member_a="meadows", member_b="torvalds",
            tension="Redesign the system vs fix the symptom"),
    DuoPair(domain_keywords=["economics", "investment", "models", "moat"],
            member_a="munger", member_b="aristotle",
            tension="Multi-model lattice vs single taxonomy"),
    DuoPair(domain_keywords=["risk", "uncertainty", "fragility", "tail"],
            member_a="taleb", member_b="karpathy",
            tension="Hidden tails vs smooth empirical curves"),
    DuoPair(domain_keywords=["design", "user", "usability", "ux"],
            member_a="rams", member_b="ada",
            tension="What the user needs vs what computation can do"),
]

_DEFAULT_DUO = DuoPair(
    domain_keywords=[],
    member_a="socrates",
    member_b="feynman",
    tension="Top-down questioning vs bottom-up rebuilding",
)

_PROFILES: dict[str, CouncilProfile] = {
    "classic": CouncilProfile(
        name="classic",
        description="All 18 members with the domain triads above. Best for broad deliberation.",
        members=[
            "aristotle", "socrates", "sun-tzu", "ada", "aurelius",
            "machiavelli", "lao-tzu", "feynman", "torvalds", "musashi",
            "watts", "karpathy", "sutskever", "kahneman", "meadows",
            "munger", "taleb", "rams",
        ],
        triads={t.domain: t for t in _TRIADS},
    ),
    "exploration-orthogonal": CouncilProfile(
        name="exploration-orthogonal",
        description=(
            "12-member panel for discovery and 'unknown unknowns' reduction."
        ),
        members=[
            "socrates", "feynman", "sun-tzu", "machiavelli", "ada",
            "lao-tzu", "aurelius", "torvalds", "karpathy", "sutskever",
            "kahneman", "meadows",
        ],
        triads={
            "unknowns": Triad(
                domain="unknowns",
                members=["socrates", "lao-tzu", "feynman"],
                rationale="Assumption destruction + emergence + first-principles",
            ),
            "market-entry": Triad(
                domain="market-entry",
                members=["sun-tzu", "machiavelli", "aurelius"],
                rationale="Terrain + incentives + moral grounding",
            ),
            "system-design": Triad(
                domain="system-design",
                members=["ada", "feynman", "torvalds"],
                rationale="Formalize + simplify + ship",
            ),
            "reframing": Triad(
                domain="reframing",
                members=["socrates", "lao-tzu", "ada"],
                rationale="Destroy assumptions + emergence + formalize",
            ),
            "ai-frontier": Triad(
                domain="ai-frontier",
                members=["karpathy", "sutskever", "ada"],
                rationale="Empirical ML + scaling frontier + formal limits",
            ),
            "blind-spots": Triad(
                domain="blind-spots",
                members=["kahneman", "meadows", "socrates"],
                rationale="Cognitive bias + systems feedback + assumption testing",
            ),
        },
    ),
    "execution-lean": CouncilProfile(
        name="execution-lean",
        description="5-member panel for fast decision-to-action loops.",
        members=["torvalds", "feynman", "sun-tzu", "aurelius", "ada"],
        triads={
            "ship-now": Triad(
                domain="ship-now",
                members=["torvalds", "feynman", "aurelius"],
                rationale="Pragmatism + first-principles + moral clarity",
            ),
            "launch-strategy": Triad(
                domain="launch-strategy",
                members=["sun-tzu", "torvalds", "ada"],
                rationale="Terrain + engineering reality + formalism",
            ),
            "stability": Triad(
                domain="stability",
                members=["ada", "feynman", "aurelius"],
                rationale="Formal verification + empirical testing + resilience",
            ),
        },
    ),
}

# Canonical list of all polarity pair tuples (unordered).
_POLARITY_PAIRS: list[tuple[str, str]] = [
    ("socrates", "feynman"),
    ("aristotle", "lao-tzu"),
    ("sun-tzu", "aurelius"),
    ("ada", "machiavelli"),
    ("torvalds", "watts"),
    ("musashi", "torvalds"),
    ("karpathy", "sutskever"),
    ("karpathy", "ada"),
    ("kahneman", "feynman"),
    ("meadows", "torvalds"),
    ("munger", "aristotle"),
    ("taleb", "karpathy"),
    ("rams", "ada"),
]


# ---------------------------------------------------------------------------
# Registry class
# ---------------------------------------------------------------------------

class CouncilRegistry:
    """
    In-memory registry of council members, triads, duo pairs, and profiles.

    Automatically loads all agent ``.md`` files on construction.
    """

    def __init__(self, agents_dir: str | Path | None = None) -> None:
        self._agents_dir = Path(agents_dir) if agents_dir else resolve_agents_dir()
        self._members: dict[str, CouncilMember] = {}
        self._loaded = False

    # -- Lazy loading -------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load_agents()

    def load_agents(self) -> None:
        """Parse all ``council-*.md`` files from the agents directory."""
        self._members.clear()
        for path in sorted(self._agents_dir.glob("council-*.md")):
            member = parse_agent_file(path)
            key = member.short_name
            self._members[key] = member
        self._loaded = True

    # -- Members ------------------------------------------------------------

    @property
    def members(self) -> dict[str, CouncilMember]:
        self._ensure_loaded()
        return dict(self._members)

    def get_member(self, name: str) -> Optional[CouncilMember]:
        """Get a member by short name (e.g. ``"socrates"``)."""
        self._ensure_loaded()
        return self._members.get(name)

    def list_members(self) -> list[CouncilMember]:
        """Return all 18 council members sorted by name."""
        self._ensure_loaded()
        return list(self._members.values())

    def member_exists(self, name: str) -> bool:
        self._ensure_loaded()
        return name in self._members

    # -- Triads -------------------------------------------------------------

    @staticmethod
    def list_triads() -> list[Triad]:
        """Return all 20 pre-defined domain triads."""
        return list(_TRIADS)

    @staticmethod
    def get_triad(domain: str) -> Optional[Triad]:
        """Look up a triad by domain keyword."""
        for triad in _TRIADS:
            if triad.domain == domain:
                return triad
        return None

    def auto_select_triad(self, problem: str) -> Triad:
        """
        Auto-select the best-fitting triad for a problem statement.

        Uses keyword frequency matching against triad domains and
        rationales.  Falls back to ``"strategy"`` if no keywords match.
        """
        problem_lower = problem.lower()
        best_triad: Optional[Triad] = None
        best_score = 0

        for triad in _TRIADS:
            score = 0
            # Domain keyword match
            for word in triad.domain.replace("-", " ").split():
                if word in problem_lower:
                    score += 3
            # Rationale keyword match
            for word in triad.rationale.lower().split():
                if len(word) > 3 and word in problem_lower:
                    score += 1
            # Also check member domains
            for member_name in triad.members:
                member = self.get_member(member_name)
                if member:
                    for word in member.council.domain.lower().split():
                        if len(word) > 3 and word in problem_lower:
                            score += 2

            if score > best_score:
                best_score = score
                best_triad = triad

        if best_triad is None:
            # Default fallback: strategy triad
            best_triad = self.get_triad("strategy") or _TRIADS[1]

        return best_triad

    # -- Duo Pairs ----------------------------------------------------------

    @staticmethod
    def list_duo_pairs() -> list[DuoPair]:
        """Return all 13 duo polarity pairs."""
        return list(_DUO_PAIRS)

    @staticmethod
    def match_duo_pair(problem: str) -> DuoPair:
        """
        Match a problem statement to the best-fitting duo polarity pair.

        Falls back to Socrates vs Feynman if no keywords match.
        """
        problem_lower = problem.lower()
        best_pair = _DEFAULT_DUO
        best_score = 0

        for pair in _DUO_PAIRS:
            score = sum(
                1 for kw in pair.domain_keywords if kw in problem_lower
            )
            if score > best_score:
                best_score = score
                best_pair = pair

        return best_pair

    # -- Profiles -----------------------------------------------------------

    @staticmethod
    def list_profiles() -> list[CouncilProfile]:
        """Return all 3 council profiles."""
        return list(_PROFILES.values())

    @staticmethod
    def get_profile(name: str) -> Optional[CouncilProfile]:
        """Look up a council profile by name."""
        return _PROFILES.get(name)

    # -- Polarity Pairs -----------------------------------------------------

    @staticmethod
    def get_all_polarity_pairs() -> list[tuple[str, str]]:
        """Return all canonical polarity pair tuples."""
        return list(_POLARITY_PAIRS)

    @staticmethod
    def get_active_polarity_pairs(
        panel_members: list[str],
    ) -> list[tuple[str, str]]:
        """
        Return polarity pairs where *both* members are on the panel.

        Args:
            panel_members: Short names of the selected panel members.
        """
        member_set = set(panel_members)
        return [
            (a, b)
            for a, b in _POLARITY_PAIRS
            if a in member_set and b in member_set
        ]

    # -- Panel validation ---------------------------------------------------

    def validate_panel(
        self,
        member_names: list[str],
    ) -> dict:
        """
        Validate a custom member panel.

        Returns a dict with ``valid`` (bool), ``errors`` (list[str]),
        ``warnings`` (list[str]), and ``polarity_pairs`` found.
        """
        self._ensure_loaded()
        errors: list[str] = []
        warnings: list[str] = []

        # Check member count
        if len(member_names) < 2:
            errors.append("Panel must have at least 2 members.")
        if len(member_names) > 18:
            errors.append("Panel cannot exceed 18 members.")

        # Check duplicates
        if len(member_names) != len(set(member_names)):
            errors.append("Panel contains duplicate members.")

        # Check existence
        unknown = [n for n in member_names if not self.member_exists(n)]
        if unknown:
            errors.append(f"Unknown members: {', '.join(unknown)}")

        # Active polarity pairs
        active_pairs = self.get_active_polarity_pairs(member_names)
        if not active_pairs:
            warnings.append(
                "No polarity pairs found in this panel. Consider adding "
                "members that form natural tensions."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "polarity_pairs": [
                {"member_a": a, "member_b": b} for a, b in active_pairs
            ],
            "member_count": len(member_names),
        }
