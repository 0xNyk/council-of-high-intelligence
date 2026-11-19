"""
Council of High Intelligence — Routing Engine.

Implements the STEP 1 routing algorithm from the deliberation protocol:

  Path A — Manual routing (``--models`` YAML)
  Path B — Auto-routing (polarity separation → spread → affinity → tier)
  Path C — No routing (Claude-only frontmatter defaults)

Also handles chairman selection (STEP 1.7).
"""

from __future__ import annotations

import math
from typing import Any, Optional

from .config_loader import load_auto_route_defaults
from .council_registry import CouncilRegistry
from .models import (
    ChairmanSelection,
    CouncilMember,
    ExecMethod,
    ProviderInfo,
    RoutingSlot,
    RoutingTable,
)


# Default provider → exec_method mapping.
_PROVIDER_EXEC: dict[str, str] = {
    "anthropic": ExecMethod.SUBAGENT.value,
    "openai": ExecMethod.CODEX_EXEC.value,
    "google": ExecMethod.AGY.value,
    "ollama": ExecMethod.OLLAMA_RUN.value,
    "nvidia_nim": ExecMethod.OPENAI_COMPATIBLE_API.value,
    "cursor_cli": ExecMethod.CURSOR_CLI.value,
}

# Default timeout per exec method (seconds).
_TIMEOUTS: dict[str, int] = {
    ExecMethod.SUBAGENT.value: 60,
    ExecMethod.CODEX_EXEC.value: 60,
    ExecMethod.AGY.value: 60,
    ExecMethod.OLLAMA_RUN.value: 120,
    ExecMethod.CURSOR_CLI.value: 90,
    ExecMethod.OPENAI_COMPATIBLE_API.value: 90,
}


def _get_timeout(exec_method: str) -> int:
    return _TIMEOUTS.get(exec_method, 60)


# ---------------------------------------------------------------------------
# Path A — Manual routing
# ---------------------------------------------------------------------------

def manual_route(
    members: list[CouncilMember],
    slots_config: dict[str, Any],
) -> RoutingTable:
    """
    Build a routing table from a YAML seat mapping (``--models`` flag).

    The config must contain a ``seats`` dict keyed by member short name,
    each with ``provider``, ``model``, and optionally ``base_url``,
    ``api_key_env``, ``exec_method``.
    """
    seats = slots_config.get("seats", {})
    fallback = slots_config.get("fallback", {})
    slots: list[RoutingSlot] = []
    providers_seen: set[str] = set()

    for member in members:
        key = member.short_name
        seat = seats.get(key, fallback)
        if not seat:
            # Ultimate fallback: anthropic with frontmatter model
            seat = {"provider": "anthropic", "model": member.model_tier}

        provider = seat.get("provider", "anthropic")
        exec_method = seat.get(
            "exec_method", _PROVIDER_EXEC.get(provider, ExecMethod.SUBAGENT.value)
        )
        providers_seen.add(provider)

        slots.append(
            RoutingSlot(
                member_name=key,
                provider=provider,
                model=seat.get("model", member.model_tier),
                exec_method=exec_method,
                base_url=seat.get("base_url"),
                api_key_env=seat.get("api_key_env"),
                timeout_seconds=_get_timeout(exec_method),
            )
        )

    return RoutingTable(
        slots=slots,
        provider_count=len(providers_seen),
        multi_provider=len(providers_seen) >= 2,
    )


# ---------------------------------------------------------------------------
# Path B — Auto-routing
# ---------------------------------------------------------------------------

