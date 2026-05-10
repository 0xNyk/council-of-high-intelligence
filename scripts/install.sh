#!/usr/bin/env bash
# Council of High Intelligence — multi-CLI installer
# Supports Claude Code, Codex, and Gemini CLI targets.
#
# CANONICAL GEMINI INSTALL (no script needed):
#   gemini extensions install https://github.com/Alpsource/council-of-high-intelligence-gemini
# That command clones the repo into ~/.gemini/extensions/council-of-high-intelligence/
# automatically. Use this script only for local/offline installs or Claude/Codex targets.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "${SCRIPT_DIR}")"

CLAUDE_DIR="${HOME}/.claude"
CODEX_DIR="${HOME}/.codex"
GEMINI_DIR="${HOME}/.gemini"

DRY_RUN=false
COPY_CONFIGS=false
INSTALL_CLAUDE=true
INSTALL_CODEX=false
INSTALL_GEMINI=false

usage() {
  cat <<'EOF'
Usage: ./scripts/install.sh [OPTIONS]

Install Council of High Intelligence into Claude Code, Codex, and/or Gemini CLI.

Options:
  --claude-dir PATH   Target Claude config directory (default: ~/.claude)
  --codex-dir PATH    Target Codex config directory (default: ~/.codex)
  --gemini-dir PATH   Target Gemini extensions directory (default: ~/.gemini)
  --codex             Also install to Codex
  --codex-only        Install only to Codex (skip Claude)
  --gemini            Also install as a Gemini extension
  --gemini-only       Install only as a Gemini extension (skip Claude and Codex)
  --all               Install to all three: Claude, Codex, and Gemini
  --copy-configs      Also copy configs/ into skill config folders (Claude/Codex)
  --dry-run           Print actions without writing files
  --help              Show this help message

Examples:
  ./scripts/install.sh                          # Claude only (default)
  ./scripts/install.sh --gemini                 # Claude + Gemini
  ./scripts/install.sh --gemini-only            # Gemini only
  ./scripts/install.sh --all                    # All three targets
  ./scripts/install.sh --gemini --dry-run       # Preview Gemini install
EOF
}

run_cmd() {
  if [[ "${DRY_RUN}" == true ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude-dir)   CLAUDE_DIR="$2"; shift 2 ;;
    --codex-dir)    CODEX_DIR="$2"; shift 2 ;;
    --gemini-dir)   GEMINI_DIR="$2"; shift 2 ;;
    --codex)        INSTALL_CODEX=true; shift ;;
    --codex-only)   INSTALL_CLAUDE=false; INSTALL_CODEX=true; shift ;;
    --gemini)       INSTALL_GEMINI=true; shift ;;
    --gemini-only)  INSTALL_CLAUDE=false; INSTALL_CODEX=false; INSTALL_GEMINI=true; shift ;;
    --all)          INSTALL_CLAUDE=true; INSTALL_CODEX=true; INSTALL_GEMINI=true; shift ;;
    --copy-configs) COPY_CONFIGS=true; shift ;;
    --dry-run)      DRY_RUN=true; shift ;;
    --help|-h)      usage; exit 0 ;;
    *)              echo "Error: unknown argument '$1'" >&2; usage; exit 1 ;;
  esac
done

if [[ "${INSTALL_CLAUDE}" == false ]] && [[ "${INSTALL_CODEX}" == false ]] && [[ "${INSTALL_GEMINI}" == false ]]; then
  echo "Error: no install target selected" >&2
  usage
  exit 1
fi

# --- validation ---
if [[ ! -d "${REPO_DIR}/agents" ]]; then
  echo "Error: agents/ directory not found at ${REPO_DIR}/agents" >&2; exit 1
fi
if [[ "${INSTALL_CLAUDE}" == true ]] && [[ ! -f "${REPO_DIR}/skills/council/SKILL.md" ]]; then
  echo "Error: skills/council/SKILL.md not found" >&2; exit 1
fi
if [[ ! -f "${REPO_DIR}/gemini-extension.json" ]]; then
  echo "Error: gemini-extension.json not found at ${REPO_DIR}" >&2; exit 1
fi

