#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_DIR}"

echo "== Council Simulation Checklist =="

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }
warn() { echo "[WARN] $1"; }

# --- File existence checks ---

[[ -f "SKILL.md" ]] || fail "SKILL.md is missing"
pass "SKILL.md exists"

if compgen -G "agents/council-*.md" >/dev/null; then
  agent_count=$(python3 -c "import glob; print(len(glob.glob('agents/council-*.md')))" 2>/dev/null || echo "unknown")
  pass "Agent definitions found (count=${agent_count})"
else
  fail "No agent definitions found under agents/council-*.md"
fi

[[ -f "configs/provider-model-slots.example.yaml" ]] || fail "configs/provider-model-slots.example.yaml is missing"
pass "Provider/model slot template exists"

[[ -f "CLAUDE.md" ]] || warn "CLAUDE.md is missing (recommended for project conventions)"

# --- SKILL.md content checks ---

grep -q "exploration-orthogonal" SKILL.md || fail "exploration-orthogonal profile missing in SKILL.md"
pass "exploration-orthogonal profile documented in SKILL.md"

grep -q "execution-lean" SKILL.md || fail "execution-lean profile missing in SKILL.md"
pass "execution-lean profile documented in SKILL.md"

grep -q -- "--models" SKILL.md || fail "--models flag missing in SKILL.md"
pass "--models flag documented in SKILL.md"

grep -q -- "--quick" SKILL.md || fail "--quick flag missing in SKILL.md"
pass "--quick mode documented in SKILL.md"

grep -q -- "--duo" SKILL.md || fail "--duo flag missing in SKILL.md"
pass "--duo mode documented in SKILL.md"

grep -q "CHECKPOINT" SKILL.md || fail "Execution checkpoints missing in SKILL.md"
pass "Execution checkpoints present in SKILL.md"

grep -q "VERIFY" SKILL.md || fail "Verification steps missing in SKILL.md"
pass "Verification steps present in SKILL.md"

# --- Agent structure checks ---

required_sections=("Identity" "Grounding Protocol" "Analytical Method" "What You See" "What You Tend to Miss" "When Deliberating" "Output Format (Council Round 2)" "Output Format (Standalone)")

agent_structure_ok=true
for agent_file in agents/council-*.md; do
  agent_name=$(basename "${agent_file}" .md)
  for section in "${required_sections[@]}"; do
    if ! grep -q "## ${section}" "${agent_file}" 2>/dev/null; then
      # Some sections use slightly different headers, try partial match
      section_word=$(echo "${section}" | awk '{print $1}')
      if ! grep -qi "${section_word}" "${agent_file}" 2>/dev/null; then
        warn "${agent_name}: missing section '${section}'"
        agent_structure_ok=false
      fi
    fi
  done
done

if [[ "${agent_structure_ok}" == true ]]; then
  pass "All agents have consistent section structure"
else
  warn "Some agents have inconsistent section structure (see warnings above)"
fi

# --- Grounding protocol placement check ---

grounding_early=true
for agent_file in agents/council-*.md; do
  agent_name=$(basename "${agent_file}" .md)
  grounding_line=$(grep -n "## Grounding Protocol" "${agent_file}" 2>/dev/null | head -1 | cut -d: -f1 || echo "999")
  method_line=$(grep -n "## Analytical Method" "${agent_file}" 2>/dev/null | head -1 | cut -d: -f1 || echo "0")
  if [[ "${grounding_line}" -gt "${method_line}" ]] && [[ "${method_line}" -gt 0 ]]; then
    warn "${agent_name}: Grounding Protocol appears after Analytical Method (should be before)"
    grounding_early=false
  fi
done

if [[ "${grounding_early}" == true ]]; then
  pass "Grounding protocols placed before Analytical Method in all agents"
fi

# --- Triad member validation ---

triad_members_ok=true
for member_name in aristotle socrates feynman ada sun-tzu machiavelli aurelius lao-tzu torvalds musashi watts; do
  if [[ ! -f "agents/council-${member_name}.md" ]]; then
    fail "Missing agent file for triad member: council-${member_name}.md"
    triad_members_ok=false
  fi
done

if [[ "${triad_members_ok}" == true ]]; then
  pass "All triad member agent files present"
fi

# --- Verdict template dedup check ---

if grep -q "^{" demos/verdict-template.md 2>/dev/null; then
  warn "demos/verdict-template.md still contains template placeholders (should point to SKILL.md)"
fi
pass "Verdict template dedup check done"

# --- Install script checks ---

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck install.sh
  pass "shellcheck passed for install.sh"
else
  warn "shellcheck not installed; skipped"
fi

./install.sh --dry-run >/tmp/council-install-dry-run.log
pass "install.sh --dry-run completed"

grep -q "Installed .* council agents" /tmp/council-install-dry-run.log || fail "install dry-run output missing agent install summary"
pass "install summary output present"

./install.sh --dry-run --copy-configs >/tmp/council-install-dry-run-configs.log
pass "install.sh --dry-run --copy-configs completed"

grep -q "Installed .* config files" /tmp/council-install-dry-run-configs.log || fail "copy-configs dry-run output missing config install summary"
pass "config summary output present"

echo
echo "Checklist complete."
