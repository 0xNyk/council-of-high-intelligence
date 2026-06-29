#!/usr/bin/env python3
"""Explain a council panel and provider route without running deliberation."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / "protocol.json").read_text(encoding="utf-8"))

TRIAD_KEYWORDS = {
    "architecture": ["architecture", "structure", "system", "backend", "monorepo"],
    "strategy": ["strategy", "competition", "market", "moat"],
    "ethics": ["ethics", "moral", "duty", "right"],
    "debugging": ["debug", "bug", "failure", "root cause"],
    "innovation": ["innovation", "new", "invention"],
    "conflict": ["conflict", "war", "fight", "dispute", "войн", "конфликт"],
    "risk": ["risk", "threat", "downside", "опасн", "риск"],
    "shipping": ["ship", "release", "launch", "релиз", "запуск"],
    "product": ["product", "pricing", "onboarding", "продукт", "цено"],
    "ai": ["ai", "ml", "llm", "model", "нейро", "модель"],
    "decision": ["decision", "choose", "bias", "решен", "выбор"],
    "systems": ["systems", "feedback", "loop", "систем"],
    "uncertainty": ["uncertain", "tail", "fragile", "неопредел"],
    "design": ["design", "ux", "ui", "user", "дизайн"],
    "economics": ["economics", "investment", "money", "рынок", "деньги"],
    "bias": ["bias", "judgment", "cognitive", "ошибк"],
}

DOMAIN_WEIGHT = {
    "architecture": "ada",
    "strategy": "sun-tzu",
    "ethics": "aurelius",
    "debugging": "feynman",
    "innovation": "ada",
    "conflict": "machiavelli",
    "complexity": "ada",
    "risk": "sun-tzu",
    "shipping": "torvalds",
    "product": "rams",
    "founder": "musashi",
    "ai": "karpathy",
    "ai-product": "karpathy",
    "ai-safety": "sutskever",
    "decision": "kahneman",
    "systems": "meadows",
    "uncertainty": "taleb",
    "design": "rams",
    "economics": "munger",
    "bias": "kahneman",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", default="", help="Problem statement used for auto-triad explanation")
    parser.add_argument("--mode", default="full", choices=["full", "quick", "duo"], help="Council mode")
    parser.add_argument("--triad", choices=sorted(PROTOCOL["triads"].keys()), help="Use a predefined triad")
    parser.add_argument("--profile", choices=sorted(PROTOCOL["profiles"].keys()), help="Use a predefined profile")
    parser.add_argument("--members", help="Comma-separated explicit members")
    parser.add_argument("--providers-json", help="Use precomputed detect-providers JSON")
    return parser.parse_args()


def detect_providers(args: argparse.Namespace) -> list[dict]:
    if args.providers_json:
        data = json.loads(Path(args.providers_json).read_text(encoding="utf-8"))
    else:
        detect_script = ROOT / "scripts" / "detect-providers.sh"
        try:
            output = subprocess.check_output(["bash", str(detect_script)], text=True, timeout=10)
            data = json.loads(output)
        except Exception:
            data = {
                "providers": [
                    {
                        "name": "anthropic",
                        "available": True,
                        "exec_method": "subagent",
                        "binary": "native",
                        "models": ["opus", "sonnet"],
                    }
                ]
            }
    available = [provider for provider in data.get("providers", []) if provider.get("available")]
    return available or [{"name": "anthropic", "exec_method": "subagent", "models": ["opus", "sonnet"]}]


def auto_triad(problem: str) -> str:
    lowered = problem.lower()
    scores: list[tuple[int, str]] = []
    for triad, keywords in TRIAD_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        scores.append((score, triad))
    scores.sort(reverse=True)
    return scores[0][1] if scores and scores[0][0] > 0 else "decision"


def selected_panel(args: argparse.Namespace) -> tuple[str, list[str], str]:
    if args.members:
        members = [member.strip() for member in args.members.split(",") if member.strip()]
        return "members", members, "explicit --members override"
    if args.profile:
        return args.profile, PROTOCOL["profiles"][args.profile], "explicit --profile override"
    triad = args.triad or auto_triad(args.problem)
    reason = "explicit --triad override" if args.triad else "auto-selected from problem keywords"
    return triad, PROTOCOL["triads"][triad], reason


def rejected_alternatives(selected: str, problem: str) -> list[str]:
    candidates = []
    lowered = problem.lower()
    for triad, keywords in TRIAD_KEYWORDS.items():
        if triad == selected:
            continue
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > 0:
            candidates.append((score, triad))
    if not candidates:
        candidates = [(0, name) for name in ("strategy", "risk", "decision", "systems") if name != selected]
    candidates.sort(reverse=True)
    return [name for _, name in candidates[:4]]


def route_members(members: list[str], providers: list[dict]) -> list[tuple[str, str, str, str]]:
    rows = []
    for index, member in enumerate(members):
        provider = providers[index % len(providers)]
        models = provider.get("models") or ["default"]
        model = models[0] if isinstance(models, list) else "default"
        rows.append((member, provider.get("name", "unknown"), model, provider.get("exec_method", "unknown")))
    return rows


def chairman_plan(providers: list[dict], routed_providers: set[str]) -> tuple[str, str, str]:
    for provider in providers:
        if provider.get("name") not in routed_providers:
            models = provider.get("models") or ["default"]
            return provider.get("name", "unknown"), models[0], "provider not represented on panel"
    provider = providers[0]
    models = provider.get("models") or ["default"]
    return provider.get("name", "unknown"), models[0], "single-provider or all providers already represented"


def main() -> int:
    args = parse_args()
    selected, members, reason = selected_panel(args)
    providers = detect_providers(args)
    route = route_members(members, providers)
    domain_member = DOMAIN_WEIGHT.get(selected)
    if domain_member not in members:
        domain_member = None
    rejected = rejected_alternatives(selected, args.problem)
    chairman_provider, chairman_model, chairman_reason = chairman_plan(
        providers, {provider for _, provider, _, _ in route}
    )

    print("## Explain Route")
    print()
    print(f"### Selected Panel\n{selected} ({args.mode}) - {', '.join(members)}")
    print(f"\nReason: {reason}.")
    print("\n### Rejected Alternatives")
    for alternative in rejected:
        print(f"- {alternative}: less direct fit for this invocation")
    print("\n### Domain-Weight Seat")
    if domain_member:
        print(f"{domain_member} -> 1.5x (best domain match for `{selected}`)")
    else:
        print("none -> ambiguous or explicit member selection")
    print("\n### Provider Routing")
    for member, provider, model, exec_method in route:
        print(f"- {member} -> {provider} -> {model} -> {exec_method}")
    print("\n### Chairman Plan")
    print(f"{chairman_provider} -> {chairman_model} ({chairman_reason})")
    print("\n### User Override Hints")
    print(f"- /council --triad {selected} <problem>")
    print("- /council --members socrates,feynman,ada <problem>")
    print("- /council --profile geopolitics <problem>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