shopt -s nullglob
agent_files=("${REPO_DIR}"/agents/council-*.md)
shopt -u nullglob
if [[ ${#agent_files[@]} -eq 0 ]]; then
  echo "Error: no council-*.md files found in ${REPO_DIR}/agents" >&2; exit 1
fi

echo "Installing Council of High Intelligence..."
echo

# --- Claude install ---
install_claude() {
  local dest_agents="${CLAUDE_DIR}/agents"
  local dest_skill_dir="${CLAUDE_DIR}/skills/council"
  local dest_skill="${dest_skill_dir}/SKILL.md"

  echo "==> Claude Code: ${CLAUDE_DIR}"
  run_cmd mkdir -p "${dest_agents}" "${dest_skill_dir}"

  local count=0
  for f in "${agent_files[@]}"; do
    run_cmd install -m 0644 "${f}" "${dest_agents}/"
    ((count+=1))
  done

  run_cmd install -m 0644 "${REPO_DIR}/skills/council/SKILL.md" "${dest_skill}"

  if [[ "${COPY_CONFIGS}" == true ]] && [[ -d "${REPO_DIR}/configs" ]]; then
    local dest_configs="${dest_skill_dir}/configs"
    run_cmd mkdir -p "${dest_configs}"
    for f in "${REPO_DIR}"/configs/*; do
      [[ -f "${f}" ]] && run_cmd install -m 0644 "${f}" "${dest_configs}/"
    done
  fi

  echo "    Installed ${count} agents → ${dest_agents}"
  echo "    Installed skill → ${dest_skill}"
}

# --- Codex install ---
install_codex() {
  local dest_skill_dir="${CODEX_DIR}/skills/council"
  local dest_agents="${dest_skill_dir}/agents"

  echo "==> Codex: ${CODEX_DIR}"
  run_cmd mkdir -p "${dest_skill_dir}" "${dest_agents}"

  # Codex uses the same Gemini skill (no separate SKILL.codex.md in this port)
  run_cmd install -m 0644 "${REPO_DIR}/skills/council/SKILL.md" "${dest_skill_dir}/SKILL.md"

  local count=0
  for f in "${agent_files[@]}"; do
    run_cmd install -m 0644 "${f}" "${dest_agents}/"
    ((count+=1))
  done

  echo "    Installed ${count} agents → ${dest_agents}"
  echo "    Installed skill → ${dest_skill_dir}/SKILL.md"
}

# --- Gemini install ---
install_gemini() {
  local ext_name="council-of-high-intelligence"
  local dest="${GEMINI_DIR}/extensions/${ext_name}"

  echo "==> Gemini CLI: ${dest}"
  run_cmd mkdir -p "${dest}/commands/council" "${dest}/skills/council/references" \
                   "${dest}/agents" "${dest}/configs" "${dest}/hooks"

  run_cmd install -m 0644 "${REPO_DIR}/gemini-extension.json" "${dest}/"
  run_cmd install -m 0644 "${REPO_DIR}/GEMINI.md"             "${dest}/"
  run_cmd install -m 0644 "${REPO_DIR}/LICENSE"               "${dest}/"

  # commands
  run_cmd install -m 0644 "${REPO_DIR}/commands/council.toml" "${dest}/commands/"
  for f in "${REPO_DIR}"/commands/council/*.toml; do
    run_cmd install -m 0644 "${f}" "${dest}/commands/council/"
  done

  # skill + references
  run_cmd install -m 0644 "${REPO_DIR}/skills/council/SKILL.md" "${dest}/skills/council/"
  for f in "${REPO_DIR}"/skills/council/references/*.md; do
    run_cmd install -m 0644 "${f}" "${dest}/skills/council/references/"
  done

  # agents
  local count=0
  for f in "${agent_files[@]}"; do
    run_cmd install -m 0644 "${f}" "${dest}/agents/"
    ((count+=1))
  done

  # configs
  for f in "${REPO_DIR}"/configs/*.yaml; do
    run_cmd install -m 0644 "${f}" "${dest}/configs/"
  done

  echo "    Installed ${count} agents → ${dest}/agents"
  echo "    Installed skill + 3 reference files → ${dest}/skills/council/"
  echo "    Installed gemini-extension.json → ${dest}/"

  if command -v gemini &>/dev/null; then
    echo
    echo "    Gemini CLI detected. Verify the extension with:"
    echo "      gemini extensions list"
  else
    echo
    echo "    Note: 'gemini' CLI not found on PATH. Install Gemini CLI, then verify:"
    echo "      gemini extensions list"
  fi
}

[[ "${INSTALL_CLAUDE}" == true ]] && install_claude
[[ "${INSTALL_CODEX}"  == true ]] && install_codex
[[ "${INSTALL_GEMINI}" == true ]] && install_gemini

echo
echo "Done."
if [[ "${INSTALL_CLAUDE}" == true ]]; then
  echo "  Restart Claude Code and use /council to convene the council."
fi
if [[ "${INSTALL_CODEX}" == true ]]; then
  echo "  Restart Codex and use /council to convene the council."
fi
if [[ "${INSTALL_GEMINI}" == true ]]; then
  echo "  Restart Gemini CLI and use /council to convene the council."
fi
