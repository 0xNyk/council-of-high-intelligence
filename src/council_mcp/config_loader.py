"""
Council of High Intelligence — Configuration Loader.

Loads YAML configuration files (auto-route-defaults, provider-model-slots)
and resolves the project root from the MCP server's location or an
environment variable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml


def _get_bundled_or_source_path(folder_name: str) -> Path:
    """Helper to locate a folder either bundled in the package or in the source repo."""
    current = Path(__file__).resolve().parent
    
    # 1. Check if it's bundled inside the installed package
    bundled = current / folder_name
    if bundled.is_dir():
        return bundled
        
    # 2. Check if we are running from source (up two levels: src/council_mcp -> repo root)
    source_repo = current.parent.parent / folder_name
    if source_repo.is_dir():
        return source_repo
        
    raise FileNotFoundError(
        f"Could not locate '{folder_name}' directory. It is neither bundled in the "
        "package nor found in the source repository."
    )

def resolve_project_root() -> Path:
    """
    Resolve the CoHI project root directory.
    Returns the repository root if running from source. If running from an 
    installed package, returns the package root.
    """
    env_root = os.environ.get("COHI_PROJECT_ROOT")
    if env_root:
        root = Path(env_root).resolve()
        if root.is_dir():
            return root
        raise FileNotFoundError(f"COHI_PROJECT_ROOT={env_root!r} does not point to a valid directory.")
        
    current = Path(__file__).resolve().parent
    if (current / "agents").is_dir():
        return current
        
    # Running from source
    return current.parent.parent

def resolve_agents_dir() -> Path:
    """Resolve the directory containing council agent ``.md`` files."""
    env_dir = os.environ.get("COHI_AGENTS_DIR")
    if env_dir:
        agents = Path(env_dir).resolve()
        if agents.is_dir():
            return agents
        raise FileNotFoundError(f"COHI_AGENTS_DIR={env_dir!r} is invalid.")
    
    return _get_bundled_or_source_path("agents")

def resolve_scripts_dir() -> Path:
    """Resolve the ``scripts/`` directory."""
    return _get_bundled_or_source_path("scripts")

def resolve_configs_dir() -> Path:
    """Resolve the ``configs/`` directory."""
    return _get_bundled_or_source_path("configs")


def load_yaml(path: Path) -> dict[str, Any]:
    """
    Load and parse a YAML file.

    Args:
        path: Absolute or relative path to the YAML file.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the file contains invalid YAML.
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"YAML file not found: {path}")

    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_auto_route_defaults() -> dict[str, Any]:
    """
    Load ``configs/auto-route-defaults.yaml``.

    Returns:
        Dictionary with ``provider_models``, ``chairman_defaults``,
        and optionally ``chairman`` keys.
    """
    path = resolve_configs_dir() / "auto-route-defaults.yaml"
    return load_yaml(path)


def load_model_slots(path: str | Path) -> dict[str, Any]:
    """
    Load a provider-model-slots YAML file.

    Args:
        path: Path to the YAML file.  If relative, resolved against
              the ``configs/`` directory.

    Returns:
        Dictionary with ``profile``, ``strategy``, ``seats``,
        and ``fallback`` keys.
    """
    p = Path(path)
    if not p.is_absolute():
        p = resolve_configs_dir() / p
    return load_yaml(p)


def load_protocol_json() -> dict[str, Any]:
    """
    Load the protocol.json definition containing triads, duo pairs, and profiles.

    Checks ``configs/protocol.json`` first, then ``protocol.json`` in project root.
    """
    try:
        path = resolve_configs_dir() / "protocol.json"
        if path.is_file():
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
    except FileNotFoundError:
        pass

    root_path = resolve_project_root() / "protocol.json"
    if root_path.is_file():
        with open(root_path, encoding="utf-8") as fh:
            return json.load(fh)

    raise FileNotFoundError("Could not find protocol.json in configs/ or project root.")
