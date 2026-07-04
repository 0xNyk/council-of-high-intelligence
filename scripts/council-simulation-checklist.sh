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
[[ -f "SKILL.codex.md" ]] || fail "SKILL.codex.md is missing"
pass "SKILL.codex.md exists"
[[ -f "SKILL.gemini.md" ]] || fail "SKILL.gemini.md is missing"
pass "SKILL.gemini.md exists"

if compgen -G "agents/council-*.md" >/dev/null; then
  agent_count=$(compgen -G "agents/council-*.md" | wc -l | tr -d ' ')
  pass "Agent definitions found (count=${agent_count})"
else
  fail "No agent definitions found under agents/council-*.md"
fi

[[ -f "configs/provider-model-slots.example.yaml" ]] || fail "configs/provider-model-slots.example.yaml is missing"
pass "Provider/model slot template exists"

# --- Plugin manifest checks ---

[[ -f ".claude-plugin/plugin.json" ]] || fail ".claude-plugin/plugin.json is missing"
[[ -f ".claude-plugin/marketplace.json" ]] || fail ".claude-plugin/marketplace.json is missing"
[[ -e "skills/council/SKILL.md" ]] || fail "skills/council/SKILL.md (plugin skill path) is missing or a broken symlink"
pass "Plugin manifests and skill path present"

changelog_version=$(sed -nE 's/^## \[([0-9]+\.[0-9]+\.[0-9]+)\].*/\1/p' CHANGELOG.md | head -1)
plugin_version=$(sed -nE 's/.*"version": "([0-9]+\.[0-9]+\.[0-9]+)".*/\1/p' .claude-plugin/plugin.json | head -1)
marketplace_version=$(sed -nE 's/.*"version": "([0-9]+\.[0-9]+\.[0-9]+)".*/\1/p' .claude-plugin/marketplace.json | head -1)
if [[ "$plugin_version" != "$changelog_version" ]] || [[ "$marketplace_version" != "$changelog_version" ]]; then
  fail "Version drift: CHANGELOG=${changelog_version} plugin.json=${plugin_version} marketplace.json=${marketplace_version} — bump the manifests when releasing"
fi
pass "Plugin manifest versions match CHANGELOG (${changelog_version})"

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

# Round 2 anonymization (issue #17) — protect against silent regression
grep -q "ANONYMIZED" SKILL.md || fail "Round 2 anonymization missing in SKILL.md (issue #17)"
grep -q "Member A" SKILL.md || fail "Member-label vocabulary missing in SKILL.md (issue #17)"
pass "Round 2 anonymization wired in SKILL.md"

grep -q "anonymiz" SKILL.codex.md || fail "Round 2 anonymization missing in SKILL.codex.md (issue #17)"
pass "Round 2 anonymization wired in SKILL.codex.md"

# Anti-conformity directive (issue #19) — must be in every Round 2 prompt
ac_count_skill=$(grep -c "Anti-conformity directive" SKILL.md || true)
if [[ "$ac_count_skill" -lt 3 ]]; then
  fail "Anti-conformity directive missing from one or more Round 2 prompts in SKILL.md (issue #19; expected ≥3 occurrences, found ${ac_count_skill})"
fi
pass "Anti-conformity directive present in all 3 Round 2 prompts in SKILL.md"

grep -q "Anti-conformity directive" SKILL.codex.md || fail "Anti-conformity directive missing in SKILL.codex.md (issue #19)"
pass "Anti-conformity directive present in SKILL.codex.md"

# Chairman role (issue #18) — must be wired into STEP 1.7, STEP 7, flags, and Codex
grep -q "STEP 1.7" SKILL.md || fail "Chairman selection step missing in SKILL.md (issue #18)"
grep -q -- "--chairman" SKILL.md || fail "--chairman flag missing in SKILL.md (issue #18)"
grep -q "CHAIRMAN" SKILL.md || fail "Chairman synthesis step missing in SKILL.md (issue #18)"
pass "Chairman role wired in SKILL.md (STEP 1.7 + --chairman flag + synthesis step)"

grep -q -i "chairman" SKILL.codex.md || fail "Chairman role missing in SKILL.codex.md (issue #18)"
pass "Chairman role wired in SKILL.codex.md"

grep -q "chairman_defaults" configs/auto-route-defaults.yaml || fail "chairman_defaults block missing in auto-route-defaults.yaml (issue #18)"
pass "Chairman defaults configured in auto-route-defaults.yaml"

