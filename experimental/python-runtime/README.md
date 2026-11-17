# Experimental: Python runtime (Agno / LangGraph)

> **Experimental and opt-in.** This runtime is not installed by `install.sh` and is not
> part of the `/council` skill. It **bypasses the skill's multi-provider routing**
> (`scripts/detect-providers.sh`, `configs/provider-model-slots*.yaml`): every seat,
> including the Chairman, runs on the single endpoint and model you configure below.
> Its interface may change or be removed without notice.

It runs the same three-round protocol (blind analysis → anonymized cross-examination →
final positions → Chairman synthesis) as a standalone Python program, with either an
[Agno](https://github.com/agno-agi/agno) or a [LangGraph](https://github.com/langchain-ai/langgraph)
backend. Personas are read from the repository's [`agents/`](../../agents/) directory.

## Where requests go

All traffic goes to **one OpenAI-compatible endpoint that you choose**. Each call sends:

- the persona instructions (Identity, Grounding Protocol, Analytical Method from `agents/council-*.md`),
- your problem statement and the transcript of earlier rounds,
- `COUNCIL_API_KEY` as the bearer token.

Nothing is sent anywhere else by this code. There is **no default endpoint**: if
`COUNCIL_BASE_URL` or `COUNCIL_MODEL` is unset, the runtime exits with an error before
making any request, so the client library's built-in default (api.openai.com) is never
used implicitly.

| Variable | Required | Meaning |
|---|---|---|
| `COUNCIL_BASE_URL` | yes | OpenAI-compatible base URL, e.g. `https://openrouter.ai/api/v1`, `http://localhost:11434/v1` (Ollama), `http://localhost:4000` (LiteLLM) |
| `COUNCIL_MODEL` | yes | Model id served by that endpoint. Used for **every** call, members and Chairman |
| `COUNCIL_API_KEY` | yes | Key for that endpoint (any non-empty value for local servers that ignore it) |
| `COUNCIL_REASONING` | no | `true` (default) adds `{"reasoning": {"enabled": true}}` to the request body; set `false` for endpoints that reject unknown fields |

A full run makes `3 × members + 1` requests.

## Install

Dependencies are bounded in [`pyproject.toml`](pyproject.toml) and locked in
[`uv.lock`](uv.lock). Python 3.10+ is required. From this directory:

```bash
uv sync --extra agno        # Agno backend
uv sync --extra langgraph   # LangGraph backend
uv sync --all-extras        # both
```

## Run

```bash
export COUNCIL_BASE_URL="https://openrouter.ai/api/v1"
export COUNCIL_MODEL="deepseek/deepseek-v4-flash"
export COUNCIL_API_KEY="..."

uv run python run_framework.py --framework agno --members socrates "State the word hello once."
uv run python run_framework.py --framework langgraph --members socrates,sun-tzu,aurelius \
  "Is scaling a monolith always better?"
```

`--members` accepts any of the 18 persona slugs in `agents/` (without the `council-` prefix).

## Layout

```text
run_framework.py            CLI runner (--framework agno|langgraph, --members)
agno_council.py             minimal Agno example
council_engine/
  core.py                   env config, persona parser, Round 2 anonymization
  agno_engine.py            Agno backend
  langgraph_engine.py       LangGraph StateGraph backend
```
