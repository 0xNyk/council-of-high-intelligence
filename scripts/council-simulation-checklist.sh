#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_DIR}"

echo "== Council Simulation Checklist =="

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }
warn() { echo "[WARN] $1"; }

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

grep -q "exploration-orthogonal" SKILL.md || fail "exploration-orthogonal profile missing in SKILL.md"
pass "exploration-orthogonal profile documented in SKILL.md"

grep -q -- "--models" SKILL.md || fail "--models flag missing in SKILL.md"
pass "--models flag documented in SKILL.md"

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
