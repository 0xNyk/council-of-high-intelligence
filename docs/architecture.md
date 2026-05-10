# Architecture

## Gemini Extension Layout

```
council-of-high-intelligence-gemini/
├── gemini-extension.json          # Extension manifest (entry point)
├── GEMINI.md                      # Context file loaded at session start
├── commands/
│   ├── council.toml               # /council → main entry point
│   └── council/
│       ├── quick.toml             # /council:quick
│       ├── duo.toml               # /council:duo
│       ├── full.toml              # /council:full
│       └── triad.toml             # /council:triad <domain>
├── skills/
│   └── council/
│       ├── SKILL.md               # Coordinator logic (loaded on-demand)
│       └── references/
│           ├── triads.md          # 20 pre-defined triads + 3 profiles
│           ├── polarity-pairs.md  # 13 polarity pairs + duo table
│           └── verdict-templates.md # Full / Quick / Duo verdict formats
├── agents/
│   └── council-*.md               # 18 persona files
└── configs/
    ├── auto-route-defaults.yaml   # Provider → model tier mapping
    ├── provider-model-slots.yaml  # Example seat mapping (exploration-orthogonal)
    └── mcp-provider-slots.yaml    # MCP server → member routing (all 18 seats)
```

## Claude → Gemini Translation Table

| Claude Code concept | Gemini CLI equivalent | Notes |
|---|---|---|
| `~/.claude/agents/council-*.md` | `${extensionPath}/agents/council-*.md` | Path variable substitution |
| `SKILL.md` in `~/.claude/skills/council/` | `skills/council/SKILL.md` | Same structure |
| `/council` slash command | `commands/council.toml` | TOML `prompt` field |
| `subagent_type: council-*` | Read file + embody persona | No native sub-agent spawning needed |
| `model: opus` frontmatter | Removed → `mcp_affinity` | Model selected by MCP server |
| `tools: [...]` frontmatter | Removed | Gemini handles tool access |
| `provider_affinity: [anthropic]` | `mcp_affinity: [anthropic]` | Maps to MCP server name |
| `detect-providers.sh` | `mcpServers` in manifest | Declarative vs. dynamic |
| `--models [path]` flag | `--mcp-route [path]` | Same purpose, MCP-native |
| `--no-auto-route` flag | Removed | MCP routing is always declarative |
| Multi-provider via Bash exec | MCP server routing | `claude-code`, `ollama` MCP servers |

## How Commands Activate the Skill

```
User: /council Should we open-source?
          ↓
commands/council.toml (TOML prompt)
          ↓
  "Read skills/council/SKILL.md and follow coordinator sequence"
          ↓
Gemini reads SKILL.md on-demand (progressive disclosure)
          ↓
Coordinator: parse flags → select panel → route providers
          ↓
For each member: read ${extensionPath}/agents/council-{name}.md
                 embody persona
                 run assigned round
          ↓
Synthesize verdict using references/verdict-templates.md
```

## MCP Multi-Provider Routing

When `COUNCIL_ROUTING_PROFILE=mcp-multi` or `--mcp-route` is passed:

```
configs/mcp-provider-slots.yaml
          ↓
Coordinator reads seat assignments
          ↓
For members on claude-code MCP:
  → gemini-extension.json mcpServers.claude-code
  → npx @anthropic-ai/claude-code --mcp
  → Routes prompt to Claude model specified in slots file

For members on ollama MCP:
  → gemini-extension.json mcpServers.ollama
  → ollama serve at localhost:11434
  → Routes prompt to Ollama model specified in slots file

For members with no MCP assignment (fallback):
  → Active Gemini model
```

Polarity pair members (e.g., Socrates/Feynman) are always on different MCP servers (hard constraint enforced in STEP 1 of SKILL.md).

## Deliberation Protocol (preserved from upstream)

```
STEP 0   Parse mode + select panel
STEP 1   Provider detection + routing
STEP 1.5 Problem Restate Gate (each member restates before analysis)
STEP 2   Round 1 — independent analysis, parallel, blind-first
STEP 3   Round 2 — cross-examination (parallel for ≥5, sequential for ≤4)
STEP 4   Post-Round Enforcement Scan
           [VERIFY] Dissent quota (≥2 non-overlapping objections)
           [VERIFY] Novelty gate (≥1 new claim per member)
           [VERIFY] Agreement check (>70% consensus triggers counterfactual)
           [VERIFY] Evidence labels (empirical | mechanistic | strategic | ethical | heuristic)
           [VERIFY] Anti-recursion (Socrates hemlock rule, exchange depth limits)
STEP 5   Round 3 — final crystallization, parallel
STEP 6   Tie-breaking (2/3 majority → consensus; domain expert 1.5× weight)
STEP 7   Synthesize verdict (Full / Quick / Duo template)
```
