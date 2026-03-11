# Council of High Intelligence

A Claude Code skill that convenes historical thinkers for multi-perspective deliberation on complex problems.

LLMs make you think they are smart, but when things get complex their reasoning can fall short. This council uses structured disagreement between diverse intellectual traditions to surface blind spots, challenge assumptions, and produce better decisions.

## The 11 Council Members

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

## Polarity Pairs

The members are chosen as deliberate counterweights:

- **Socrates vs Feynman** — Both question, but Socrates destroys top-down; Feynman rebuilds bottom-up
- **Aristotle vs Lao Tzu** — Aristotle classifies everything; Lao Tzu says structure IS the problem
- **Sun Tzu vs Aurelius** — Sun Tzu wins external games; Aurelius governs the internal one
- **Ada vs Machiavelli** — Ada abstracts toward formal purity; Machiavelli anchors in messy human incentives
- **Torvalds vs Watts** — Torvalds ships concrete solutions; Watts questions whether the problem exists
- **Musashi vs Torvalds** — Musashi waits for the perfect moment; Torvalds says ship it now

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

## Usage

```
/council [problem description]
/council --triad architecture Should we use a monorepo or polyrepo?
/council --full What is the right pricing strategy for our SaaS product?
/council --members socrates,feynman,ada Is our caching strategy correct?
```

## Deliberation Protocol

1. **Round 1: Independent Analysis** — All selected members analyze the problem in parallel (400 words max each)
2. **Round 2: Cross-Examination** — Members challenge each other sequentially (300 words, must engage 2+ others)
3. **Round 3: Synthesis** — Final 100-word position statements. Socrates gets one last question.

Anti-recursion enforcement prevents Socrates from infinite questioning. Tie-breaking uses 2/3 majority with domain expert weighting.

## Installation

```bash
./install.sh
```

Or manually:

```bash
# Copy agents
cp agents/council-*.md ~/.claude/agents/

# Copy skill
mkdir -p ~/.claude/skills/council
cp SKILL.md ~/.claude/skills/council/SKILL.md
```

Then restart Claude Code. The `/council` command will be available immediately.

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
