#!/usr/bin/env bash
set -euo pipefail

# Council of High Intelligence — Provider Detection Script
# Detects available LLM providers and outputs structured JSON to stdout.
# Usage: ./scripts/detect-providers.sh [--config PATH] [--check-config]

TIMEOUT_SECONDS=5
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_CONFIG="${COUNCIL_MODEL_CONFIG:-${SCRIPT_DIR}/../configs/auto-route-defaults.yaml}"
CHECK_CONFIG_ONLY=false

usage() {
  cat <<'EOF'
Usage: ./scripts/detect-providers.sh [--config PATH] [--check-config]

Options:
  --config PATH   Read model IDs from this catalog instead of the bundled one
  --check-config  Validate the catalog without probing provider CLIs
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config)
      [[ $# -ge 2 ]] || { echo "Error: --config requires a path" >&2; exit 2; }
      MODEL_CONFIG="$2"
      shift 2
      ;;
    --check-config)
      CHECK_CONFIG_ONLY=true
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown argument '$1'" >&2
      usage >&2
      exit 2
      ;;
  esac
done

# --- Helper functions ---

json_provider() {
  local name="$1" available="$2" exec_method="$3" binary="$4" models="$5"
  printf '{"name":"%s","available":%s,"exec_method":"%s","binary":"%s","models":[%s]}' \
    "$name" "$available" "$exec_method" "$binary" "$models"
}

# Read one scalar from provider_models.<provider>.<tier>. This deliberately
# supports only the small, stable YAML subset used by the catalog, avoiding a
# runtime dependency on yq/Python in installed skills.
model_config_get() {
  local provider="$1" tier="$2"
  awk -v provider="$provider" -v tier="$tier" '
    /^provider_models:[[:space:]]*$/ { in_models=1; next }
    in_models && /^[^[:space:]#]/ { exit }
    in_models && $0 ~ "^  " provider ":[[:space:]]*$" { in_provider=1; next }
    in_provider && /^  [^[:space:]][^:]*:[[:space:]]*$/ { exit }
    in_provider && $0 ~ "^    " tier ":[[:space:]]*" {
      value=$0
      sub("^    " tier ":[[:space:]]*", "", value)
      sub(/[[:space:]]+#.*$/, "", value)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      if ((value ~ /^\".*\"$/) || (value ~ /^\047.*\047$/)) {
        value=substr(value, 2, length(value)-2)
      }
      if (value != "null" && value != "~") print value
      exit
    }
  ' "$MODEL_CONFIG"
}

json_quote() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '"%s"' "$value"
}

provider_models_json() {
  local provider="$1" tier value result="" seen="|"
  for tier in high mid low; do
    value="$(model_config_get "$provider" "$tier")"
    [[ -n "$value" ]] || continue
    if [[ "$seen" != *"|${value}|"* ]]; then
      [[ -z "$result" ]] || result+=","
      result+="$(json_quote "$value")"
      seen+="${value}|"
    fi
  done
  printf '%s' "$result"
}

validate_model_config() {
  local provider tier value failed=false
  [[ -r "$MODEL_CONFIG" ]] || {
    echo "Error: model catalog is not readable: $MODEL_CONFIG" >&2
    return 1
  }
  for provider in anthropic openai google; do
    for tier in high mid; do
      value="$(model_config_get "$provider" "$tier")"
      if [[ -z "$value" ]]; then
        echo "Error: missing provider_models.${provider}.${tier} in $MODEL_CONFIG" >&2
        failed=true
      elif [[ "$value" =~ [[:space:]\"] ]]; then
        echo "Error: invalid model ID at provider_models.${provider}.${tier}: '$value'" >&2
        failed=true
      fi
    done
  done
  [[ "$failed" == false ]]
}

validate_model_config
if [[ "$CHECK_CONFIG_ONLY" == true ]]; then
  printf 'Model catalog OK: %s\n' "$MODEL_CONFIG"
  exit 0
fi

check_command() {
  command -v "$1" 2>/dev/null || echo ""
}

# macOS-compatible timeout using perl (no coreutils required)
run_with_timeout() {
  perl -e '
    use POSIX ":sys_wait_h";
    my $timeout = shift @ARGV;
    my $pid = fork();
    if ($pid == 0) { exec @ARGV; exit 1; }
    my $elapsed = 0;
    while ($elapsed < $timeout) {
      if (waitpid($pid, WNOHANG) > 0) { exit ($? >> 8); }
      select(undef, undef, undef, 0.1);
      $elapsed += 0.1;
    }
    kill("TERM", $pid);
    waitpid($pid, 0);
    exit 124;
  ' "$TIMEOUT_SECONDS" "$@" 2>/dev/null
}

# --- Detect each provider ---

providers=()

# Anthropic — always available (host runtime)
providers+=("$(json_provider "anthropic" "true" "subagent" "native" "$(provider_models_json anthropic)")")

# OpenAI via Codex CLI
codex_bin="$(check_command codex)"
if [[ -n "$codex_bin" ]] && run_with_timeout codex --version >/dev/null 2>&1; then
  providers+=("$(json_provider "openai" "true" "codex_exec" "$codex_bin" "$(provider_models_json openai)")")
else
  providers+=("$(json_provider "openai" "false" "codex_exec" "${codex_bin:-not_found}" '')")
fi

# Google via Gemini CLI
gemini_bin="$(check_command gemini)"
if [[ -n "$gemini_bin" ]] && run_with_timeout gemini --version >/dev/null 2>&1; then
  providers+=("$(json_provider "google" "true" "gemini_cli" "$gemini_bin" "$(provider_models_json google)")")
else
  providers+=("$(json_provider "google" "false" "gemini_cli" "${gemini_bin:-not_found}" '')")
fi

# Ollama (local models)
ollama_bin="$(check_command ollama)"
ollama_available=false
ollama_models=""
if [[ -n "$ollama_bin" ]]; then
  # Check if ollama server is running by listing models
  if model_list="$(run_with_timeout ollama list 2>/dev/null)"; then
    ollama_available=true
    # Parse model names from 'ollama list' output (skip header line, take first column)
    ollama_models="$(echo "$model_list" | tail -n +2 | awk '{print $1}' | head -5 | \
      sed 's/.*/"&"/' | paste -sd ',' -)"
  fi
fi
providers+=("$(json_provider "ollama" "$ollama_available" "ollama_run" "${ollama_bin:-not_found}" "$ollama_models")")

# Cursor via Cursor CLI (cursor-agent) — model aggregator: serves GPT-5.x,
# Claude, Gemini, and Grok families through one binary + CURSOR_API_KEY.
cursor_bin="$(check_command cursor-agent)"
if [[ -n "$cursor_bin" ]] && run_with_timeout cursor-agent --version >/dev/null 2>&1; then
  # Cross-family defaults come from the same canonical catalog.
  providers+=("$(json_provider "cursor_cli" "true" "cursor_cli" "$cursor_bin" "$(provider_models_json cursor_cli)")")
else
  providers+=("$(json_provider "cursor_cli" "false" "cursor_cli" "${cursor_bin:-not_found}" '')")
fi

# NVIDIA NIM (OpenAI-compatible hosted endpoint at build.nvidia.com)
# Detection: NVIDIA_API_KEY env var + optional reachability check.
nim_available=false
nim_models=""
nim_endpoint="https://integrate.api.nvidia.com/v1"
if [[ -n "${NVIDIA_API_KEY:-}" ]]; then
  # Verify the key is not a placeholder (real keys start with nvapi-)
  if [[ "${NVIDIA_API_KEY}" =~ ^nvapi- ]]; then
    # Optional: confirm catalog reachability. Skip if curl missing or offline.
    # The auth header is passed via process substitution so the key never
    # appears in curl's argv (visible to other local users via `ps`).
    if command -v curl >/dev/null 2>&1; then
      if run_with_timeout curl -sf -o /dev/null \
          -H @<(printf 'Authorization: Bearer %s\n' "${NVIDIA_API_KEY}") \
          "${nim_endpoint}/models" 2>/dev/null; then
        nim_available=true
      fi
    else
      # Curl unavailable; trust env var presence + key prefix as availability signal.
      nim_available=true
    fi
    nim_models="$(provider_models_json nvidia_nim)"
  fi
fi
providers+=("$(json_provider "nvidia_nim" "$nim_available" "openai_compatible_api" "$nim_endpoint" "$nim_models")")

# --- Build JSON output ---

available_count=0
for p in "${providers[@]}"; do
  if echo "$p" | grep -q '"available":true'; then
    ((available_count+=1))
  fi
done

multi_provider=false
if [[ "$available_count" -ge 2 ]]; then
  multi_provider=true
fi

# Assemble providers array
provider_json=""
for i in "${!providers[@]}"; do
  if [[ $i -gt 0 ]]; then
    provider_json+=","
  fi
  provider_json+="${providers[$i]}"
done

printf '{"providers":[%s],"provider_count":%d,"multi_provider":%s}\n' \
  "$provider_json" "$available_count" "$multi_provider"
