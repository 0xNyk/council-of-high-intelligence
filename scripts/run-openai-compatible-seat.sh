#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: $0 BASE_URL MODEL PROMPT_FILE API_KEY_ENV [REASONING_EFFORT]" >&2
  exit 2
}

[[ $# -ge 4 && $# -le 5 ]] || usage

base_url="${1%/}"
model="$2"
prompt_file="$3"
api_key_env="$4"
reasoning_effort="${5:-}"

[[ -f "$prompt_file" && ! -L "$prompt_file" ]] || {
  echo "prompt file must be a regular, non-symlink file" >&2
  exit 2
}

case "${api_key_env}:${base_url}:${model}" in
  MODEL_API_KEY:https://api.meta.ai/v1:muse-spark-1.1)
    ;;
  NVIDIA_API_KEY:https://integrate.api.nvidia.com/v1:deepseek-ai/deepseek-v4-pro | \
  NVIDIA_API_KEY:https://integrate.api.nvidia.com/v1:moonshotai/kimi-k2.6 | \
  NVIDIA_API_KEY:https://integrate.api.nvidia.com/v1:minimaxai/minimax-m2.7 | \
  NVIDIA_API_KEY:https://integrate.api.nvidia.com/v1:z-ai/glm-5.1 | \
  NVIDIA_API_KEY:https://integrate.api.nvidia.com/v1:qwen/qwen3.5-397b-a17b)
    ;;
  *)
    echo "unsupported provider endpoint, model, or credential binding" >&2
    exit 2
    ;;
esac

case "$reasoning_effort" in
  "" | low | medium | high | xhigh)
    ;;
  *)
    echo "unsupported reasoning effort" >&2
    exit 2
    ;;
esac

api_key="${!api_key_env:-}"
[[ -n "$api_key" ]] || {
  echo "required API key is unavailable" >&2
  exit 3
}

command -v curl >/dev/null 2>&1 || {
  echo "curl is required" >&2
  exit 4
}
command -v jq >/dev/null 2>&1 || {
  echo "jq is required" >&2
  exit 4
}

request_file="$(mktemp)"
cleanup() {
  rm -f "$request_file"
}
trap cleanup EXIT

jq -n \
  --arg model "$model" \
  --rawfile prompt "$prompt_file" \
  --arg reasoning_effort "$reasoning_effort" \
  '{
    model: $model,
    messages: [
      {
        role: "system",
        content: "You are operating as a council member in a structured deliberation."
      },
      {role: "user", content: $prompt}
    ],
    max_completion_tokens: 2400
  }
  + (if $reasoning_effort == "" then {} else {reasoning_effort: $reasoning_effort} end)' \
  >"$request_file"

response="$(
  curl --fail-with-body --silent --show-error \
    -X POST "${base_url}/chat/completions" \
    -H @<(printf 'Authorization: Bearer %s\n' "$api_key") \
    -H "Content-Type: application/json" \
    --data-binary "@${request_file}"
)"

jq -er '
  .choices[0].message.content
  | select(type == "string" and length > 0)
' <<<"$response"
