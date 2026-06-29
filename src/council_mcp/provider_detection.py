"""
Council of High Intelligence — Provider Detection.

Wraps the existing ``scripts/detect-providers.sh`` shell script and
returns structured ``ProviderInfo`` objects.  Also provides a pure-Python
fallback when the shell script is unavailable.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from .config_loader import resolve_scripts_dir
from .models import ExecMethod, ProviderInfo

# Mapping from legacy exec_method names to current names.
_EXEC_METHOD_ALIASES: dict[str, str] = {
    "gemini_cli": ExecMethod.AGY.value,
}


def _normalise_exec_method(raw: str) -> str:
    """Map legacy exec_method names (e.g. ``gemini_cli``) to ``agy``."""
    return _EXEC_METHOD_ALIASES.get(raw, raw)


def detect_providers(
    script_path: str | Path | None = None,
    timeout: int = 15,
) -> list[ProviderInfo]:
    """
    Run the provider detection script and parse its JSON output.

    Args:
        script_path: Explicit path to ``detect-providers.sh``.
                     If *None*, resolved from the project's ``scripts/`` dir.
        timeout: Maximum seconds to wait for the script.

    Returns:
        List of ``ProviderInfo`` objects (one per provider, including
        unavailable ones).

    Raises:
        FileNotFoundError: If the detection script cannot be found.
        RuntimeError: If the script exits non-zero or produces invalid JSON.
    """
    if script_path is None:
        script_path = resolve_scripts_dir() / "detect-providers.sh"

    script_path = Path(script_path).resolve()
    if not script_path.is_file():
        raise FileNotFoundError(
            f"Provider detection script not found: {script_path}"
        )

    try:
        result = subprocess.run(
            ["bash", str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Provider detection timed out after {timeout}s."
        ) from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"Provider detection failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Provider detection produced invalid JSON: {exc}"
        ) from exc

    providers: list[ProviderInfo] = []
    for entry in data.get("providers", []):
        providers.append(
            ProviderInfo(
                name=entry.get("name", ""),
                available=entry.get("available", False),
                exec_method=_normalise_exec_method(
                    entry.get("exec_method", "")
                ),
                binary=entry.get("binary", ""),
                models=entry.get("models", []),
            )
        )
    return providers


def get_available_providers(
    script_path: str | Path | None = None,
) -> list[ProviderInfo]:
    """Return only the providers that are currently available."""
    return [p for p in detect_providers(script_path) if p.available]


def get_provider_count(
    script_path: str | Path | None = None,
) -> int:
    """Return the number of available providers."""
    return len(get_available_providers(script_path))


def fallback_anthropic_only() -> list[ProviderInfo]:
    """
    Return a single-provider list with only Anthropic available.

    Used as a safe fallback when the detection script is missing or
    the system has no other providers.
    """
    return [
        ProviderInfo(
            name="anthropic",
            available=True,
            exec_method=ExecMethod.SUBAGENT.value,
            binary="native",
            models=["opus", "sonnet", "haiku"],
        ),
    ]
