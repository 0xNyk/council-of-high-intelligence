"""Tests for the CouncilRegistry and agent parsing."""

import pytest
from council_mcp.council_registry import CouncilRegistry
from council_mcp.models import CouncilMember, Triad, DuoPair, CouncilProfile


@pytest.fixture
def registry() -> CouncilRegistry:
    return CouncilRegistry()


def test_registry_parses_all_agents(registry: CouncilRegistry):
    members = registry.list_members()
    assert len(members) == 18, f"Expected 18 council members, got {len(members)}"

    expected_names = {
        "ada", "aristotle", "aurelius", "feynman", "kahneman",
        "karpathy", "lao-tzu", "machiavelli", "meadows", "munger",
        "musashi", "rams", "socrates", "sun-tzu", "sutskever",
        "taleb", "torvalds", "watts"
    }
    actual_names = {m.short_name for m in members}
    assert actual_names == expected_names

    for m in members:
        assert isinstance(m, CouncilMember)
        assert m.short_name
        assert m.figure
        assert m.domain
        assert m.polarity
        assert m.model_tier in ("opus", "sonnet", "haiku")


def test_triad_lookups(registry: CouncilRegistry):
    triads = registry.list_triads()
    assert len(triads) >= 20

    arch_triad = registry.get_triad("architecture")
    assert arch_triad is not None
    assert isinstance(arch_triad, Triad)
    assert arch_triad.domain == "architecture"
    assert arch_triad.members == ["aristotle", "ada", "feynman"]

    assert registry.get_triad("nonexistent-domain") is None


def test_duo_pair_lookups(registry: CouncilRegistry):
    pairs = registry.list_duo_pairs()
    assert len(pairs) >= 10

    pair = registry.match_duo_pair("Should we use microservices for our backend architecture?")
    assert pair is not None
    assert isinstance(pair, DuoPair)
    assert pair.member_a in ("aristotle", "lao-tzu")
    assert pair.member_b in ("aristotle", "lao-tzu")


def test_profile_lookups(registry: CouncilRegistry):
    profiles = registry.list_profiles()
    assert len(profiles) == 3

    profile_names = {p.name for p in profiles}
    assert profile_names == {"classic", "exploration-orthogonal", "execution-lean"}

    lean = registry.get_profile("execution-lean")
    assert lean is not None
    assert isinstance(lean, CouncilProfile)
    assert len(lean.members) == 5
    assert "torvalds" in lean.members
