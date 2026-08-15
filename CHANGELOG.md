# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Roster validation drift guard** — `scripts/validate-roster.py`, wired into CI. Runs 166 structural checks that `SKILL.md` prose and `agents/*.md` frontmatter describe the same council: profile sizes and enumerated member lists against `profiles:` tags, polarity pairs resolvable/mutual/mirrored in the Polarity Pairs list, `reasoning_method` uniqueness (DMAD), triad references, and roster-table parity. Panel selection reads the frontmatter while the coordinator reads the prose, so drift silently seats the wrong members with no visible error. Complements `council-simulation-checklist.sh`, which greps for protocol features rather than checking roster consistency.

### Fixed
- **Socrates/Watts polarity pair was missing from the Polarity Pairs list** — mutual in frontmatter and present in the duo table, but absent from the list the coordinator reads. Added to `SKILL.md` and `SKILL.opencode.md`.
- **Sutskever/Machiavelli polarity pair was missing from the Polarity Pairs list** — the frontmatter reciprocation landed in #51 (@xiaolai); this adds the matching prose entry to `SKILL.md` and `SKILL.opencode.md`, where the duo table already carried it.

The two frontmatter drifts this validator was written to catch — Aristotle's stray
`exploration-orthogonal` tag (#50) and the one-directional Sutskever/Machiavelli pair
(#51) — were found and fixed independently by @xiaolai on 2026-07-06, six weeks before
the validator existed. Both are merged. The validator's value is preventing the next
one, not having found these.

## [1.2.0] - 2026-07-04

### Added
- **Claude Code plugin-marketplace support** (#45) — `.claude-plugin/plugin.json` + `marketplace.json`; install with `/plugin marketplace add 0xNyk/council-of-high-intelligence` then `/plugin install council@council-of-high-intelligence`. Root `SKILL.md` remains the single source of truth via a `skills/council/` symlink; a new Asset Resolution section resolves agents/scripts/configs from either the install.sh layout or `${CLAUDE_PLUGIN_ROOT}`.
- **Confidence-weighted vote tally** (#44) — a member's vote weight is now base weight (1.0, or 1.5× domain seat) × confidence factor from their `STANCE:` line (`high 1.0 / med 0.75 / low 0.5`). `W_total` stays at full base weights, so a hesitant council raises its own consensus bar and escalates to the user rather than forcing a verdict (Roundtable Policy, arXiv:2509.16839; ConfMAD, arXiv:2509.14034).
- **Per-member `reasoning_method` frontmatter** (E3 / DMAD, arXiv:2410.12853) (#44) — all 18 personas declare a distinct reasoning method (elenchic-questioning, tail-stress-testing, causal-loop-mapping, …) and Round 1 prompts direct each member to reason via their method: method diversity, not just persona diversity.
- **Project-level `./.council.yaml` overrides** (E7) (#44) — pin `profile`/`triad`/`members`/`chairman`/`models`/`no_auto_route` per project; CLI flags always win.
- Standard repo furniture (#42) — `.gitignore`, `SECURITY.md`, `FUNDING.yml`, bug/feature/provider issue templates, and a PR template with a three-file protocol-parity checklist.
- **Structured stance voting + deterministic weighted tie-break.** The final round (full Round 3 / quick Round 2) now requires each member to emit a machine-parseable `STANCE: <option> | CONFIDENCE: … | DEALBREAKER: …` line, so consensus is a counted weighted tally rather than a prose impression. STEP 6 specifies the exact math: `W_option ≥ (2/3) × W_total`, with the on-domain seat carrying 1.5×. New **Vote Tally** field in the full and quick verdict templates records `option → weight` and which seat carried the weight. Mirrored in `SKILL.codex.md`.
- Cursor CLI provider support (`cursor_cli` archetype) — sixth dispatch path alongside subagent / codex_exec / gemini_cli / ollama_run / openai_compatible_api. Auto-detected via the `cursor-agent` binary; members run headless and read-only (`cursor-agent -p --mode ask --model <id>`). Cursor is a model aggregator (GPT-5.x / Claude / Gemini / Grok through one CLI), so routing treats it as a single provider for spread and steers diversity seats to cross-family models to avoid duplicating Anthropic bias. New `configs/provider-model-slots.cursor.example.yaml`, `cursor_cli` tiers in `configs/auto-route-defaults.yaml`, and `cursor_cli` as a valid `--chairman` tag.

### Changed
- **Domain-weight seat (1.5×) is now designated at panel selection (STEP 0), before any positions exist** — previously chosen at tie-break time, which let the coordinator pick the heavyweight after seeing votes. Locking it up front removes that nudge.
- README "Enforcement Mechanisms" rewritten to state the actual forcing function (bounded round budget + anti-recursion guards) and that genuine splits escalate to the user instead of being forced into consensus.
- **CI drift guards are now real** (#42) — `council-simulation-checklist.sh` executes in CI (it never ran before), extended with full `SKILL.gemini.md` parity checks and a three-file STANCE/Vote-Tally/1.5×/2-3-threshold parity gate; markdownlint's variadic `--disable` was missing its trailing `--` and silently linted zero files — rule selection now lives in `.markdownlint.json` and covers all doc files.
- `install.sh` derives the generated `gemini-extension.json` version from CHANGELOG instead of a hardcoded string; model IDs reconciled across configs/docs (`gemini-3-pro`, `gpt-5.4` generation); README/CLAUDE.md document the `--gemini` install path and marketplace install.

### Fixed
- **`SKILL.gemini.md` drift regression** (#42) — the Gemini coordinator was missing structured stance voting, the weighted 2/3 tie-break, and the Vote Tally verdict field entirely; `SKILL.codex.md` referenced a Vote Tally field its own verdict template lacked.
- `SKILL.md` `classic` profile said "All 11 members" — the roster is 18 (#42).
- Shell-injection surface in external dispatch templates — prompts now route through quoted heredocs instead of being inlined into double-quoted argv; API keys no longer appear in `ps`-visible curl argv (#42).
- Tracked `.DS_Store` and a stray `.gstack` error log removed; junk excluded from release tarballs (#42).

## [1.1.0] - 2026-05-21

### Added
- `SKILL.codex.md` — dedicated Codex council coordinator
- Codex install support in `install.sh` (`--codex`, `--codex-only` flags) with reliability hardening
- NVIDIA NIM provider support (`configs/provider-model-slots.nim.example.yaml`) — auto-detection via `NVIDIA_API_KEY`
- Round 2 cross-examination anonymization — peer Round 1 outputs are masked behind stable `Member A/B/C` labels in full and quick modes (Choi et al., arXiv:2510.07517; Karpathy `llm-council`)
- Anti-conformity directive — Round 2 prompts in all three modes now require members to name the specific flaw in their earlier argument before updating; defends correct prior positions against social pressure (Cui et al., Free-MAD, arXiv:2509.11035)
- Explicit Chairman role — synthesis (STEP 7, QUICK STEP 3, DUO STEP 4) is performed by a named model selected via STEP 1.7; new `--chairman <name>` flag, `chairman_defaults:` block in `configs/auto-route-defaults.yaml`, and a hard constraint that Chairman cannot be a panel member
- Verdict actionability sections — `Acceptable Compromises`, `Kill Criteria`, `Concrete Next Step` are now required in every verdict (full mode); quick and duo modes require subsets per the per-mode policy
- `openai_compatible_api` provider archetype — fifth dispatch path alongside subagent / codex_exec / gemini_cli / ollama_run; routes NIM seats (and future Together / Fireworks / vLLM) via `/chat/completions` with credentials resolved from `api_key_env` at runtime
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

[Unreleased]: https://github.com/0xNyk/council-of-high-intelligence/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/0xNyk/council-of-high-intelligence/releases/tag/v1.2.0
[1.1.0]: https://github.com/0xNyk/council-of-high-intelligence/releases/tag/v1.1.0
[1.0.0]: https://github.com/0xNyk/council-of-high-intelligence/releases/tag/v1.0.0
