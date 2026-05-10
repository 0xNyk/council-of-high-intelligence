#!/usr/bin/env bash
# Smoke test for the council-of-high-intelligence-gemini extension.
# Exits non-zero if any check fails.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "${SCRIPT_DIR}")"
PASS=0
FAIL=0

# Detect Python — prefer python3, fall back to python
PYTHON=""
for _py in python3 python python3.exe python.exe; do
  if command -v "${_py}" &>/dev/null && "${_py}" -c "import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)" 2>/dev/null; then
    PYTHON="${_py}"; break
  fi
done

pass() { echo "[PASS] $1"; ((PASS+=1)); }
fail() { echo "[FAIL] $1"; ((FAIL+=1)); }

# --- 1. JSON validity ---
manifest="${REPO_DIR}/gemini-extension.json"
if [[ -f "${manifest}" ]]; then
  if [[ -n "${PYTHON}" ]]; then
    if "${PYTHON}" -c "import sys, json; json.load(sys.stdin)" < "${manifest}" 2>/dev/null; then
      pass "gemini-extension.json is valid JSON"
    else
      fail "gemini-extension.json is invalid JSON"
    fi
  else
    echo "[SKIP] Python not found — skipping JSON check"
  fi
else
  fail "gemini-extension.json not found"
fi

# --- 2. TOML validity + prompt field (grep-based, no parser required) ---
check_toml() {
  local f="$1"
  local name="${f#"${REPO_DIR}/"}"
  if [[ ! -f "${f}" ]]; then
    fail "TOML not found: ${name}"; return
  fi
  # Check file has at least one key=value line (minimal TOML sanity)
  if ! grep -qE '^\s*\w+\s*=' "${f}"; then
    fail "TOML appears empty or malformed: ${name}"; return
  fi
  # Check prompt key exists
  if grep -qE '^\s*prompt\s*=' "${f}"; then
    pass "TOML has prompt field: ${name}"
  else
    fail "TOML missing 'prompt' field: ${name}"
  fi
}

shopt -s nullglob
for toml_file in "${REPO_DIR}"/commands/*.toml "${REPO_DIR}"/commands/council/*.toml; do
  check_toml "${toml_file}"
done
shopt -u nullglob

# --- 3. SKILL.md frontmatter ---
skill_file="${REPO_DIR}/skills/council/SKILL.md"
if [[ -f "${skill_file}" ]]; then
  # Check file starts with --- and has name: and description: within first frontmatter block
  if head -20 "${skill_file}" | grep -q "^name:" && head -20 "${skill_file}" | grep -q "^description:"; then
    pass "skills/council/SKILL.md has valid frontmatter (name + description)"
  else
    fail "skills/council/SKILL.md missing or invalid frontmatter"
  fi
else
  fail "skills/council/SKILL.md not found"
fi

# --- 4. Agent frontmatter ---
agent_pass=0
agent_fail=0
shopt -s nullglob
for agent_file in "${REPO_DIR}"/agents/council-*.md; do
  fname="$(basename "${agent_file}")"
  has_name=false
  has_desc=false
  head -10 "${agent_file}" | grep -q "^name:" && has_name=true
  head -10 "${agent_file}" | grep -q "^description:" && has_desc=true
  if [[ "${has_name}" == true ]] && [[ "${has_desc}" == true ]]; then
    ((agent_pass+=1))
  else
    fail "Agent missing frontmatter (name or description): ${fname}"
    ((agent_fail+=1))
  fi
done
shopt -u nullglob

if [[ ${agent_fail} -eq 0 ]] && [[ ${agent_pass} -gt 0 ]]; then
  pass "All ${agent_pass} agent files have valid frontmatter (name + description)"
elif [[ ${agent_pass} -eq 0 ]]; then
  fail "No agent files found in agents/"
fi

# --- 5. Required files ---
required_files=(
  "gemini-extension.json"
  "GEMINI.md"
  "README.md"
  "LICENSE"
  "NOTICE"
  "CHANGELOG.md"
)
for rf in "${required_files[@]}"; do
  if [[ -f "${REPO_DIR}/${rf}" ]]; then
    pass "Required file present: ${rf}"
  else
    fail "Required file missing: ${rf}"
  fi
done

# --- 6. Reference files ---
ref_files=(
  "skills/council/references/triads.md"
  "skills/council/references/polarity-pairs.md"
  "skills/council/references/verdict-templates.md"
)
for rf in "${ref_files[@]}"; do
  if [[ -f "${REPO_DIR}/${rf}" ]]; then
    pass "Reference file present: ${rf}"
  else
    fail "Reference file missing: ${rf}"
  fi
done

# --- summary ---
echo
echo "Results: ${PASS} passed, ${FAIL} failed"
if [[ ${FAIL} -gt 0 ]]; then
  exit 1
fi
