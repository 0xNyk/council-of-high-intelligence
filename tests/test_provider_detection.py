"""Tests for provider detection and graceful fallback behavior."""

import pytest
from pathlib import Path
from council_mcp.provider_detection import (
    detect_providers,
    get_available_providers,
    get_provider_count,
    fallback_anthropic_only,
)
from council_mcp.models import ExecMethod


def test_detect_providers_missing_script_raises_when_no_fallback(tmp_path: Path):
    nonexistent = tmp_path / "detect-providers.sh"
    with pytest.raises(FileNotFoundError):
        detect_providers(script_path=nonexistent, fallback=False)


def test_detect_providers_degrades_gracefully_with_fallback(tmp_path: Path):
    nonexistent = tmp_path / "detect-providers.sh"
    providers = detect_providers(script_path=nonexistent, fallback=True)
    assert len(providers) == 1
    p = providers[0]
    assert p.name == "anthropic"
    assert p.available is True
    assert p.exec_method == ExecMethod.SUBAGENT.value
    assert p.models == ["opus", "sonnet", "haiku"]


def test_get_available_providers_defaults_to_fallback(tmp_path: Path):
    nonexistent = tmp_path / "detect-providers.sh"
    providers = get_available_providers(script_path=nonexistent)
    assert len(providers) == 1
    assert providers[0].name == "anthropic"
    assert get_provider_count(script_path=nonexistent) == 1


def test_fallback_anthropic_only():
    providers = fallback_anthropic_only()
    assert len(providers) == 1
    assert providers[0].name == "anthropic"
    assert providers[0].available is True
