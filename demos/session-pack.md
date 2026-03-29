# Council Demo Session Pack

This pack gives copy/paste prompts and expected output shape so contributors can quickly sanity-check council behavior.

## Demo A — Full mode: Exploration profile (unknown unknown discovery)

Goal: stress-test framing quality and epistemic diversity.

Prompt:

```bash
/council --profile exploration-orthogonal --triad unknowns Should we expand our AI devtool into enterprise compliance workflows this quarter?
```

Optional multi-provider routing:

```bash
/council --profile exploration-orthogonal --triad unknowns --models configs/provider-model-slots.example.yaml Should we expand our AI devtool into enterprise compliance workflows this quarter?
```

What good output looks like:
- at least 2 non-overlapping objections before consensus
- one explicit counterfactual if early agreement forms
- evidence labels across multiple categories (`empirical`, `mechanistic`, `strategic`, `ethical`, `heuristic`)
- clear unknowns list with concrete data needed

Expected verdict sections:
- Problem, Council Composition, Model/Provider Routing, Consensus Position
- Key Insights by Member, Points of Agreement/Disagreement
- Minority Report, Unresolved Questions, Epistemic Diversity Scorecard, Recommended Next Steps

## Demo B — Full mode: Exploration profile (market-entry triad)

Goal: validate adversarial and incentive-aware reasoning.

Prompt:

```bash
/council --profile exploration-orthogonal --triad market-entry Should we launch in Germany before France for our API platform?
```

What good output looks like:
- explicit competitor/counterparty behavior assumptions
- incentive map by actor class (buyers, legal, competitors, internal teams)
- downside containment plan if launch assumptions fail

## Demo C — Full mode: Execution profile (ship-now triad)

Goal: test speed-to-decision and ship-readiness.

Prompt:

```bash
/council --profile execution-lean --triad ship-now Should we ship release v0.9.4 today if one flaky test remains in CI?
```

What good output looks like:
- binary recommendation with conditions (ship / block / canary)
- explicit rollback triggers
- owner + timeline in next steps

## Demo D — Full mode: Execution profile (stability triad)

Goal: validate reliability-first reasoning.

Prompt:

```bash
/council --profile execution-lean --triad stability Our p95 latency regressed 18% after the new caching layer. Should we revert now or investigate first?
```

What good output looks like:
- mechanism hypothesis list ranked by likelihood
- immediate containment action
- bounded investigation window and decision checkpoint

## Demo E — Quick mode

Goal: test rapid 2-round deliberation with condensed output.

Prompt:

```bash
/council --quick Should we add a Redis cache in front of our Postgres auth queries?
```

What good output looks like:
- 200-word max analyses from each member
- 75-word final positions
- Quick Verdict with: Panel, Positions, Consensus, Key Disagreement, Recommended Action
- Total output significantly shorter than full mode
- Clear, decisive recommendation

## Demo F — Duo mode

Goal: test polarity-pair dialectic with focused tension.

Prompt:

```bash
/council --duo Should we rewrite the monolith into microservices?
```

Expected: auto-selects Aristotle vs Lao Tzu (architecture domain).

What good output looks like:
- Each member argues from their epistemic lens (categories vs emergence)
- Round 2 directly engages the other's specific claims
- Duo Verdict presents both sides without forcing consensus
- The Core Tension section clearly names the irreducible disagreement
- "What This Means for Your Decision" gives actionable framing

Alternative duo test:

```bash
/council --duo --members torvalds,musashi Should we ship the beta this week or wait for the security audit?
```

Expected: Torvalds (ship now) vs Musashi (strategic timing) — classic polarity tension.

## Demo G — Auto-triad selection

Goal: test automatic triad selection from problem analysis.

Prompt:

```bash
/council What's the best pricing model for our developer API?
```

Expected: coordinator analyzes the problem, selects `product` triad (Torvalds + Machiavelli + Watts), states reasoning.

What good output looks like:
- Coordinator explicitly states which triad was selected and why
- Selection rationale references problem keywords and triad domain match
- Full 3-round deliberation follows

## Demo H — AI triad

Goal: test AI-native reasoning with the new Karpathy + Sutskever + Ada triad.

Prompt:

```bash
/council --triad ai Should we fine-tune an open-source LLM or use a frontier API for our customer support agent?
```

Expected: Karpathy assesses ML capability and training dynamics, Sutskever evaluates scaling/safety implications, Ada provides formal analysis of the problem structure.

What good output looks like:
- Karpathy grounds the analysis in actual model capabilities and failure modes
- Sutskever assesses what happens as the system scales (more queries, edge cases, adversarial users)
- Ada identifies the formal properties the system must preserve (accuracy, consistency, safety constraints)
- Productive tension between Karpathy (empirical, build-and-observe) and Ada (formal, prove-before-build)

## Demo I — AI duo

Goal: test the Karpathy vs Sutskever polarity pair.

Prompt:

```bash
/council --duo Should we train our own foundation model or build on top of existing ones?
```

Expected: auto-selects Karpathy vs Sutskever (ai domain keyword).

What good output looks like:
- Karpathy argues from empirical ML experience (training dynamics, data requirements, what you actually learn)
- Sutskever argues from scaling frontier perspective (where's the phase transition, what's the safety boundary)
- Core Tension: build-and-learn vs. pause-and-research
- Neither position forced to converge

## Fast scoring rubric (0-2 each, 10 max)

1. Perspective spread: distinct viewpoints, not paraphrases
2. Decision clarity: actionable recommendation with thresholds
3. Counterfactual depth: strongest alternative is seriously tested
4. Evidence discipline: claims tagged and justified
5. Execution quality: concrete owners, deadlines, rollback criteria

Interpretation:
- 9-10 strong
- 7-8 usable
- <=6 revise profile/triad/model routing
