# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Validation

```bash
./scripts/validate.sh          # 17 checks: JSON, TOML, frontmatter, required files
shellcheck scripts/*.sh        # shell script linting
```

The validate script uses Python (auto-detected as `python3`/`python`) for JSON checking via stdin redirect, and grep-based checks for TOML and frontmatter — no parser dependencies.

## Local Extension Install

```bash
# Preferred: link for live iteration (changes visible without reinstall)
gemini extensions link $(pwd)

# Manual install to ~/.gemini/extensions/
./scripts/install.sh --gemini

# Dry run
./scripts/install.sh --gemini --dry-run
```

## Architecture

This is a Gemini CLI extension. The entry point is `gemini-extension.json`, which declares the manifest, two optional MCP servers (`claude-code`, `ollama`), and two env-var settings (`COUNCIL_ROUTING_PROFILE`, `COUNCIL_MCP_SLOTS_PATH`). Gemini loads `GEMINI.md` as session context at startup.

**Execution flow for `/council <problem>`:**
1. `commands/council.toml` — receives user input via `{{args}}`; its `prompt` field instructs Gemini to read `SKILL.md`
2. `skills/council/SKILL.md` — coordinator logic; parses flags, selects panel, routes providers, runs the 7-step deliberation protocol
3. For each council member: SKILL.md instructs Gemini to read `agents/council-<name>.md` and embody that persona for the round
4. Reference data loaded on-demand from `skills/council/references/` (triads, polarity pairs, verdict templates)

**TOML commands** (`commands/`): five files — `council.toml` (main), plus `council/quick.toml`, `full.toml`, `duo.toml`, `triad.toml`. Each is a thin wrapper that injects a mode flag before handing off to SKILL.md.

**Agent files** (`agents/council-*.md`): 18 files. Frontmatter fields that matter: `name`, `description`, `council.mcp_affinity` (values: `anthropic` or `ollama` — used by SKILL.md to assign MCP servers in multi-provider mode). Body sections must follow this order: Identity → Grounding Protocol → Analytical Method → What You See → What You Miss → When Deliberating → Output Format (Council Round 2) → Output Format (Standalone).

**MCP routing** (`configs/mcp-provider-slots.yaml`): maps all 18 seats to `claude-code` or `ollama` MCP servers. Active only when `COUNCIL_ROUTING_PROFILE=mcp-multi` or `--mcp-route` flag is passed. Polarity pair members (e.g., Socrates/Feynman) are hard-constrained to different servers in STEP 1 of SKILL.md.

## Key Constraints

- `${extensionPath}` is the only Gemini-specific path variable — every agent and reference file path in SKILL.md uses it. Don't use `~/.claude/` or absolute paths.
- The deliberation protocol in SKILL.md (Steps 0–7, all `[CHECKPOINT]` and `[VERIFY]` markers, enforcement rules) is preserved verbatim from the upstream Claude Code original. Don't refactor it for style.
- Agent frontmatter must not include `model`, `color`, `tools`, or `provider_affinity` — those are Claude Code fields. Use `mcp_affinity` instead.
