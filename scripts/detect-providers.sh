#!/usr/bin/env bash
set -euo pipefail

# Council of High Intelligence - provider detection.
# Usage: ./scripts/detect-providers.sh [--host claude|codex|gemini]

TIMEOUT_SECONDS=8
HOST_RUNTIME="codex"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      if [[ $# -lt 2 ]]; then
        echo "--host requires claude, codex, or gemini" >&2
        exit 2
      fi
      HOST_RUNTIME="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! "$HOST_RUNTIME" =~ ^(claude|codex|gemini)$ ]]; then
  echo "usage: $0 [--host claude|codex|gemini]" >&2
  exit 2
fi

json_provider() {
  local name="$1" available="$2" exec_method="$3" binary="$4" models_json="$5"
  local base_url="${6:-}" api_key_env="${7:-}" reasoning_effort="${8:-}"

  jq -cn \
    --arg name "$name" \
    --argjson available "$available" \
    --arg exec_method "$exec_method" \
    --arg binary "$binary" \
    --argjson models "[$models_json]" \
    --arg base_url "$base_url" \
    --arg api_key_env "$api_key_env" \
    --arg reasoning_effort "$reasoning_effort" \
    '{name:$name, available:$available, exec_method:$exec_method, binary:$binary, models:$models}
      + (if $base_url == "" then {} else {base_url:$base_url} end)
      + (if $api_key_env == "" then {} else {api_key_env:$api_key_env} end)
      + (if $reasoning_effort == "" then {} else {reasoning_effort:$reasoning_effort} end)'
}

check_command() {
  command -v "$1" 2>/dev/null || true
}

# macOS-compatible timeout without requiring GNU coreutils.
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

providers=()

# Anthropic is native only when Claude is the coordinator. Other hosts must use
# a real authenticated Claude CLI call; a host subagent is not Anthropic.
claude_bin="$(check_command claude)"
if [[ "$HOST_RUNTIME" == "claude" ]]; then
  providers+=("$(json_provider anthropic true subagent native '"claude-fable-5","opus"')")
elif [[ -n "$claude_bin" ]] \
  && auth_output="$(run_with_timeout claude auth status 2>/dev/null || true)" \
  && grep -Eq '"loggedIn"[[:space:]]*:[[:space:]]*true' <<<"$auth_output"; then
  providers+=("$(json_provider anthropic true claude_cli "$claude_bin" '"claude-fable-5","opus"')")
else
  providers+=("$(json_provider anthropic false claude_cli "${claude_bin:-not_found}" '')")
fi

# OpenAI via Codex CLI.
codex_bin="$(check_command codex)"
if [[ -n "$codex_bin" ]] && run_with_timeout codex --version >/dev/null 2>&1; then
  providers+=("$(json_provider openai true codex_exec "$codex_bin" '"gpt-5.6-sol"' '' '' high)")
else
  providers+=("$(json_provider openai false codex_exec "${codex_bin:-not_found}" '')")
fi

# Google via Antigravity first, then Gemini CLI.
agy_bin="$(check_command agy)"
gemini_bin="$(check_command gemini)"
if [[ -n "$agy_bin" ]] && model_output="$(run_with_timeout agy models 2>/dev/null || true)" \
  && grep -q 'Gemini 3.1 Pro (High)' <<<"$model_output"; then
  google_models='"Gemini 3.1 Pro (High)"'
  if grep -q 'Gemini 3.5 Flash (High)' <<<"$model_output"; then
    google_models+=',"Gemini 3.5 Flash (High)"'
  fi
  providers+=("$(json_provider google true antigravity_cli "$agy_bin" "$google_models")")
elif [[ -n "$gemini_bin" ]] && run_with_timeout gemini --version >/dev/null 2>&1; then
  providers+=("$(json_provider google true gemini_cli "$gemini_bin" '"gemini-3.1-pro"')")
else
  providers+=("$(json_provider google false antigravity_cli "${agy_bin:-${gemini_bin:-not_found}}" '')")
fi

# xAI via the authenticated Grok CLI.
grok_bin="$(check_command grok)"
if [[ -n "$grok_bin" ]] && grok_models="$(run_with_timeout grok models 2>/dev/null || true)" \
  && grep -q 'grok-4.5' <<<"$grok_models"; then
  providers+=("$(json_provider xai true grok_cli "$grok_bin" '"grok-4.5"' '' '' high)")
else
  providers+=("$(json_provider xai false grok_cli "${grok_bin:-not_found}" '')")
fi

# Ollama local models.
ollama_bin="$(check_command ollama)"
ollama_available=false
ollama_models=""
if [[ -n "$ollama_bin" ]] && model_list="$(run_with_timeout ollama list 2>/dev/null || true)" \
  && [[ -n "$model_list" ]]; then
  ollama_available=true
  ollama_models="$(tail -n +2 <<<"$model_list" | awk '{print $1}' | head -5 | jq -R . | paste -sd ',' -)"
fi
providers+=("$(json_provider ollama "$ollama_available" ollama_run "${ollama_bin:-not_found}" "$ollama_models")")

# Cursor is an aggregator and counts as one provider for spread.
cursor_bin="$(check_command cursor-agent)"
if [[ -n "$cursor_bin" ]] && run_with_timeout cursor-agent --version >/dev/null 2>&1; then
  providers+=("$(json_provider cursor_cli true cursor_cli "$cursor_bin" '"gpt-5.6-sol","claude-fable-5","Gemini 3.1 Pro (High)","grok-4.5"')")
else
  providers+=("$(json_provider cursor_cli false cursor_cli "${cursor_bin:-not_found}" '')")
fi

# NVIDIA NIM OpenAI-compatible endpoint.
nim_available=false
nim_endpoint="https://integrate.api.nvidia.com/v1"
nim_models=""
if [[ "${NVIDIA_API_KEY:-}" =~ ^nvapi- ]]; then
  # Keep the key out of curl's argv so other local users cannot read it via ps.
  if ! command -v curl >/dev/null 2>&1 || run_with_timeout curl -fsS -o /dev/null \
      -H @<(printf 'Authorization: Bearer %s\n' "${NVIDIA_API_KEY}") \
      "${nim_endpoint}/models"; then
    nim_available=true
  fi
  nim_models='"deepseek-ai/deepseek-v4-pro","moonshotai/kimi-k2.6","minimaxai/minimax-m2.7","z-ai/glm-5.1","qwen/qwen3.5-397b-a17b"'
fi
providers+=("$(json_provider nvidia_nim "$nim_available" openai_compatible_api "$nim_endpoint" "$nim_models" "$nim_endpoint" NVIDIA_API_KEY)")

printf '%s\n' "${providers[@]}" | jq -cs \
  --arg host_runtime "$HOST_RUNTIME" \
  '{host_runtime:$host_runtime, providers:., provider_count:([.[] | select(.available)] | length), multi_provider:([.[] | select(.available)] | length >= 2)}'