# Verdict actionability sections (issue #21)
grep -q "Acceptable Compromises" SKILL.md || fail "Acceptable Compromises section missing in SKILL.md (issue #21)"
grep -q "Kill Criteria" SKILL.md || fail "Kill Criteria section missing in SKILL.md (issue #21)"
grep -q "Concrete Next Step" SKILL.md || fail "Concrete Next Step section missing in SKILL.md (issue #21)"
pass "Verdict actionability sections present in SKILL.md (Acceptable Compromises / Kill Criteria / Concrete Next Step)"

grep -q "Acceptable Compromises" SKILL.codex.md || fail "Acceptable Compromises missing in SKILL.codex.md (issue #21)"
grep -q "Kill Criteria" SKILL.codex.md || fail "Kill Criteria missing in SKILL.codex.md (issue #21)"
grep -q "Concrete Next Step" SKILL.codex.md || fail "Concrete Next Step missing in SKILL.codex.md (issue #21)"
pass "Verdict actionability sections present in SKILL.codex.md"

# OpenAI-compatible API archetype (issue #16) — must be wired in dispatch + routing
grep -q "openai_compatible_api" SKILL.md || fail "openai_compatible_api archetype missing in SKILL.md (issue #16)"
grep -q "base_url" SKILL.md || fail "base_url handling missing in SKILL.md (issue #16)"
grep -q "api_key_env" SKILL.md || fail "api_key_env handling missing in SKILL.md (issue #16)"
pass "openai_compatible_api archetype wired in SKILL.md (dispatch + base_url + api_key_env)"

grep -q "openai_compatible_api\|openai-compatible\|OpenAI-Compatible" SKILL.codex.md || fail "openai_compatible_api archetype missing in SKILL.codex.md (issue #16)"
pass "openai_compatible_api archetype wired in SKILL.codex.md"

# Session Metadata schema (issue #7 Phase 1)
grep -q "Session Metadata" SKILL.md || fail "Session Metadata block missing in SKILL.md (issue #7)"
grep -q "schema_version: 1" SKILL.md || fail "schema_version: 1 marker missing in SKILL.md Session Metadata (issue #7)"
pass "Session Metadata schema wired in SKILL.md"

grep -q "Session Metadata\|session metadata\|session_metadata" SKILL.codex.md || fail "Session Metadata missing in SKILL.codex.md (issue #7)"
pass "Session Metadata referenced in SKILL.codex.md"

# --- SKILL.gemini.md parity checks ---
# The Gemini variant is the least-exercised of the three coordinator files and
# is exactly where feature drift shipped once before. Every protocol feature
# checked for codex above is checked for gemini here.

grep -q "anonymiz" SKILL.gemini.md || fail "Round 2 anonymization missing in SKILL.gemini.md (issue #17)"
pass "Round 2 anonymization wired in SKILL.gemini.md"

grep -q "Anti-conformity directive" SKILL.gemini.md || fail "Anti-conformity directive missing in SKILL.gemini.md (issue #19)"
pass "Anti-conformity directive present in SKILL.gemini.md"

grep -q -i "chairman" SKILL.gemini.md || fail "Chairman role missing in SKILL.gemini.md (issue #18)"
pass "Chairman role wired in SKILL.gemini.md"

grep -q "Acceptable Compromises" SKILL.gemini.md || fail "Acceptable Compromises missing in SKILL.gemini.md (issue #21)"
grep -q "Kill Criteria" SKILL.gemini.md || fail "Kill Criteria missing in SKILL.gemini.md (issue #21)"
grep -q "Concrete Next Step" SKILL.gemini.md || fail "Concrete Next Step missing in SKILL.gemini.md (issue #21)"
pass "Verdict actionability sections present in SKILL.gemini.md"

grep -q "openai_compatible_api\|openai-compatible\|OpenAI-Compatible" SKILL.gemini.md || fail "openai_compatible_api archetype missing in SKILL.gemini.md (issue #16)"
pass "openai_compatible_api archetype wired in SKILL.gemini.md"

grep -q "Session Metadata\|session metadata\|session_metadata" SKILL.gemini.md || fail "Session Metadata missing in SKILL.gemini.md (issue #7)"
pass "Session Metadata referenced in SKILL.gemini.md"

# --- Structured stance / weighted tally parity (PR #36) ---
# All three coordinator files must carry the STANCE line, the Vote Tally
# verdict field, and the 1.5x domain-weight seat. This is the check that
# would have caught the Gemini regression.

