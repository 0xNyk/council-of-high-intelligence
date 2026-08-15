#!/usr/bin/env python3
"""Validate that SKILL.md prose and agents/*.md frontmatter describe the same council.

The coordinator reads the prose; panel selection and tie-breaking read the
frontmatter. When the two disagree the council still runs, silently seating the
wrong people -- which is why this is a hard gate rather than a lint warning.

Three real drifts motivated it: Aristotle carried a `profiles` tag for a panel
that SKILL.md documents without him, and the Sutskever/Machiavelli and
Socrates/Watts polarity pairs existed in the frontmatter and the duo table but
were missing from the Polarity Pairs list the coordinator reads.

Usage: validate-roster.py [repo_root]
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit(
        "Error: PyYAML is required. Install it with: pip3 install --user pyyaml"
    )

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

REQUIRED_KEYS = {
    "figure",
    "domain",
    "polarity",
    "polarity_pairs",
    "triads",
    "duo_keywords",
    "profiles",
    "reasoning_method",
}

failures = []
checks = 0


def fail(message):
    """Record one failed check."""
    global checks
    checks += 1
    failures.append(message)


def check(condition, message):
    """Record one check, failing it when the condition does not hold."""
    global checks
    if condition:
        checks += 1
    else:
        fail(message)


def norm(name):
    """Fold a prose name and a slug onto one key: 'Sun Tzu' and 'sun-tzu' -> 'suntzu'."""
    return re.sub(r"[^a-z]", "", name.lower())


def load_agents(agents_dir):
    agents = {}
    for path in sorted(agents_dir.glob("council-*.md")):
        match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
        if not match:
            fail(f"{path.name}: no YAML frontmatter")
            continue
        council = (yaml.safe_load(match.group(1)) or {}).get("council")
        if not council:
            fail(f"{path.name}: no `council:` block")
            continue
        agents[path.stem.removeprefix("council-")] = council
    return agents


def main():
    # Default to the repo root relative to this script, so the check behaves the
    # same from any working directory (matching council-simulation-checklist.sh).
    default_root = Path(__file__).resolve().parent.parent
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_root
    agents = load_agents(root / "agents")
    skill = (root / "SKILL.md").read_text(encoding="utf-8")

    if not agents:
        sys.exit("No agent definitions found under agents/council-*.md")

    by_norm = {norm(slug): slug for slug in agents}

    def resolve(prose_name):
        return by_norm.get(norm(prose_name))

    # --- frontmatter completeness ---
    for slug, council in agents.items():
        missing = REQUIRED_KEYS - set(council)
        check(not missing, f"{slug}: missing council keys {sorted(missing)}")

    # --- method diversity (DMAD): every seat reasons differently ---
    methods = {}
    for slug, council in agents.items():
        methods.setdefault(council.get("reasoning_method"), []).append(slug)
    for method, owners in sorted(methods.items()):
        check(len(owners) == 1, f"reasoning_method '{method}' shared by {owners}")

    # --- polarity pairs: resolvable, mutual, and mirrored in the prose ---
    frontmatter_pairs = set()
    for slug, council in agents.items():
        for peer in council.get("polarity_pairs", []):
            if peer not in agents:
                fail(f"{slug}: polarity pair '{peer}' is not a member")
                continue
            check(
                slug in agents[peer].get("polarity_pairs", []),
                f"polarity pair {slug} -> {peer} is not reciprocated by {peer}",
            )
            frontmatter_pairs.add(frozenset((slug, peer)))

    prose_block = skill.split("## Polarity Pairs", 1)
    if len(prose_block) == 2:
        prose_pairs = set()
        for left, right in re.findall(
            r"^- \*\*(.+?) vs (.+?)\*\*", prose_block[1].split("\n## ", 1)[0], re.MULTILINE
        ):
            a, b = resolve(left), resolve(right)
            if a and b:
                prose_pairs.add(frozenset((a, b)))
            else:
                fail(f"Polarity Pairs: unknown member in '{left} vs {right}'")
        for pair in sorted(frontmatter_pairs - prose_pairs, key=sorted):
            fail(f"pair {sorted(pair)} in frontmatter but not in SKILL.md")
        for pair in sorted(prose_pairs - frontmatter_pairs, key=sorted):
            fail(f"pair {sorted(pair)} in SKILL.md but not in frontmatter")
    else:
        fail("SKILL.md has no '## Polarity Pairs' section")

    # --- profiles: declared size and enumerated members match the tags ---
    # Slice each `### `name`` section at the next heading, so a section without
    # a **Members** line cannot borrow the next section's roster.
    sections = re.split(r"^(?=#{2,3} )", skill, flags=re.MULTILINE)
    for section in sections:
        heading = re.match(r"^### `([a-z-]+)`", section)
        if not heading:
            continue
        name = heading.group(1)
        tagged = sorted(s for s, c in agents.items() if name in c.get("profiles", []))

        size = re.search(r"^(?:All )?(\d+)[- ]member", section, re.MULTILINE)
        if size:
            check(
                len(tagged) == int(size.group(1)),
                f"profile '{name}': SKILL.md says {size.group(1)} members, "
                f"{len(tagged)} tagged ({tagged})",
            )

        members = re.search(r"^\*\*Members\*\*: (.+)$", section, re.MULTILINE)
        if members:
            listed = sorted(
                filter(None, (resolve(m) for m in members.group(1).split(", ")))
            )
            check(
                listed == tagged,
                f"profile '{name}': listed {listed} but tagged {tagged}",
            )

    # --- every tagged profile is one SKILL.md actually documents ---
    documented = set(re.findall(r"^### `([a-z-]+)`", skill, re.MULTILINE))
    for slug, council in agents.items():
        for profile in council.get("profiles", []):
            check(
                profile in documented,
                f"{slug}: profile '{profile}' is not documented in SKILL.md",
            )

    # --- triads referenced by members exist in the triad table ---
    triads = set(re.findall(r"^\| `([a-z-]+)` \|", skill, re.MULTILINE))
    for slug, council in agents.items():
        for triad in council.get("triads", []):
            check(triad in triads, f"{slug}: triad '{triad}' is not in the triad table")

    # --- the roster table lists exactly the agents on disk ---
    rostered = set(re.findall(r"\| `council-([a-z-]+)` \|", skill))
    check(
        rostered == set(agents),
        f"roster/agent mismatch: only in SKILL.md {sorted(rostered - set(agents))}, "
        f"only on disk {sorted(set(agents) - rostered)}",
    )

    print(f"== Roster Validation ==\nmembers: {len(agents)}  checks: {checks}")
    if failures:
        for line in failures:
            print(f"[FAIL] {line}")
        sys.exit(f"\n{len(failures)} problem(s) found")
    print("[PASS] SKILL.md and agent frontmatter agree")


if __name__ == "__main__":
    main()
