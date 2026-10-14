"""
Council of High Intelligence — MCP Data Models.

Type-safe Pydantic v2 models covering the full CoHI domain:
enums, agent metadata, triads, routing, deliberation protocol,
stances, vote tallies, and verdict structures.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DeliberationMode(str, Enum):
    """The three deliberation modes supported by the council."""

    FULL = "full"
    QUICK = "quick"
    DUO = "duo"


class Provider(str, Enum):
    """LLM provider identifiers recognised by the routing engine."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    OLLAMA = "ollama"
    NVIDIA_NIM = "nvidia_nim"
    CURSOR_CLI = "cursor_cli"


class ExecMethod(str, Enum):
    """Dispatch method for running a member's prompt on a provider."""

    SUBAGENT = "subagent"
    CODEX_EXEC = "codex_exec"
    AGY = "agy"
    OLLAMA_RUN = "ollama_run"
    CURSOR_CLI = "cursor_cli"
    OPENAI_COMPATIBLE_API = "openai_compatible_api"


class ModelTier(str, Enum):
    """Model quality tier — maps to provider-specific model ids."""

    HIGH = "high"
    MID = "mid"


class Confidence(str, Enum):
    """Member confidence level in their final stance."""

    HIGH = "high"
    MED = "med"
    LOW = "low"


class EvidenceLabel(str, Enum):
    """Claim-type labels used during cross-examination."""

    EMPIRICAL = "empirical"
    MECHANISTIC = "mechanistic"
    STRATEGIC = "strategic"
    ETHICAL = "ethical"
    HEURISTIC = "heuristic"


class RoundName(str, Enum):
    """Canonical round identifiers across all deliberation modes."""

    # Full mode rounds
    RESTATE = "restate"
    ANALYSIS = "analysis"
    CROSS_EXAMINATION = "cross_examination"
    FINAL = "final"

    # Quick mode rounds
    QUICK_ANALYSIS = "quick_analysis"
    QUICK_FINAL = "quick_final"

    # Duo mode rounds
    DUO_OPENING = "duo_opening"
    DUO_RESPONSE = "duo_response"
    DUO_FINAL = "duo_final"


# ---------------------------------------------------------------------------
# Agent / Council Member models
# ---------------------------------------------------------------------------

class CouncilMetadata(BaseModel):
    """Structured council metadata parsed from agent YAML frontmatter."""

    model_config = ConfigDict(populate_by_name=True)

    figure: str
    domain: str
    polarity: str
    polarity_pairs: list[str] = Field(default_factory=list)
    triads: list[str] = Field(default_factory=list)
    duo_keywords: list[str] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)
    provider_affinity: list[str] = Field(default_factory=list)


class CouncilMember(BaseModel):
    """
    Complete representation of a council member, combining YAML
    frontmatter with parsed markdown body sections.
    """

    model_config = ConfigDict(populate_by_name=True)

    # --- Frontmatter fields ---
    name: str
    description: str
    model_tier: str = Field(
        description="Default model tier from frontmatter (e.g. 'opus', 'sonnet').",
    )
    color: str = ""
    tools: list[str] = Field(default_factory=list)
    council: CouncilMetadata

    # --- Markdown body sections (raw text) ---
    identity: str = ""
    grounding_protocol: str = ""
    analytical_method: str = ""
    what_you_see: str = ""
    what_you_miss: str = ""
    when_deliberating: str = ""
    output_format_round2: str = ""
    output_format_standalone: str = ""

    @property
    def short_name(self) -> str:
        """Return the member key without the 'council-' prefix."""
        return self.name.removeprefix("council-")

    @property
    def figure(self) -> str:
        """Return the historical/technical figure name."""
        return self.council.figure

    @property
    def domain(self) -> str:
        """Return the member's domain of expertise."""
        return self.council.domain

    @property
    def polarity(self) -> str:
        """Return the member's analytical polarity."""
        return self.council.polarity


# ---------------------------------------------------------------------------
# Triad / Duo / Profile models
# ---------------------------------------------------------------------------

class Triad(BaseModel):
    """A pre-defined 3-member triad for a specific domain."""

    domain: str
    members: list[str] = Field(min_length=3, max_length=3)
    rationale: str


class DuoPair(BaseModel):
    """A polarity pair used in duo mode with associated domain keywords."""

    domain_keywords: list[str]
    member_a: str
    member_b: str
    tension: str