def auto_route(
    members: list[CouncilMember],
    providers: list[ProviderInfo],
    registry: CouncilRegistry,
    route_config: dict[str, Any] | None = None,
) -> RoutingTable:
    """
    Automatically route panel members across available providers.

    Implements the algorithm from SKILL.md STEP 1:
      1. Polarity pair separation (hard constraint)
      2. Provider spread (hard constraint)
      3. Provider affinity (soft tiebreaker)
      4. Tier matching (soft)
    """
    if route_config is None:
        try:
            route_config = load_auto_route_defaults()
        except FileNotFoundError:
            route_config = {}

    available = [p for p in providers if p.available]
    if len(available) <= 1:
        # Single provider — skip routing
        return no_route(members)

    provider_models = route_config.get("provider_models", {})
    active_pairs = registry.get_active_polarity_pairs(
        [m.short_name for m in members]
    )

    # Build provider capacity: floor/ceil distribution
    n_providers = len(available)
    n_members = len(members)
    base = n_members // n_providers
    extra = n_members % n_providers

    capacity: dict[str, int] = {}
    for idx, p in enumerate(available):
        capacity[p.name] = base + (1 if idx < extra else 0)

    # Track assignments: provider → list of member keys
    assignments: dict[str, list[str]] = {p.name: [] for p in available}

    # Build pair constraint graph: if (A, B) is a pair, they must go to
    # different providers.
    pair_of: dict[str, set[str]] = {}
    for a, b in active_pairs:
        pair_of.setdefault(a, set()).add(b)
        pair_of.setdefault(b, set()).add(a)

    # Sort members: constrained first (have polarity pair partners),
    # then by affinity list length (fewer options first).
    def _sort_key(m: CouncilMember) -> tuple[int, int]:
        has_pair = 1 if m.short_name in pair_of else 0
        affinity_len = len(m.council.provider_affinity)
        return (-has_pair, affinity_len)

    sorted_members = sorted(members, key=_sort_key)

    # Assign each member to a provider
    member_provider: dict[str, str] = {}

    for member in sorted_members:
        key = member.short_name
        affinities = member.council.provider_affinity or [
            p.name for p in available
        ]

        # Providers used by polarity partners (forbidden for this member)
        forbidden: set[str] = set()
        for partner in pair_of.get(key, set()):
            if partner in member_provider:
                forbidden.add(member_provider[partner])
                # Cursor claude-* check: if partner is on anthropic,
                # cursor with claude model is also forbidden
                if member_provider[partner] == "anthropic":
                    forbidden.add("cursor_cli")  # avoid claude-on-cursor

        # Score each available provider
        best_provider: str | None = None
        best_score = -999

        for provider in available:
            if provider.name in forbidden:
                continue
            remaining = capacity[provider.name] - len(
                assignments[provider.name]
            )
            if remaining <= 0:
                continue

            score = 0
            # Affinity bonus (higher = listed earlier)
            if provider.name in affinities:
                score += (len(affinities) - affinities.index(provider.name)) * 10
            # Spread bonus: prefer providers with more remaining capacity
            score += remaining * 5
            # Slight penalty if provider already used a lot
            score -= len(assignments[provider.name]) * 2

            if score > best_score:
                best_score = score
                best_provider = provider.name

        if best_provider is None:
            # All preferred providers full or forbidden — use any with capacity
            for provider in available:
                remaining = capacity[provider.name] - len(
                    assignments[provider.name]
                )
                if remaining > 0 and provider.name not in forbidden:
                    best_provider = provider.name
                    break

        if best_provider is None:
            # Absolute fallback: anthropic (break polarity constraint)
            best_provider = "anthropic"

        member_provider[key] = best_provider
        assignments[best_provider].append(key)

    # Build routing slots with tier-matched models
    slots: list[RoutingSlot] = []
    provider_info_map = {p.name: p for p in available}

    for member in members:
        key = member.short_name
        provider_name = member_provider.get(key, "anthropic")
        p_info = provider_info_map.get(provider_name)
        exec_method = (
            p_info.exec_method
            if p_info
            else ExecMethod.SUBAGENT.value
        )

        # Tier matching
        tier = "high" if member.model_tier == "opus" else "mid"
        p_models = provider_models.get(provider_name, {})
        model = p_models.get(tier) or member.model_tier
        if model is None:
            model = member.model_tier

        # NIM-specific fields
        base_url = None
        api_key_env = None
        if provider_name == "nvidia_nim":
            base_url = (
                p_info.binary
                if p_info and p_info.binary.startswith("http")
                else "https://integrate.api.nvidia.com/v1"
            )
            api_key_env = "NVIDIA_API_KEY"

        slots.append(
            RoutingSlot(
                member_name=key,
                provider=provider_name,
                model=model,
                exec_method=exec_method,
                base_url=base_url,
                api_key_env=api_key_env,
                timeout_seconds=_get_timeout(exec_method),
            )
        )

    providers_used = set(s.provider for s in slots)
    return RoutingTable(
        slots=slots,
        provider_count=len(providers_used),
        multi_provider=len(providers_used) >= 2,
    )


