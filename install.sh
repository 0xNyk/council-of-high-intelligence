#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
Usage: ./install.sh [--claude-dir PATH] [--codex-dir PATH] [--gemini-dir PATH] [--codex] [--codex-only] [--gemini] [--gemini-only] [--copy-configs] [--dry-run] [--help]

Install Council of High Intelligence into Claude Code, Codex, and/or Gemini CLI skill directories.

Options:
  --claude-dir PATH  Target Claude config directory (default: ~/.claude)
  --codex-dir PATH   Target Codex config directory (default: ~/.codex)
  --gemini-dir PATH  Target Gemini config directory (default: ~/.gemini)
  --codex            Also install a Codex-compatible council skill
  --codex-only       Install only the Codex skill
  --gemini           Also install a Gemini-compatible council skill
  --gemini-only      Install only the Gemini skill
  --copy-configs     Also install repo configs/ into skill config folders
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
    --codex-dir)
      if [[ $# -lt 2 ]]; then
        echo "Error: --codex-dir requires a path argument" >&2
        usage
        exit 1
      fi
      CODEX_DIR="$2"
      shift 2
      ;;
    --gemini-dir)
      if [[ $# -lt 2 ]]; then
        echo "Error: --gemini-dir requires a path argument" >&2
        usage
        exit 1
      fi
      GEMINI_DIR="$2"
      shift 2
      ;;
    --codex)
      INSTALL_CODEX=true
      shift
      ;;
    --codex-only)
      INSTALL_CLAUDE=false
      INSTALL_CODEX=true
      shift
      ;;
    --gemini)
      INSTALL_GEMINI=true
      shift
      ;;
    --gemini-only)
      INSTALL_CLAUDE=false
      INSTALL_GEMINI=true
      shift
      ;;
    --copy-configs)
      COPY_CONFIGS=true
      shift
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

if [[ "${INSTALL_CLAUDE}" == false ]] && [[ "${INSTALL_CODEX}" == false ]] && [[ "${INSTALL_GEMINI}" == false ]]; then
  echo "Error: no install target selected" >&2
  usage
  exit 1
fi

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

if [[ "${INSTALL_CLAUDE}" == true ]] && [[ ! -f "${SCRIPT_DIR}/SKILL.md" ]]; then
  echo "Error: SKILL.md not found at ${SCRIPT_DIR}/SKILL.md" >&2
  exit 1
fi

if [[ "${INSTALL_CODEX}" == true ]] && [[ ! -f "${SCRIPT_DIR}/SKILL.codex.md" ]]; then
  echo "Error: SKILL.codex.md not found at ${SCRIPT_DIR}/SKILL.codex.md" >&2
  exit 1
fi

if [[ "${INSTALL_GEMINI}" == true ]] && [[ ! -f "${SCRIPT_DIR}/SKILL.gemini.md" ]]; then
  echo "Error: SKILL.gemini.md not found at ${SCRIPT_DIR}/SKILL.gemini.md" >&2
  exit 1
fi

shopt -s nullglob
agent_files=("${SCRIPT_DIR}"/agents/council-*.md)
shopt -u nullglob

