# Council of High Intelligence — Gemini CLI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](CHANGELOG.md)
[![Gemini Extension](https://img.shields.io/badge/Gemini-Extension-blue.svg)](gemini-extension.json)
[![Council Members](https://img.shields.io/badge/council%20members-18-green.svg)](agents/)

**Structured multi-persona deliberation with 18 historical-thinker council members — now native to Gemini CLI, with MCP multi-provider routing.**

```
/council Should we open-source our agent framework?
```

---

## What This Is

This is a Gemini CLI port of [Council of High Intelligence](https://github.com/0xNyk/council-of-high-intelligence) by [@0xNyk](https://github.com/0xNyk). The original is a structured deliberation framework for Claude Code: 18 historical-thinker personas as sub-agents, a coordinator skill, and a multi-round protocol that forces disagreement, cross-examination, and synthesis before any verdict.

This port translates that framework to Gemini CLI's extension model (TOML commands + skills + sub-agents) and adds one net-new capability: **native MCP multi-provider routing**. With a single config file, you can distribute council members across Claude (via the `@anthropic-ai/claude-code` MCP), local Ollama, and Gemini in the same deliberation — giving you genuine cross-provider epistemic diversity, not just persona simulation.

---

## Quickstart

```bash
# 1. Install as a Gemini extension
gemini extensions install https://github.com/Alpsource/council-of-high-intelligence-gemini

# 2. Restart Gemini CLI

# 3. Convene the council
/council Should we rewrite the auth service or add an abstraction layer?
```

That's it. The coordinator auto-selects the best 3-member triad for your problem and runs the full 3-round deliberation.

---

## Modes

| Command | Mode | Rounds | Best for |
|---------|------|--------|----------|
| `/council <problem>` | Full (auto-triad) | 3 | Default — complex decisions |
| `/council:full <problem>` | Full (all 18) | 3 | Maximum coverage |
| `/council:quick <problem>` | Quick | 2 | Fast sanity check |
| `/council:duo <problem>` | Dialectic | 3 | Sharp opposing perspectives |
| `/council:triad <domain> <problem>` | Named triad | 3 | Domain-specific panel |

**Examples:**

```
/council:quick Should we add Redis caching to the auth flow?

/council:duo Should we use microservices or a monolith?

/council:triad ai What are the limits of current foundation models?

/council --members socrates,feynman,ada Is this abstraction sound?
```

---

## Council Members

| Agent | Figure | Domain | Polarity |
|-------|--------|--------|---------|
| `council-aristotle` | Aristotle | Categorization & structure | Classifies everything |
| `council-socrates` | Socrates | Assumption destruction | Questions everything |
| `council-sun-tzu` | Sun Tzu | Adversarial strategy | Reads terrain & competition |
| `council-ada` | Ada Lovelace | Formal systems & abstraction | What can/can't be mechanized |
| `council-aurelius` | Marcus Aurelius | Resilience & moral clarity | Control vs acceptance |
| `council-machiavelli` | Machiavelli | Power dynamics & realpolitik | How actors actually behave |
| `council-lao-tzu` | Lao Tzu | Non-action & emergence | When less is more |
| `council-feynman` | Feynman | First-principles debugging | Refuses unexplained complexity |
| `council-torvalds` | Linus Torvalds | Pragmatic engineering | Ship it or shut up |
| `council-musashi` | Miyamoto Musashi | Strategic timing | The decisive strike |
| `council-watts` | Alan Watts | Perspective & reframing | Dissolves false problems |
| `council-karpathy` | Andrej Karpathy | Neural network intuition & empirical ML | How models actually learn and fail |
| `council-sutskever` | Ilya Sutskever | Scaling frontier & AI safety | When capability becomes risk |
| `council-kahneman` | Daniel Kahneman | Cognitive bias & decision science | Your own thinking is the first error |
| `council-meadows` | Donella Meadows | Systems thinking & feedback loops | Redesign the system, not the symptom |
| `council-munger` | Charlie Munger | Multi-model reasoning & economics | Invert — what guarantees failure? |
| `council-taleb` | Nassim Taleb | Antifragility & tail risk | Design for the tail, not the average |
| `council-rams` | Dieter Rams | User-centered design | Less, but better — the user decides |

---

## What's Different from Upstream

This port is honest about what changed and what's the same.

**Preserved verbatim from upstream:**
- All 18 persona definitions (Identity, Grounding Protocol, Analytical Method, Output Formats)
- The complete deliberation protocol: Problem Restate Gate → Round 1 (blind-first) → Round 2 (cross-examination) → Post-Round Enforcement Scan → Round 3 (crystallization) → Tie-Breaking → Verdict
- All 13 polarity pairs and 20 pre-defined triads
- Three deliberation modes: full, quick, duo
- Three council profiles: classic, exploration-orthogonal, execution-lean
- All enforcement rules: dissent quota, novelty gate, agreement check, anti-recursion

**Changed for Gemini:**
- Agent paths: `~/.claude/agents/` → `${extensionPath}/agents/`
- Dispatch: Claude subagent spawning → read file + embody persona each round
- Provider routing: `detect-providers.sh` script → `mcpServers` in `gemini-extension.json`
- Flag: `--models [path]` → `--mcp-route [path]`
- Flag removed: `--no-auto-route` (Claude-only concept)
- Frontmatter: removed `model`, `color`, `tools`, `provider_affinity`; added `mcp_affinity`
- Reference files: triad taxonomy and verdict templates extracted from SKILL.md into `skills/council/references/` for progressive disclosure

**Net-new (not in upstream):**
- `configs/mcp-provider-slots.yaml` — maps all 18 seats to MCP servers with reasoning modes
- `mcpServers` block in `gemini-extension.json` — registers `claude-code` and `ollama` as optional council providers
- `--mcp-route` flag — activates MCP-based multi-provider deliberation from inside Gemini

---

## MCP Multi-Provider Routing

The key new capability in v0.1. Route different council members to different model providers — Claude for depth, Ollama for privacy, Gemini as the coordinator — all inside a single deliberation session.

### Setup

1. Ensure the MCP servers you want are available:
   - **Claude**: `npm install -g @anthropic-ai/claude-code` (requires Anthropic API key)
   - **Ollama**: [Install Ollama](https://ollama.ai) and pull a model (`ollama pull llama3.3`)

2. Set the routing profile:
   ```bash
   export COUNCIL_ROUTING_PROFILE=mcp-multi
   ```

3. Invoke with MCP routing:
   ```
   /council --mcp-route configs/mcp-provider-slots.yaml --triad ai What are the limits of current foundation models?
   ```

The coordinator reads `configs/mcp-provider-slots.yaml`, assigns each panel member to their MCP server, and routes Round 1, 2, and 3 accordingly.

### Customize Routing

Copy `configs/mcp-provider-slots.yaml`, edit seat assignments, then point at your file:
```
/council --mcp-route configs/my-slots.yaml "Should we open-source?"
```

The default `mcp-provider-slots.yaml` assigns `anthropic`-affinity members (Socrates, Ada, Aurelius, Sutskever, etc.) to `claude-code` and pragmatic/empirical members (Feynman, Torvalds, Karpathy, Meadows, etc.) to `ollama`.

### Polarity Pair Separation

The coordinator enforces a hard constraint: polarity pair members (e.g., Socrates/Feynman, Ada/Machiavelli) are never assigned to the same MCP server. This ensures opposing perspectives come from genuinely different model families, not just different personas on the same model.

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full Gemini extension layout and Claude→Gemini translation table.

---

## Local Development

```bash
git clone https://github.com/Alpsource/council-of-high-intelligence-gemini
cd council-of-high-intelligence-gemini

# Link for live iteration (no reinstall needed on changes)
gemini extensions link $(pwd)

# Validate everything
./scripts/validate.sh

# Local install (manual)
./scripts/install.sh --gemini --dry-run   # preview
./scripts/install.sh --gemini             # install
```

---

## Roadmap

- **v0.2** — Hooks-based telemetry: log every deliberation round to a JSONL file for analysis and replay
- **v0.3** — Unified TOML config (`council.toml`) consumed by Claude, Codex, and Gemini installers — potential upstream contribution
- **v0.4** — Adversarial eval harness: `council eval` subcommand that runs the council against a benchmark set and scores agreement/dissent metrics

---

## Credits

- **Original work**: [Council of High Intelligence](https://github.com/0xNyk/council-of-high-intelligence) by [@0xNyk](https://github.com/0xNyk) — MIT License
- **Persona thinkers**: Aristotle, Socrates, Sun Tzu, Ada Lovelace, Marcus Aurelius, Machiavelli, Lao Tzu, Feynman, Torvalds, Musashi, Alan Watts, Karpathy, Sutskever, Kahneman, Meadows, Munger, Taleb, Dieter Rams
- **Gemini CLI team**: for the extension model that made this port clean

Full attribution: [NOTICE](NOTICE)

---

## License

MIT — see [LICENSE](LICENSE). Original work copyright © 2026 nyk.
