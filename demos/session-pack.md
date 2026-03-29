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

## Demo J — Decision triad (Kahneman + Munger + Aurelius)

Goal: test cognitive bias detection, inversion reasoning, and moral clarity.

Prompt:

```bash
/council --triad decision Should we acquire this competitor or build the feature ourselves?
```

What good output looks like:
- Kahneman identifies specific biases (sunk cost, overconfidence, anchoring on acquisition price)
- Munger inverts ("what would guarantee this acquisition destroys value?") and checks circle of competence
- Aurelius draws the control boundary and identifies the duty regardless of difficulty
- Productive tension between Kahneman's bias skepticism and Munger's multi-model confidence

## Demo K — Uncertainty duo (Taleb vs Karpathy)

Goal: test the tail risk vs empirical scaling tension.

Prompt:

```bash
/council --duo --members taleb,karpathy Should we deploy this ML model to production with 99.2% accuracy?
```

What good output looks like:
- Taleb classifies the domain (Mediocristan vs Extremistan) and assesses fragility of the 99.2% claim
- Karpathy assesses what the model actually learned, where the 0.8% errors cluster, and failure modes
- Core tension: Taleb warns about catastrophic tail scenarios hidden in the 0.8%; Karpathy argues empirical observation reveals more than theoretical tail analysis
- Duo Verdict presents both without forcing consensus

## Demo L — Design triad (Rams + Torvalds + Watts)

Goal: test user-centered design reasoning alongside engineering pragmatism and philosophical reframing.

Prompt:

```bash
/council --triad design Our onboarding flow has 8 steps and 40% drop-off. Should we simplify or add more guidance?
```

What good output looks like:
- Rams evaluates from the user's perspective — which steps fail the honesty/clarity test
- Torvalds asks what's the boring, maintainable solution
- Watts questions whether the framing ("simplify vs add guidance") is a false dichotomy
- Concrete recommendation with user evidence

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
