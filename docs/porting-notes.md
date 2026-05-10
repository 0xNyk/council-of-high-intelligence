# Porting Notes: Claude Code → Gemini CLI

Honest accounting of what changed, what stayed the same, and why.

## What Was Preserved Verbatim

- All 18 persona definitions: Identity, Grounding Protocol, Analytical Method, What You See/Miss, When Deliberating, Output Format (Council Round 2), Output Format (Standalone)
- The complete 7-step deliberation protocol with all [CHECKPOINT] and [VERIFY] markers
- All enforcement rules: dissent quota, novelty gate, agreement check (>70% triggers counterfactual), evidence labeling, anti-recursion / hemlock rule
- Three modes: full (3-round), quick (2-round), duo (dialectic)
- All 20 pre-defined triads with rationale
- All 13 polarity pairs
- Three council profiles: classic, exploration-orthogonal, execution-lean
- Duo polarity pairs table
- All verdict templates (Full, Quick, Duo)

## What Changed and Why

### Agent Paths

**Upstream**: `~/.claude/agents/council-{name}.md`
**This port**: `${extensionPath}/agents/council-{name}.md`

Gemini CLI uses `${extensionPath}` as a variable for the extension's installed path. This is the only Gemini-specific path concept. Every reference in SKILL.md was updated.

### Sub-Agent Dispatch

**Upstream**: `subagent_type: council-name` spawns a true sub-agent process (Claude Code feature). Each member runs as an isolated agent with its own context.

**This port**: The coordinator reads each member's agent file from `${extensionPath}/agents/council-{name}.md` and embodies their persona for that round. Isolation is maintained by re-reading the file at the start of each round.

This is the most significant functional difference. Claude's sub-agent system provides harder isolation (separate process). Gemini's approach is in-context persona switching. In practice, the multi-round protocol and enforcement rules do most of the isolation work — but it's worth noting for evaluators.

**Mitigation**: The Gemini CLI sub-agents feature (preview) would provide harder isolation when stable. This port is written to be forward-compatible: if you can point each round's prompt at a sub-agent TOML file, the SKILL.md protocol supports it.

### Provider Routing

**Upstream**: `scripts/detect-providers.sh` — a bash script that detects installed CLIs (claude, codex, gemini, ollama) at runtime and auto-routes members accordingly.

**This port**: `mcpServers` block in `gemini-extension.json` — declarative registration of MCP servers. Routing is specified in `configs/mcp-provider-slots.yaml` rather than auto-detected.

**Why**: Gemini CLI's MCP integration is the native multi-provider story. The bash auto-detection approach doesn't translate — Gemini doesn't have a concept of "detect other CLIs and exec them." MCP servers are the right abstraction.

**Trade-off**: The upstream auto-detection is zero-config for users with multiple CLIs installed. This port requires explicit configuration (`COUNCIL_ROUTING_PROFILE=mcp-multi` + slots file). That's a step backwards in convenience but a step forwards in correctness and auditability.

### Removed Frontmatter Fields

All agent files had these fields removed:
- `model: opus/sonnet` — Claude-specific tier hint; replaced by MCP server assignment
- `color: *` — Claude UI rendering; no equivalent in Gemini
- `tools: [Read, Grep, Glob, Bash, WebSearch, WebFetch]` — Claude agent tools; Gemini handles tool access separately
- `council.provider_affinity: [anthropic, openai]` — replaced by `council.mcp_affinity: [anthropic]` or `[ollama]`

### Removed Flags

- `--no-auto-route` — Claude-only concept (forced using frontmatter model defaults). In Gemini, without `--mcp-route`, all members already run on the active Gemini model. The flag has no meaning.

### Renamed Flags

- `--models [path]` → `--mcp-route [path]`

The original flag loaded a provider/model YAML and mapped members to external providers via bash exec. The new flag does the same via MCP servers. The semantics are equivalent; the mechanism is different.

### Reference File Extraction

**Upstream**: Triads, polarity pairs, and verdict templates are all inline in SKILL.md (a ~600-line file).

**This port**: Extracted to `skills/council/references/` as separate files. SKILL.md references them with load-on-demand language ("load `${extensionPath}/skills/council/references/triads.md`").

**Why**: Gemini's skill system loads frontmatter at session start and the body on-demand. Keeping SKILL.md focused on the execution sequence and loading reference data only when needed is cleaner and more efficient.

## Known Differences in Behavior

1. **Isolation**: In-context persona switching vs. true sub-agent processes. See "Sub-Agent Dispatch" above.
2. **Routing zero-config**: Upstream auto-detects providers. This port requires explicit MCP setup for multi-provider routing.
3. **No `codex_exec` / `gemini_cli` / `ollama_run` exec methods**: Upstream's SKILL.md has bash exec dispatch for each provider type. This port uses MCP for cross-provider routing instead.

## What This Port Adds (Net-New)

- `configs/mcp-provider-slots.yaml` — all 18 seats mapped to MCP servers with reasoning modes; upstream has no equivalent
- `mcpServers` block in `gemini-extension.json` — registers `claude-code` and `ollama` as optional providers; upstream's multi-provider support relies on detecting installed CLIs
- `--mcp-route` flag — clean flag for activating MCP routing; upstream uses `--models`