if [[ ${#agent_files[@]} -eq 0 ]]; then
  echo "Error: no council agent files found under ${SCRIPT_DIR}/agents" >&2
  exit 1
fi

CONFIGS_SRC_DIR="${SCRIPT_DIR}/configs"

echo "Installing Council of High Intelligence..."
if [[ "${INSTALL_CLAUDE}" == true ]]; then
  AGENTS_DEST="${CLAUDE_DIR}/agents"
  CLAUDE_SKILL_DEST_DIR="${CLAUDE_DIR}/skills/council"
  CLAUDE_SKILL_DEST="${CLAUDE_SKILL_DEST_DIR}/SKILL.md"
  CLAUDE_CONFIGS_DEST_DIR="${CLAUDE_SKILL_DEST_DIR}/configs"
  CLAUDE_SCRIPTS_DEST_DIR="${CLAUDE_SKILL_DEST_DIR}/scripts"

  echo "Claude target directory: ${CLAUDE_DIR}"
  echo "Creating Claude destination directories..."
  run_cmd mkdir -p "${AGENTS_DEST}" "${CLAUDE_SKILL_DEST_DIR}"

  echo "Installing Claude council agents..."
  installed_count=0
  for agent_file in "${agent_files[@]}"; do
    run_cmd install -m 0644 "${agent_file}" "${AGENTS_DEST}/"
    ((installed_count+=1))
  done

  echo "Installing Claude council skill..."
  run_cmd install -m 0644 "${SCRIPT_DIR}/SKILL.md" "${CLAUDE_SKILL_DEST}"

  echo "Installing Claude council scripts..."
  run_cmd mkdir -p "${CLAUDE_SCRIPTS_DEST_DIR}"
  scripts_installed=0
  shopt -s nullglob
  script_files=("${SCRIPT_DIR}"/scripts/detect-*.sh)
  shopt -u nullglob
  for script_file in "${script_files[@]}"; do
    run_cmd install -m 0755 "${script_file}" "${CLAUDE_SCRIPTS_DEST_DIR}/"
    ((scripts_installed+=1))
  done

  claude_configs_installed=0
  if [[ "$COPY_CONFIGS" == true ]]; then
    if [[ -d "${CONFIGS_SRC_DIR}" ]]; then
      run_cmd mkdir -p "${CLAUDE_CONFIGS_DEST_DIR}"
      shopt -s nullglob
      config_files=("${CONFIGS_SRC_DIR}"/*)
      shopt -u nullglob
      for config_file in "${config_files[@]}"; do
        if [[ -f "${config_file}" ]]; then
          run_cmd install -m 0644 "${config_file}" "${CLAUDE_CONFIGS_DEST_DIR}/"
          ((claude_configs_installed+=1))
        fi
      done
    else
      echo "Warning: --copy-configs was set but ${CONFIGS_SRC_DIR} does not exist."
    fi
  fi
fi

if [[ "${INSTALL_CODEX}" == true ]]; then
  CODEX_SKILL_DEST_DIR="${CODEX_DIR}/skills/council"
  CODEX_SKILL_DEST="${CODEX_SKILL_DEST_DIR}/SKILL.md"
  CODEX_AGENTS_DEST_DIR="${CODEX_SKILL_DEST_DIR}/agents"
  CODEX_SCRIPTS_DEST_DIR="${CODEX_SKILL_DEST_DIR}/scripts"
  CODEX_CONFIGS_DEST_DIR="${CODEX_SKILL_DEST_DIR}/configs"

  echo "Codex target directory: ${CODEX_DIR}"
  echo "Creating Codex destination directories..."
  run_cmd mkdir -p "${CODEX_SKILL_DEST_DIR}" "${CODEX_AGENTS_DEST_DIR}" "${CODEX_SCRIPTS_DEST_DIR}"

  echo "Installing Codex council skill..."
  run_cmd install -m 0644 "${SCRIPT_DIR}/SKILL.codex.md" "${CODEX_SKILL_DEST}"

  echo "Installing Codex council agents..."
  codex_agents_installed=0
  for agent_file in "${agent_files[@]}"; do
    run_cmd install -m 0644 "${agent_file}" "${CODEX_AGENTS_DEST_DIR}/"
    ((codex_agents_installed+=1))
  done

  echo "Installing Codex council scripts..."
  codex_scripts_installed=0
  shopt -s nullglob
  codex_script_files=("${SCRIPT_DIR}"/scripts/detect-*.sh)
  shopt -u nullglob
  for script_file in "${codex_script_files[@]}"; do
    run_cmd install -m 0755 "${script_file}" "${CODEX_SCRIPTS_DEST_DIR}/"
    ((codex_scripts_installed+=1))
  done

  codex_configs_installed=0
  if [[ "$COPY_CONFIGS" == true ]]; then
    if [[ -d "${CONFIGS_SRC_DIR}" ]]; then
      run_cmd mkdir -p "${CODEX_CONFIGS_DEST_DIR}"
      shopt -s nullglob
      codex_config_files=("${CONFIGS_SRC_DIR}"/*)
      shopt -u nullglob
      for config_file in "${codex_config_files[@]}"; do
        if [[ -f "${config_file}" ]]; then
          run_cmd install -m 0644 "${config_file}" "${CODEX_CONFIGS_DEST_DIR}/"
          ((codex_configs_installed+=1))
        fi
      done
    else
      echo "Warning: --copy-configs was set but ${CONFIGS_SRC_DIR} does not exist."
    fi
  fi
fi

if [[ "${INSTALL_GEMINI}" == true ]]; then
  echo
  GEMINI_EXT_ROOT="${GEMINI_DIR}/extensions/council-of-high-intelligence"
  GEMINI_EXT_DEST_DIR="${GEMINI_EXT_ROOT}/skills/council"
  GEMINI_SKILL_DEST="${GEMINI_EXT_DEST_DIR}/SKILL.md"
  GEMINI_AGENTS_DEST_DIR="${GEMINI_EXT_DEST_DIR}/agents"
  GEMINI_SCRIPTS_DEST_DIR="${GEMINI_EXT_DEST_DIR}/scripts"
  GEMINI_CONFIGS_DEST_DIR="${GEMINI_EXT_DEST_DIR}/configs"

  echo "Gemini target directory: ${GEMINI_DIR}"
  echo "Creating Gemini destination directories..."
  run_cmd mkdir -p "${GEMINI_EXT_DEST_DIR}" "${GEMINI_AGENTS_DEST_DIR}" "${GEMINI_SCRIPTS_DEST_DIR}"

  echo "Writing gemini-extension.json manifest..."
  if [[ "$DRY_RUN" == false ]]; then
    cat <<EOF > "${GEMINI_EXT_ROOT}/gemini-extension.json"
{
  "name": "council-of-high-intelligence",
  "version": "1.0.0",
  "description": "Council of High Intelligence multiple persona deliberation system"
}
EOF
  else
    echo "[dry-run] Create ${GEMINI_EXT_ROOT}/gemini-extension.json"
  fi

  echo "Installing Gemini council skill..."
  run_cmd install -m 0644 "${SCRIPT_DIR}/SKILL.gemini.md" "${GEMINI_SKILL_DEST}"

  echo "Installing Gemini council agents..."
  gemini_agents_installed=0
  for agent_file in "${agent_files[@]}"; do
    run_cmd install -m 0644 "${agent_file}" "${GEMINI_AGENTS_DEST_DIR}/"
    ((gemini_agents_installed+=1))
  done

  echo "Installing Gemini council scripts..."
  gemini_scripts_installed=0
  shopt -s nullglob
  gemini_script_files=("${SCRIPT_DIR}"/scripts/detect-*.sh)
  shopt -u nullglob
  for script_file in "${gemini_script_files[@]}"; do
    run_cmd install -m 0755 "${script_file}" "${GEMINI_SCRIPTS_DEST_DIR}/"
    ((gemini_scripts_installed+=1))
  done

  gemini_configs_installed=0
  if [[ "$COPY_CONFIGS" == true ]]; then
    if [[ -d "${CONFIGS_SRC_DIR}" ]]; then
      run_cmd mkdir -p "${GEMINI_CONFIGS_DEST_DIR}"
      shopt -s nullglob
      gemini_config_files=("${CONFIGS_SRC_DIR}"/*)
      shopt -u nullglob
      for config_file in "${gemini_config_files[@]}"; do
        if [[ -f "${config_file}" ]]; then
          run_cmd install -m 0644 "${config_file}" "${GEMINI_CONFIGS_DEST_DIR}/"
          ((gemini_configs_installed+=1))
        fi
      done
    else
      echo "Warning: --copy-configs was set but ${CONFIGS_SRC_DIR} does not exist."
    fi
  fi
fi

echo
echo "Done."
if [[ "${INSTALL_CLAUDE}" == true ]]; then
  echo "  Installed ${installed_count} council agents to ${AGENTS_DEST}"
  echo "  Installed skill to ${CLAUDE_SKILL_DEST}"
  echo "  Installed ${scripts_installed} scripts to ${CLAUDE_SCRIPTS_DEST_DIR}"
  if [[ "$COPY_CONFIGS" == true ]]; then
    echo "  Installed ${claude_configs_installed} config files to ${CLAUDE_CONFIGS_DEST_DIR}"
  fi
fi
if [[ "${INSTALL_CODEX}" == true ]]; then
  echo "  Installed Codex skill to ${CODEX_SKILL_DEST}"
  echo "  Installed ${codex_agents_installed} Codex council agents to ${CODEX_AGENTS_DEST_DIR}"
  echo "  Installed ${codex_scripts_installed} Codex scripts to ${CODEX_SCRIPTS_DEST_DIR}"
  if [[ "$COPY_CONFIGS" == true ]]; then
    echo "  Installed ${codex_configs_installed} Codex config files to ${CODEX_CONFIGS_DEST_DIR}"
  fi
fi
if [[ "${INSTALL_GEMINI}" == true ]]; then
  echo "  Installed Gemini skill to ${GEMINI_SKILL_DEST}"
  echo "  Installed ${gemini_agents_installed} Gemini council agents to ${GEMINI_AGENTS_DEST_DIR}"
  echo "  Installed ${gemini_scripts_installed} Gemini scripts to ${GEMINI_SCRIPTS_DEST_DIR}"
  if [[ "$COPY_CONFIGS" == true ]]; then
    echo "  Installed ${gemini_configs_installed} Gemini config files to ${GEMINI_CONFIGS_DEST_DIR}"
  fi
fi

echo "Restart your CLI client(s) and use /council to convene the council."
