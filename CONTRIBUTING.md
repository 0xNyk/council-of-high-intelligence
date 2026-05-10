# Contributing

## Development Setup

```bash
git clone https://github.com/Alpsource/council-of-high-intelligence-gemini
cd council-of-high-intelligence-gemini

# Link as a live Gemini extension (changes visible without reinstall)
gemini extensions link $(pwd)
```

## Branching

```
main       — tagged releases only
develop    — integration branch
feat/*     — new capabilities
fix/*      — bug fixes
docs/*     — documentation only
```

## Validation (run before every commit)

```bash
# Smoke test: JSON validity, TOML validity, frontmatter checks, required files
./scripts/validate.sh

# Shell script linting
shellcheck scripts/*.sh

# Dry-run installer
./scripts/install.sh --dry-run
./scripts/install.sh --dry-run --gemini
```

## Adding or Modifying Agents

Agent files live in `agents/council-<name>.md`. Required frontmatter fields:
- `name` — must match filename (`council-<name>`)
- `description` — one-line summary used for skill discovery

Preserve section order per the upstream convention:
Identity → Grounding Protocol → Analytical Method → What You See → What You Miss → When Deliberating → Output Format (Council Round 2) → Output Format (Standalone)

## Modifying the Skill

After changes to `skills/council/SKILL.md`, run at least one deliberation in each mode (full, quick, duo) to verify the protocol still works end-to-end.

## Pull Requests

- Keep PRs focused (one concern per PR)
- Update `CHANGELOG.md` under `[Unreleased]`
- Run `./scripts/validate.sh` and confirm all checks pass
- Tag the upstream original in the PR description if you're back-porting a persona fix
