# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `SKILL.codex.md` — dedicated Codex council coordinator
- Codex install support in `install.sh` (`--codex`, `--codex-only` flags) with reliability hardening
- NVIDIA NIM provider support (`configs/provider-model-slots.nim.example.yaml`)
- Round 2 cross-examination anonymization — members labeled A/B/C to prevent anchoring bias

### Changed
- README updated with header image, quickstart, and open-source best practices

## [1.0.0] - 2026-03-30

### Added
- 18 council member personas: Aristotle, Socrates, Sun Tzu, Ada Lovelace, Marcus Aurelius, Machiavelli, Lao Tzu, Feynman, Torvalds, Musashi, Watts, Karpathy, Sutskever, Kahneman, Meadows, Munger, Taleb, Rams
- 3-round structured deliberation protocol: Problem Restate Gate → Blind Analysis → Cross-Examination → Crystallization → Verdict
- Post-round enforcement scan: dissent quota, novelty gate, agreement check (>70% triggers mandatory counterfactual), evidence labeling, anti-recursion rule
- Quick mode (2-round), Duo mode (2-member deliberation), pre-defined triads by domain
- Multi-provider auto-detection (`scripts/detect-providers.sh`) — routes council members across Claude, Codex (OpenAI), and Ollama
- Execution profiles (`configs/auto-route-defaults.yaml`) and simulation checklist (`scripts/council-simulation-checklist.sh`)
- Provider model slot template (`configs/provider-model-slots.example.yaml`)

### Fixed
- Default OpenAI model for Codex set to `gpt-5.4` (E2E test found o3/o4-mini unavailable on standard ChatGPT accounts)

[Unreleased]: https://github.com/0xNyk/council-of-high-intelligence/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/0xNyk/council-of-high-intelligence/releases/tag/v1.0.0
