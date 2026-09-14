"""Tests for the deliberation engine and routing engine."""

import pytest
from council_mcp.council_registry import CouncilRegistry
from council_mcp.deliberation_engine import generate_restate_prompts
from council_mcp.routing_engine import auto_route
from council_mcp.models import ProviderInfo, ExecMethod


@pytest.fixture
def registry() -> CouncilRegistry:
    return CouncilRegistry()


def test_generate_restate_prompts(registry: CouncilRegistry):
    members = [registry.get_member(name) for name in ["socrates", "feynman", "torvalds"]]
    members = [m for m in members if m is not None]
    
    providers = [
        ProviderInfo(
            name="anthropic",
            available=True,
            exec_method=ExecMethod.SUBAGENT.value,
            binary="native",
            models=["opus", "sonnet", "haiku"],
        )
    ]
    routing_table = auto_route(members=members, providers=providers, registry=registry)
    
    prompts = generate_restate_prompts(
        members=members,
        problem="Should we adopt AI coding assistants across all engineering teams?",
        routing_table=routing_table,
    )
    assert len(prompts) == 3
    for p in prompts:
        assert p.member_name in ("socrates", "feynman", "torvalds")
        assert "Should we adopt AI coding assistants" in p.prompt_text
        assert p.exec_method == ExecMethod.SUBAGENT.value
        assert p.model in ("opus", "sonnet", "haiku")


def test_routing_engine_single_provider(registry: CouncilRegistry):
    members = [registry.get_member(name) for name in ["socrates", "feynman", "torvalds"]]
    members = [m for m in members if m is not None]
    
    providers = [
        ProviderInfo(
            name="anthropic",
            available=True,
            exec_method=ExecMethod.SUBAGENT.value,
            binary="native",
            models=["opus", "sonnet", "haiku"],
        )
    ]
    table = auto_route(members=members, providers=providers, registry=registry)
    assert len(table.slots) == len(members)
    for slot in table.slots:
        assert slot.provider == "anthropic"
        assert slot.exec_method == ExecMethod.SUBAGENT.value