# ---------------------------------------------------------------------------
# Path C — No routing (Claude-only)
# ---------------------------------------------------------------------------

def no_route(members: list[CouncilMember]) -> RoutingTable:
    """
    Assign all members to Anthropic with their frontmatter model defaults.

    Used when ``--no-auto-route`` is specified or only one provider is
    detected.
    """
    slots = [
        RoutingSlot(
            member_name=m.short_name,
            provider="anthropic",
            model=m.model_tier,
            exec_method=ExecMethod.SUBAGENT.value,
            timeout_seconds=_get_timeout(ExecMethod.SUBAGENT.value),
        )
        for m in members
    ]
    return RoutingTable(slots=slots, provider_count=1, multi_provider=False)


# ---------------------------------------------------------------------------
# Chairman selection (STEP 1.7)
# ---------------------------------------------------------------------------

# Default chairman model per provider.
_CHAIRMAN_DEFAULTS: dict[str, str] = {
    "anthropic": "opus",
    "openai": "gpt-5.4",
    "google": "gemini-2.5-pro",
    "ollama": "llama3",
    "nvidia_nim": "deepseek-ai/deepseek-v4-pro",
    "cursor_cli": "gpt-5.4-high",
}

# Tier ranking for auto-selection (higher = preferred).
_PROVIDER_TIER: dict[str, int] = {
    "anthropic": 5,
    "openai": 5,
    "google": 4,
    "cursor_cli": 3,
    "nvidia_nim": 2,
    "ollama": 1,
}


def select_chairman(
    panel_members: list[str],
    available_providers: list[ProviderInfo],
    chairman_override: str | None = None,
    route_config: dict[str, Any] | None = None,
) -> ChairmanSelection:
    """
    Select the Chairman for verdict synthesis (STEP 1.7).

    Selection algorithm (first match wins):
      1. Explicit override (``--chairman <name>``)
      2. Config override (``chairman:`` block in auto-route-defaults)
      3. Auto-select: highest-tier provider not on the panel
      4. Single-provider fallback
    """
    if route_config is None:
        try:
            route_config = load_auto_route_defaults()
        except FileNotFoundError:
            route_config = {}

    chairman_defaults = route_config.get("chairman_defaults", _CHAIRMAN_DEFAULTS)

    # 1. Explicit override
    if chairman_override:
        # Could be a provider name or model alias
        if chairman_override in chairman_defaults:
            provider = chairman_override
            model = chairman_defaults[provider]
        else:
            # Treat as model alias — find a provider
            provider = "anthropic"
            model = chairman_override
            for p_name, p_model in chairman_defaults.items():
                if p_model == chairman_override:
                    provider = p_name
                    break
        return ChairmanSelection(
            name=f"chairman-{provider}",
            provider=provider,
            model=model,
            rationale="Explicit --chairman override",
        )

    # 2. Config override
    config_chairman = route_config.get("chairman")
    if config_chairman and isinstance(config_chairman, dict):
        return ChairmanSelection(
            name=f"chairman-{config_chairman['provider']}",
            provider=config_chairman["provider"],
            model=config_chairman.get("model", ""),
            rationale="Config override (auto-route-defaults.yaml)",
        )

    # 3. Auto-select: highest-tier provider, prefer one not on panel
    available_names = {p.name for p in available_providers if p.available}

    # Sort providers by tier (descending)
    ranked = sorted(
        available_names,
        key=lambda n: _PROVIDER_TIER.get(n, 0),
        reverse=True,
    )

    # Prefer provider not represented on panel
    # (We don't have routing info here, so we can't check precisely.
    #  Use panel size as a heuristic — if panel is small, anthropic
    #  is likely the only provider used.)
    for provider in ranked:
        model = chairman_defaults.get(provider, "")
        if model:
            return ChairmanSelection(
                name=f"chairman-{provider}",
                provider=provider,
                model=model,
                rationale=f"Auto-selected (highest-tier: {provider})",
            )

    # 4. Single-provider fallback
    return ChairmanSelection(
        name="chairman-anthropic",
        provider="anthropic",
        model=chairman_defaults.get("anthropic", "opus"),
        rationale=(
            "Single-provider fallback. Chairman shares provider with "
            "one or more panel members."
        ),
    )
