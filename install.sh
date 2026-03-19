#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage: ./install.sh [--claude-dir PATH] [--dry-run] [--help]

Install Council of High Intelligence agents and skill into a Claude Code config directory.

Options:
  --claude-dir PATH  Target Claude config directory (default: ~/.claude)
  --dry-run          Print actions without writing files
  --help             Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --claude-dir)
      if [[ $# -lt 2 ]]; then
        echo "Error: --claude-dir requires a path argument" >&2
        usage
        exit 1
      fi
      CLAUDE_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown argument '$1'" >&2
      usage
      exit 1
      ;;
  esac
done

run_cmd() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

if [[ ! -d "${SCRIPT_DIR}/agents" ]]; then
  echo "Error: agents directory not found at ${SCRIPT_DIR}/agents" >&2
  exit 1
fi

if [[ ! -f "${SCRIPT_DIR}/SKILL.md" ]]; then
  echo "Error: SKILL.md not found at ${SCRIPT_DIR}/SKILL.md" >&2
  exit 1
fi

shopt -s nullglob
agent_files=("${SCRIPT_DIR}"/agents/council-*.md)
shopt -u nullglob

if [[ ${#agent_files[@]} -eq 0 ]]; then
  echo "Error: no council agent files found under ${SCRIPT_DIR}/agents" >&2
  exit 1
fi

AGENTS_DEST="${CLAUDE_DIR}/agents"
SKILL_DEST_DIR="${CLAUDE_DIR}/skills/council"
SKILL_DEST="${SKILL_DEST_DIR}/SKILL.md"

echo "Installing Council of High Intelligence..."
echo "Target directory: ${CLAUDE_DIR}"

echo "Creating destination directories..."
run_cmd mkdir -p "${AGENTS_DEST}" "${SKILL_DEST_DIR}"

echo "Installing council agents..."
installed_count=0
for agent_file in "${agent_files[@]}"; do
  run_cmd install -m 0644 "${agent_file}" "${AGENTS_DEST}/"
  ((installed_count+=1))
done

echo "Installing council skill..."
run_cmd install -m 0644 "${SCRIPT_DIR}/SKILL.md" "${SKILL_DEST}"

echo
echo "Done."
echo "  Installed ${installed_count} council agents to ${AGENTS_DEST}"
echo "  Installed skill to ${SKILL_DEST}"
echo "Restart Claude Code and use /council to convene the council."
