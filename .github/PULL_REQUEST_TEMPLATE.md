## What & why

<!-- One paragraph: what changes and what problem it solves. Link the issue if there is one. -->

## Protocol parity

Protocol features live in four coordinator files that must not drift:

- [ ] Change applied to `SKILL.md` (or N/A)
- [ ] Mirrored in `SKILL.codex.md` (or N/A / host-exempt with reason)
- [ ] Mirrored in `SKILL.gemini.md` (or N/A / host-exempt with reason)
- [ ] Mirrored in `SKILL.opencode.md` (or N/A / host-exempt with reason)

## Validation

- [ ] `./scripts/council-simulation-checklist.sh` passes
- [ ] `./install.sh --dry-run` passes (plus `--codex` / `--gemini` / `--opencode` if installer changed)
- [ ] Tested at least one mode (full/quick/duo) if protocol behavior changed

## Evidence

<!-- For protocol changes: cite the paper/benchmark/observation motivating it (repo convention — see issue #28). For fixes: how to reproduce the bug. -->
