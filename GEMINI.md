# Council of High Intelligence — Gemini Extension

This extension provides structured multi-persona deliberation with 18 historical-thinker
council members. Use it to analyze complex decisions from multiple perspectives before acting.

## Commands

| Command | Description |
|---------|-------------|
| `/council <problem>` | Full deliberation (auto-selects best triad) |
| `/council:full <problem>` | All 18 members, 3-round protocol |
| `/council:quick <problem>` | 2-round rapid analysis |
| `/council:duo <problem>` | 2-member dialectic via polarity pair |
| `/council:triad <domain> <problem>` | Predefined 3-member combination |

## Skill

The coordinator logic lives in `skills/council/SKILL.md`. Gemini loads the frontmatter
at session start and the body on-demand when a `/council` command is invoked.

## Council Members

18 personas: Aristotle, Socrates, Sun Tzu, Ada Lovelace, Marcus Aurelius, Machiavelli,
Lao Tzu, Feynman, Torvalds, Musashi, Alan Watts, Karpathy, Sutskever, Kahneman,
Meadows, Munger, Taleb, Dieter Rams.

Each persona file is in `agents/council-<name>.md` with its analytical lens, grounding
protocol, deliberation output format, and standalone output format.

## MCP Multi-Provider Routing (v0.1 net-new capability)

To run a deliberation with members distributed across Claude, Ollama, and Gemini:

1. Ensure the `claude-code` and/or `ollama` MCP servers declared in `gemini-extension.json`
   are available on your machine.
2. Set the routing profile:
   ```
   export COUNCIL_ROUTING_PROFILE=mcp-multi
   ```
3. Optionally customize seat assignments in `configs/mcp-provider-slots.yaml`.
4. Invoke `/council` — the coordinator will route each member to its assigned MCP server.

Without MCP servers configured, all members run on the active Gemini model (default behavior).

## Reference Files

- `skills/council/references/triads.md` — 20 predefined 3-member panels by domain
- `skills/council/references/polarity-pairs.md` — 13 opposing member pairs
- `skills/council/references/verdict-templates.md` — Full / Quick / Duo verdict formats

## Configuration

| Setting | Env var | Default | Description |
|---------|---------|---------|-------------|
| `ROUTING_PROFILE` | `COUNCIL_ROUTING_PROFILE` | `auto` | `auto` or `mcp-multi` |
| `MCP_SLOTS_PATH` | `COUNCIL_MCP_SLOTS_PATH` | `` | Custom slots YAML path |
