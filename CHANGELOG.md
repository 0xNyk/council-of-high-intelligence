# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Structured stance voting + deterministic weighted tie-break.** The final round (full Round 3 / quick Round 2) now requires each member to emit a machine-parseable `STANCE: <option> | CONFIDENCE: … | DEALBREAKER: …` line, so consensus is a counted weighted tally rather than a prose impression. STEP 6 specifies the exact math: `W_option ≥ (2/3) × W_total`, with the on-domain seat carrying 1.5×. New **Vote Tally** field in the full and quick verdict templates records `option → weight` and which seat carried the weight. Mirrored in `SKILL.codex.md`.
- Cursor CLI provider support (`cursor_cli` archetype) — sixth dispatch path alongside subagent / codex_exec / gemini_cli / ollama_run / openai_compatible_api. Auto-detected via the `cursor-agent` binary; members run headless and read-only (`cursor-agent -p --mode ask --model <id>`). Cursor is a model aggregator (GPT-5.x / Claude / Gemini / Grok through one CLI), so routing treats it as a single provider for spread and steers diversity seats to cross-family models to avoid duplicating Anthropic bias. New `configs/provider-model-slots.cursor.example.yaml`, `cursor_cli` tiers in `configs/auto-route-defaults.yaml`, and `cursor_cli` as a valid `--chairman` tag.

### Changed
- **Domain-weight seat (1.5×) is now designated at panel selection (STEP 0), before any positions exist** — previously chosen at tie-break time, which let the coordinator pick the heavyweight after seeing votes. Locking it up front removes that nudge.
- README "Enforcement Mechanisms" rewritten to state the actual forcing function (bounded round budget + anti-recursion guards) and that genuine splits escalate to the user instead of being forced into consensus.

## [1.1.0] - 2026-05-21

### Added
- `SKILL.codex.md` — dedicated Codex council coordinator
- Codex install support in `install.sh` (`--codex`, `--codex-only` flags) with reliability hardening
- NVIDIA NIM provider support (`configs/provider-model-slots.nim.example.yaml`) — auto-detection via `NVIDIA_API_KEY`
- Round 2 cross-examination anonymization — peer Round 1 outputs are masked behind stable `Member A/B/C` labels in full and quick modes (Choi et al., arXiv:2510.07517; Karpathy `llm-council`)
- Anti-conformity directive — Round 2 prompts in all three modes now require members to name the specific flaw in their earlier argument before updating; defends correct prior positions against social pressure (Cui et al., Free-MAD, arXiv:2509.11035)
- Explicit Chairman role — synthesis (STEP 7, QUICK STEP 3, DUO STEP 4) is performed by a named model selected via STEP 1.7; new `--chairman <name>` flag, `chairman_defaults:` block in `configs/auto-route-defaults.yaml`, and a hard constraint that Chairman cannot be a panel member
- Verdict actionability sections — `Acceptable Compromises`, `Kill Criteria`, `Concrete Next Step` are now required in every verdict (full mode); quick and duo modes require subsets per the per-mode policy
- `openai_compatible_api` provider archetype — fifth dispatch path alongside subagent / codex_exec / antigravity_cli / ollama_run; routes NIM seats (and future Together / Fireworks / vLLM) via `/chat/completions` with credentials resolved from `api_key_env` at runtime
- Session Metadata block (`schema_version: 1`) — appended to every verdict with `mode`, `panel_size`, `rounds_run`, `tools_used`, `provider_count`, `fallbacks_triggered`, plus best-effort token / duration estimates
- CI hardening — `.gitattributes` for LF normalization, `.github/workflows/lint.yml` (shellcheck + markdownlint), `.github/workflows/release.yml` (tarball + auto release notes from CHANGELOG on `v*.*.*` tag), `CHANGELOG.md` itself

### Changed
- README updated with header image, quickstart, and open-source best practices

### Fixed
- Dead code in `scripts/council-simulation-checklist.sh` that tripped ShellCheck SC2317 under CI

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

[Unreleased]: https://github.com/0xNyk/council-of-high-intelligence/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/0xNyk/council-of-high-intelligence/releases/tag/v1.1.0
[1.0.0]: https://github.com/0xNyk/council-of-high-intelligence/releases/tag/v1.0.0
