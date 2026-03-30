#!/usr/bin/env bash
set -euo pipefail

# Council of High Intelligence — Provider Detection Script
# Detects available LLM providers and outputs structured JSON to stdout.
# Usage: ./scripts/detect-providers.sh

TIMEOUT_SECONDS=5

# --- Helper functions ---

json_provider() {
  local name="$1" available="$2" exec_method="$3" binary="$4" models="$5"
  printf '{"name":"%s","available":%s,"exec_method":"%s","binary":"%s","models":[%s]}' \
    "$name" "$available" "$exec_method" "$binary" "$models"
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
  providers+=("$(json_provider "openai" "true" "codex_exec" "$codex_bin" '"o3","o4-mini"')")
else
  providers+=("$(json_provider "openai" "false" "codex_exec" "${codex_bin:-not_found}" '')")
fi

# Google via Gemini CLI
gemini_bin="$(check_command gemini)"
if [[ -n "$gemini_bin" ]] && run_with_timeout gemini --version >/dev/null 2>&1; then
  providers+=("$(json_provider "google" "true" "gemini_cli" "$gemini_bin" '"gemini-2.5-pro"')")
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
