# Council of High Intelligence

A Claude Code skill that convenes historical thinkers for multi-perspective deliberation on complex problems.

LLMs make you think they are smart, but when things get complex their reasoning can fall short. This council uses structured disagreement between diverse intellectual traditions to surface blind spots, challenge assumptions, and produce better decisions.

## The 13 Council Members

| Agent | Figure | Domain | Model | Polarity |
|-------|--------|--------|-------|----------|
| `council-aristotle` | Aristotle | Categorization & structure | opus | Classifies everything |
| `council-socrates` | Socrates | Assumption destruction | opus | Questions everything |
| `council-sun-tzu` | Sun Tzu | Adversarial strategy | sonnet | Reads terrain & competition |
| `council-ada` | Ada Lovelace | Formal systems & abstraction | sonnet | What can/can't be mechanized |
| `council-aurelius` | Marcus Aurelius | Resilience & moral clarity | opus | Control vs acceptance |
| `council-machiavelli` | Machiavelli | Power dynamics & realpolitik | sonnet | How actors actually behave |
| `council-lao-tzu` | Lao Tzu | Non-action & emergence | opus | When less is more |
| `council-feynman` | Feynman | First-principles debugging | sonnet | Refuses unexplained complexity |
| `council-torvalds` | Linus Torvalds | Pragmatic engineering | sonnet | Ship it or shut up |
| `council-musashi` | Miyamoto Musashi | Strategic timing | sonnet | The decisive strike |
| `council-watts` | Alan Watts | Perspective & reframing | opus | Dissolves false problems |
| `council-karpathy` | Andrej Karpathy | Neural network intuition & empirical ML | sonnet | How models actually learn and fail |
| `council-sutskever` | Ilya Sutskever | Scaling frontier & AI safety | opus | When capability becomes risk |

## Polarity Pairs

The members are chosen as deliberate counterweights:

- **Socrates vs Feynman** — Both question, but Socrates destroys top-down; Feynman rebuilds bottom-up
- **Aristotle vs Lao Tzu** — Aristotle classifies everything; Lao Tzu says structure IS the problem
- **Sun Tzu vs Aurelius** — Sun Tzu wins external games; Aurelius governs the internal one
- **Ada vs Machiavelli** — Ada abstracts toward formal purity; Machiavelli anchors in messy human incentives
- **Torvalds vs Watts** — Torvalds ships concrete solutions; Watts questions whether the problem exists
- **Musashi vs Torvalds** — Musashi waits for the perfect moment; Torvalds says ship it now
- **Karpathy vs Sutskever** — Build it, observe it, iterate; vs pause, research, ensure safety first
- **Karpathy vs Ada** — Empirical ML intuition vs formal systems theory

## Three Deliberation Modes

### Full Mode (default)
3-round structured deliberation: independent analysis → cross-examination → final positions.

```
/council Should we open-source our agent framework?
/council --triad strategy What's our competitive moat?
/council --full What is the right pricing model?
```

### Quick Mode (`--quick`)
2-round rapid analysis for simpler decisions. No cross-examination.

```
/council --quick Should we add caching here?
/council --quick --triad shipping Should we release today?
```

### Duo Mode (`--duo`)
2-member dialectic using polarity pairs. Great for exploring tensions.

```
/council --duo Should we use microservices or monolith?
/council --duo --members torvalds,ada Is this abstraction worth it?
```

## Pre-defined Triads

| Domain | Triad | Rationale |
|--------|-------|-----------|
| `architecture` | Aristotle + Ada + Feynman | Classify + formalize + simplicity-test |
| `strategy` | Sun Tzu + Machiavelli + Aurelius | Terrain + incentives + moral grounding |
| `ethics` | Aurelius + Socrates + Lao Tzu | Duty + questioning + natural order |
| `debugging` | Feynman + Socrates + Ada | Bottom-up + assumption testing + formal verification |
| `innovation` | Ada + Lao Tzu + Aristotle | Abstraction + emergence + classification |
| `conflict` | Socrates + Machiavelli + Aurelius | Expose + predict + ground |
| `complexity` | Lao Tzu + Aristotle + Ada | Emergence + categories + formalism |
| `risk` | Sun Tzu + Aurelius + Feynman | Threats + resilience + empirical verification |
| `shipping` | Torvalds + Musashi + Feynman | Pragmatism + timing + first-principles |
| `product` | Torvalds + Machiavelli + Watts | Ship it + incentives + reframing |
| `founder` | Musashi + Sun Tzu + Torvalds | Timing + terrain + engineering reality |
| `ai` | Karpathy + Sutskever + Ada | Empirical ML + scaling frontier + formal limits |
| `ai-product` | Karpathy + Torvalds + Machiavelli | ML capability + shipping pragmatism + incentives |
| `ai-safety` | Sutskever + Aurelius + Socrates | Safety frontier + moral clarity + assumption destruction |

