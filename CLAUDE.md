# Council of High Intelligence

## Architecture

- `SKILL.md` — coordinator protocol with execution sequence, modes, and verdict templates
- `agents/council-*.md` — 18 member personas with YAML frontmatter
- `install.sh` — copies agents and skill to `~/.claude/`
- `configs/` — provider/model routing templates
- `demos/` — example prompts and scoring rubric
- `scripts/` — validation checklist

## Conventions

### Agent files
- Section order: Identity → Grounding Protocol → Analytical Method → What You See → What You Miss → When Deliberating → Output Format (Council Round 2) → Output Format (Standalone)
- Grounding Protocol appears **immediately after Identity** (LLMs weight earlier instructions more heavily)
- "What You See" and "What You Miss" sections: ≤3 sentences each
- Every agent gets a Council Round 2 output format with structured headers (Disagree, Strengthened by, Position Update, Evidence Label)

### SKILL.md
- Coordinator instructions are an **execution sequence** with numbered STEPs and `[CHECKPOINT]`/`[VERIFY]` markers
- Three modes: full (3-round), quick (2-round), duo (dialectic)
- Reference tables (triads, profiles, polarity pairs) are below the execution sequence, not mixed in

### Testing
- Always run `./scripts/council-simulation-checklist.sh` after changes
- Always run `./install.sh --dry-run` to verify installation
- Test at least one mode (full/quick/duo) after protocol changes

### Style
- Keep agent prompts tight — no filler sentences
- Grounding protocols use specific constraints ("maximum 2 analogies", "3-level depth limit"), not vague guidance
- Each agent's Council Round 2 "Disagree" prompt is tailored to their epistemic lens