class CouncilProfile(BaseModel):
    """A named panel profile with a fixed member roster and optional triads."""

    name: str
    description: str
    members: list[str]
    triads: dict[str, Triad] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Provider / Routing models
# ---------------------------------------------------------------------------

class ProviderInfo(BaseModel):
    """Detection result for a single LLM provider."""

    name: str
    available: bool
    exec_method: str
    binary: str
    models: list[str] = Field(default_factory=list)


class RoutingSlot(BaseModel):
    """One member's routing assignment: member → provider → model."""

    member_name: str
    provider: str
    model: str
    exec_method: str
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    timeout_seconds: int = 60


class RoutingTable(BaseModel):
    """Complete routing assignment for a panel."""

    slots: list[RoutingSlot] = Field(default_factory=list)
    provider_count: int = 1
    multi_provider: bool = False

    def get_slot(self, member_name: str) -> Optional[RoutingSlot]:
        """Look up the routing slot for a member."""
        for slot in self.slots:
            if slot.member_name == member_name:
                return slot
        return None


# ---------------------------------------------------------------------------
# Panel Selection models
# ---------------------------------------------------------------------------

class PanelSelection(BaseModel):
    """Result of panel selection (STEP 0)."""

    members: list[str]
    mode: DeliberationMode
    domain_weight_member: Optional[str] = Field(
        default=None,
        description=(
            "The single member receiving 1.5× weight at tie-breaking. "
            "None if ambiguous match."
        ),
    )
    domain_weight_rationale: str = ""
    selection_rationale: str = ""


class ChairmanSelection(BaseModel):
    """Result of chairman selection (STEP 1.7)."""

    name: str
    provider: str
    model: str
    rationale: str = ""


# ---------------------------------------------------------------------------
# Deliberation Protocol models
# ---------------------------------------------------------------------------

class RoundPrompt(BaseModel):
    """A generated prompt ready to be sent to a member's LLM."""

    member_name: str
    prompt_text: str
    exec_method: str = ""
    model: str = ""
    timeout_seconds: int = 60
    identity_preamble: str = Field(
        default="",
        description="Inlined identity for non-subagent providers.",
    )


class AnonymizationMapping(BaseModel):
    """Bidirectional mapping between real names and anonymized labels."""

    label_to_member: dict[str, str] = Field(default_factory=dict)
    member_to_label: dict[str, str] = Field(default_factory=dict)


class StanceLine(BaseModel):
    """Parsed structured stance from a member's final round output."""

    member: str
    stance: str
    confidence: Confidence = Confidence.MED
    dealbreaker: bool = False
    raw_line: str = ""


class VoteOption(BaseModel):
    """One option in the vote tally."""

    label: str
    weight: float = 0.0
    backers: list[str] = Field(default_factory=list)
    domain_weight_member: Optional[str] = None


class VoteTally(BaseModel):
    """Complete weighted vote tally from STEP 6."""

    options: list[VoteOption] = Field(default_factory=list)
    w_total: float = 0.0
    threshold: float = 0.0
    consensus_option: Optional[str] = None
    consensus_reached: bool = False
    domain_weight_member: Optional[str] = None
    domain_weight_value: float = 1.5


class EnforcementResult(BaseModel):
    """Results of the post-round enforcement scan (STEP 4)."""

    dissent_quota_met: bool = False
    dissent_count: int = 0
    novelty_gate_passed: dict[str, bool] = Field(default_factory=dict)
    agreement_ratio: float = 0.0
    agreement_threshold_exceeded: bool = False
    evidence_labels: dict[str, list[str]] = Field(default_factory=dict)
    evidence_monoculture: bool = False
    anti_recursion_triggered: list[str] = Field(default_factory=list)
    remediation_prompts: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Session Metadata
# ---------------------------------------------------------------------------

class SessionMetadata(BaseModel):
    """Session telemetry appended to every verdict (schema_version: 1)."""

    schema_version: int = 1
    mode: str = ""
    panel_size: int = 0
    rounds_run: int = 0
    chairman_failed_fallback: bool = False
    tools_used: bool = False
    input_tokens_estimate: Optional[str] = None
    output_tokens_estimate: Optional[str] = None
    duration_seconds: Optional[float] = None
    provider_count: int = 1
    fallbacks_triggered: list[str] = Field(default_factory=list)