## Council Profiles

### `classic` (default)
All 11 members with domain triads above. Best for broad deliberation.

### `exploration-orthogonal`
10-member panel for discovery and "unknown unknowns" reduction:
- Socrates, Feynman, Sun Tzu, Machiavelli, Ada, Lao Tzu, Aurelius, Torvalds, Karpathy, Sutskever
- Profile triads: `unknowns`, `market-entry`, `system-design`, `reframing`, `ai-frontier`

### `execution-lean`
5-member panel for fast decision-to-action:
- Torvalds, Feynman, Sun Tzu, Aurelius, Ada
- Profile triads: `ship-now`, `launch-strategy`, `stability`

## Multi-provider / Multi-model Exploration

Use `--models` to spread members across AI providers and reduce model monoculture.

```
/council --profile exploration-orthogonal --models configs/provider-model-slots.example.yaml Should we pivot?
```

Starter template: `configs/provider-model-slots.example.yaml`

## Deliberation Protocol

### Full Mode
1. **Round 1: Independent Analysis (blind-first)** — all members analyze in parallel (400 words max)
2. **Round 2: Cross-Examination** — members challenge each other (300 words, must engage 2+ others)
3. **Round 3: Synthesis** — final 100-word position statements

### Quick Mode
1. **Round 1: Rapid Analysis** — all members analyze in parallel (200 words max)
2. **Round 2: Final Positions** — 75-word crystallization

### Duo Mode
1. **Round 1: Opening Positions** — both state positions (300 words)
2. **Round 2: Direct Response** — engage opponent's claims (200 words)
3. **Round 3: Final Statements** — 50-word positions

Anti-recursion enforcement prevents Socrates from infinite questioning. Anti-convergence enforcement requires dissent quota + counterfactual pass when agreement forms too early. Tie-breaking uses 2/3 majority with domain expert weighting.

## Installation

```bash
./install.sh
```

Optional flags:

```bash
./install.sh --claude-dir /path/to/.claude   # Non-default config directory
./install.sh --dry-run                        # Preview without writing
./install.sh --copy-configs                   # Also install model routing templates
```

Or manually:

```bash
mkdir -p ~/.claude/agents ~/.claude/skills/council
cp agents/council-*.md ~/.claude/agents/
cp SKILL.md ~/.claude/skills/council/SKILL.md
```

Then restart Claude Code. The `/council` command will be available immediately.

## Quick Simulation Checklist

Run this before release or after profile edits:

```bash
./scripts/council-simulation-checklist.sh
```

## Demo Session Pack

Use the ready-to-run examples to test all modes:
- `demos/session-pack.md`

## Requirements

- [Claude Code](https://claude.ai/claude-code) CLI
- Agent subagent support (enabled by default)

## Contributing

Contributions welcome. Read the [contribution guidelines](CONTRIBUTING.md) first.

## ❤️ Support the Project

If you find this project useful, consider supporting my open-source work.

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-support-orange?logo=buymeacoffee)](https://buymeacoffee.com/nyk_builderz)

**Solana donations**

`BYLu8XD8hGDUtdRBWpGWu5HKoiPrWqCxYFSh4oxXuvPg`

## License

[![CC0](https://licensebuttons.net/p/zero/1.0/88x31.png)](https://creativecommons.org/publicdomain/zero/1.0/)

To the extent possible under law, the authors have waived all copyright and
related or neighboring rights to this work.

---

<p align="center">
  <a href="https://star-history.com/#0xNyk/council-of-high-intelligence&Date">
    <img src="https://api.star-history.com/svg?repos=0xNyk/council-of-high-intelligence&type=Date" alt="Star History" width="400">
  </a>
</p>
