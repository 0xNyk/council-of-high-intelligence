# Verdict Templates Reference

Use these templates verbatim for the final deliverable of each mode.

---

## Council Verdict (Full Mode)

```markdown
## Council Verdict

### Problem
{Original problem statement}

### Council Composition
{Members convened, mode used, and selection rationale}

### Provider Routing
{Routing table: member → provider → model. Note any fallbacks triggered. If single-provider: "Default Gemini model (single provider)."}

### Unresolved Questions
{Questions the council could not answer — inputs needed from user. Lead with what the council does NOT know.}

### Recommended Next Steps
{Concrete actions, ordered by priority}

### Consensus & Agreement
{The position that survived deliberation and what members converged on — or "No consensus reached" with explanation}

### Key Insights by Member
- **{Name}**: {Their most valuable contribution in 1-2 sentences}
- ...

### Points of Disagreement
{Where positions remained irreconcilable}

### Minority Report
{Dissenting positions and their strongest arguments}

### Epistemic Diversity Scorecard
- Perspective spread (1-5): {how orthogonal the viewpoints were}
- Provider spread (1-5): {how distributed across model families — 1 if single provider}
- Evidence mix: {% empirical / mechanistic / strategic / ethical / heuristic}
- Convergence risk: {Low/Medium/High with reason}

### Follow-Up
After acting on this verdict, revisit: Was this verdict useful? Was the recommended action taken? What happened? {This section is a prompt for the user, not filled by the council.}
```

---

## Quick Verdict

```markdown
## Quick Council Verdict

### Problem
{Original problem statement}

### Panel
{Members and selection rationale}

### Recommended Action
{Single concrete recommendation}

### Positions
- **{Name}**: {Core position in 1-2 sentences}
- ...

### Consensus
{Majority position or "Split" with explanation}

### Key Disagreement
{The most important point of divergence}

### Follow-Up
After acting on this verdict, revisit: Was this useful? What happened?
```

---

## Duo Verdict

```markdown
## Duo Verdict

### Problem
{Original problem statement}

### The Dialectic
**{Member A}** ({their lens}) vs **{Member B}** ({their lens})

### What This Means for Your Decision
{How to use these opposing perspectives — the user decides}

### {Member A}'s Position
{Core argument in 2-3 sentences}

### {Member B}'s Position
{Core argument in 2-3 sentences}

### Where They Agree
{Unexpected convergence, if any}

### The Core Tension
{The irreducible disagreement and what drives it}

### Follow-Up
After deciding, revisit: Which perspective proved more useful? What happened?
```
