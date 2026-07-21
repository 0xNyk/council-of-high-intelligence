#!/usr/bin/env bash
set -euo pipefail

# Council of High Intelligence — Provider Detection Script
# Detects available LLM providers and outputs structured JSON to stdout.
# Usage: ./scripts/detect-providers.sh

TIMEOUT_SECONDS=5
# Longer bound for real model-call health checks: a generation round-trip is
# far slower than a `--version` probe, so it needs its own timeout.
PROBE_TIMEOUT_SECONDS=25

# --- Helper functions ---

json_provider() {
  local name="$1" available="$2" exec_method="$3" binary="$4" models="$5" extra="${6:-}"
  # Optional 6th arg = extra raw JSON fields (comma-joined, no leading comma).
  if [[ -n "$extra" ]]; then extra=",${extra}"; fi
  printf '{"name":"%s","available":%s,"exec_method":"%s","binary":"%s","models":[%s]%s}' \
    "$name" "$available" "$exec_method" "$binary" "$models" "$extra"
}

# JSON-escape a string for safe embedding in a JSON value (backslash, quote,
# and control chars). Keeps secrets out is the caller's job — this only makes
# arbitrary diagnostic text safe to place inside a JSON string.
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/ }"
  s="${s//$'\r'/ }"
  s="${s//$'\t'/ }"
  printf '%s' "$s"
}

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
providers+=("$(json_provider "anthropic" "true" "subagent" "native" '"opus","sonnet","haiku"')")

# OpenAI via Codex CLI
codex_bin="$(check_command codex)"
if [[ -n "$codex_bin" ]] && run_with_timeout codex --version >/dev/null 2>&1; then
  providers+=("$(json_provider "openai" "true" "codex_exec" "$codex_bin" '"gpt-5.4"')")
else
  providers+=("$(json_provider "openai" "false" "codex_exec" "${codex_bin:-not_found}" '')")
fi

# Google via Gemini CLI
# Detection uses a real, non-interactive health check instead of `--version`.
# `--version` only proves the binary exists; it says nothing about whether a
# model call will actually succeed. A tiny `gemini -p` probe exercises auth
# end-to-end and is transparent to HOW the key is supplied — OAuth
# (~/.gemini/oauth_creds.json), GEMINI_API_KEY / GOOGLE_API_KEY env vars, or
# the macOS Keychain all make the probe succeed, and we never read the secret.
gemini_bin="$(check_command gemini)"
gemini_available=false
gemini_auth="unknown"
gemini_diag=""
if [[ -z "$gemini_bin" ]]; then
  gemini_diag="gemini CLI not found on PATH"
else
  # Best-effort, non-secret auth hint (presence only — values are never read).
  if [[ -n "${GEMINI_API_KEY:-}" ]]; then
    gemini_auth="env:GEMINI_API_KEY"
  elif [[ -n "${GOOGLE_API_KEY:-}" ]]; then
    gemini_auth="env:GOOGLE_API_KEY"
  elif [[ -f "${HOME}/.gemini/oauth_creds.json" ]]; then
    gemini_auth="oauth"
  else
    gemini_auth="cli-managed"   # e.g. macOS Keychain: the CLI holds it, we don't
  fi

  # Non-interactive model probe. stdin from /dev/null so it can never block on
  # input; errexit disabled locally so we can capture the true exit code; a
  # dedicated longer timeout because this is a real generation call.
  _saved_to="$TIMEOUT_SECONDS"; TIMEOUT_SECONDS="$PROBE_TIMEOUT_SECONDS"
  set +e
  gemini_probe="$(run_with_timeout gemini -p "Reply exactly: OK" </dev/null 2>/dev/null)"
  gemini_rc=$?
  set -e
  TIMEOUT_SECONDS="$_saved_to"
  gemini_probe="$(printf '%s' "$gemini_probe" | tr -d '\r\n' | head -c 120)"

  if [[ "$gemini_rc" -eq 0 && -n "$gemini_probe" ]]; then
    gemini_available=true
    gemini_diag="health check passed (auth: ${gemini_auth})"
  elif [[ "$gemini_rc" -eq 124 ]]; then
    gemini_diag="health check timed out after ${PROBE_TIMEOUT_SECONDS}s (auth: ${gemini_auth}); try: gemini -p 'hi'"
  else
    gemini_diag="health check failed rc=${gemini_rc} (auth: ${gemini_auth}); try: gemini -p 'hi'"
  fi
fi
# Human-readable diagnostic to stderr so stdout stays valid JSON.
printf 'gemini detection: %s\n' "$gemini_diag" >&2
gemini_models=""
if [[ "$gemini_available" == true ]]; then gemini_models='"gemini-3-pro"'; fi
gemini_extra="$(printf '"auth":"%s","diagnostic":"%s"' "$(json_escape "$gemini_auth")" "$(json_escape "$gemini_diag")")"
providers+=("$(json_provider "google" "$gemini_available" "gemini_cli" "${gemini_bin:-not_found}" "$gemini_models" "$gemini_extra")")

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
  # Cross-family defaults so a Cursor seat adds real diversity, not a
  # second Anthropic-biased model. Verify live IDs with `cursor-agent --list-models`.
  providers+=("$(json_provider "cursor_cli" "true" "cursor_cli" "$cursor_bin" '"gpt-5.4-high","claude-opus-4-7-thinking-high","gemini-3-pro","grok-4"')")
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
    # Default model suggestions (verify live IDs at build.nvidia.com/models).
    nim_models='"deepseek-ai/deepseek-v4-pro","moonshotai/kimi-k2.6","minimaxai/minimax-m2.7","z-ai/glm-5.1","qwen/qwen3.5-397b-a17b"'
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
