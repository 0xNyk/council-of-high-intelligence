# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-10

### Added
- Gemini CLI extension manifest (`gemini-extension.json`)
- MCP multi-provider routing (opt-in): mix Claude, Ollama, and Gemini as council members; configured via `~/.gemini/settings.json` + `configs/mcp-provider-slots.yaml`
- `configs/mcp-provider-slots.yaml` — routing template mapping all 18 council seats to MCP servers
- `commands/council.toml` — `/council` entry point for Gemini CLI
- Subcommands: `/council:quick`, `/council:duo`, `/council:full`, `/council:triad`
- `skills/council/SKILL.md` — full coordinator skill ported to Gemini path variables and MCP routing
- `skills/council/references/` — triads, polarity pairs, and verdict templates in separate reference files
- All 18 council member persona files in `agents/` with Gemini-compatible frontmatter
- `scripts/install.sh` extended with `--gemini`, `--gemini-only`, and `--all` flags
- `scripts/validate.sh` smoke test (JSON, TOML, frontmatter, required files)
- `.github/workflows/lint.yml` CI pipeline
- `GEMINI.md` extension context file
- `docs/architecture.md`, `docs/porting-notes.md`

### Changed
- Stripped Claude-specific frontmatter (`model`, `color`, `tools`, `provider_affinity`) from all agent files
- Replaced `~/.claude/agents/` paths with `${extensionPath}/agents/` throughout
- Replaced `--models` flag with `--mcp-route` for Gemini-native provider routing
- Moved triad taxonomy and verdict templates from SKILL.md into `skills/council/references/` for progressive disclosure

### Removed
- `--no-auto-route` flag (Claude-only concept; MCP routing handles this natively)
- Bash-based provider detection script dependency (replaced by MCP server declarations)

### Fixed
- Removed `council:` nested key from all 18 agent frontmatters — Gemini CLI agent loader only accepts `name` and `description`
- Moved `mcpServers` out of the extension manifest into user-configured `~/.gemini/settings.json` — prevents unwanted MCP startup errors for users not using multi-provider mode

[Unreleased]: https://github.com/Alpsource/council-of-high-intelligence-gemini/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Alpsource/council-of-high-intelligence-gemini/releases/tag/v0.1.0