for skill_file in SKILL.md SKILL.codex.md SKILL.gemini.md; do
  grep -q "STANCE:" "${skill_file}" || fail "Structured STANCE line missing in ${skill_file} (PR #36)"
  grep -q "Vote Tally" "${skill_file}" || fail "Vote Tally verdict field missing in ${skill_file} (PR #36)"
  grep -q "1\.5" "${skill_file}" || fail "1.5x domain-weight seat missing in ${skill_file} (PR #36)"
  grep -q "2/3" "${skill_file}" || fail "2/3 consensus threshold missing in ${skill_file} (PR #36)"
done
pass "Structured stance + weighted tally present in all three SKILL files"

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

for member_name in aristotle socrates feynman ada sun-tzu machiavelli aurelius lao-tzu torvalds musashi watts karpathy sutskever kahneman meadows munger taleb rams; do
  if [[ ! -f "agents/council-${member_name}.md" ]]; then
    fail "Missing agent file for triad member: council-${member_name}.md"
  fi
done
pass "All triad member agent files present"

# --- Verdict template dedup check ---

if grep -q "^{" demos/verdict-template.md 2>/dev/null; then
  warn "demos/verdict-template.md still contains template placeholders (should point to SKILL.md)"
fi
pass "Verdict template dedup check done"

# --- Auto-routing checks ---

[[ -f "scripts/detect-providers.sh" ]] || fail "scripts/detect-providers.sh is missing"
[[ -x "scripts/detect-providers.sh" ]] || fail "scripts/detect-providers.sh is not executable"
pass "detect-providers.sh exists and is executable"

if detect_output="$(bash scripts/detect-providers.sh 2>/dev/null)"; then
  if echo "$detect_output" | grep -q '"provider_count"'; then
    pass "detect-providers.sh produces valid JSON"
  else
    fail "detect-providers.sh output missing provider_count field"
  fi
else
  fail "detect-providers.sh exited with error"
fi

[[ -f "configs/auto-route-defaults.yaml" ]] || fail "configs/auto-route-defaults.yaml is missing"
pass "Auto-route defaults config exists"

grep -q -- "--no-auto-route" SKILL.md || fail "--no-auto-route flag missing in SKILL.md"
pass "--no-auto-route flag documented in SKILL.md"

grep -q -- "--dry-route" SKILL.md || fail "--dry-route flag missing in SKILL.md"
pass "--dry-route flag documented in SKILL.md"

affinity_count=0
for agent_file in agents/council-*.md; do
  if grep -q "provider_affinity" "$agent_file" 2>/dev/null; then
    ((affinity_count+=1))
  fi
done
if [[ "$affinity_count" -eq "$agent_count" ]]; then
  pass "All agents have provider_affinity in frontmatter"
else
  warn "Only ${affinity_count}/${agent_count} agents have provider_affinity"
fi

# --- Install script checks ---

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck install.sh
  pass "shellcheck passed for install.sh"
else
  warn "shellcheck not installed; skipped"
fi

TMP_LOG_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_LOG_DIR}"' EXIT

./install.sh --dry-run >"${TMP_LOG_DIR}/dry-run.log"
pass "install.sh --dry-run completed"

grep -q "Installed .* council agents" "${TMP_LOG_DIR}/dry-run.log" || fail "install dry-run output missing agent install summary"
pass "install summary output present"

./install.sh --dry-run --copy-configs >"${TMP_LOG_DIR}/dry-run-configs.log"
pass "install.sh --dry-run --copy-configs completed"

grep -q "Installed .* config files" "${TMP_LOG_DIR}/dry-run-configs.log" || fail "copy-configs dry-run output missing config install summary"
pass "config summary output present"

./install.sh --dry-run --codex >"${TMP_LOG_DIR}/dry-run-codex.log"
pass "install.sh --dry-run --codex completed"

grep -q "Installed Codex skill to" "${TMP_LOG_DIR}/dry-run-codex.log" || fail "codex dry-run output missing Codex skill summary"
pass "Codex install summary output present"

./install.sh --dry-run --gemini >"${TMP_LOG_DIR}/dry-run-gemini.log"
pass "install.sh --dry-run --gemini completed"

grep -q "gemini-extension.json" "${TMP_LOG_DIR}/dry-run-gemini.log" || fail "gemini dry-run output missing gemini-extension.json manifest step"
pass "Gemini install manifest step present"

echo
echo "Checklist complete."
