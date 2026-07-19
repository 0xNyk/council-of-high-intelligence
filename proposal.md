# PROPOSAL: Modular Multi-Backend Agent Framework & Environment-Driven Configuration

## 💡 The Vision
The **Council of High Intelligence** is an amazing multi-agent deliberation prototype. I've been testing the project locally using the current CLI/subagent implementation, and the structured disagreement logic between the 18 personas works incredibly well.

Currently, the repository operates primarily as an automation/tooling layer built around shell scripts and Markdown personas. I would like to propose a structural evolution: transforming this script-based setup into a **modular, environment-driven Python Agent Framework**. 

## 🧠 Why move towards Frameworks (Agno / LangGraph)?
While the current CLI execution is great for quick terminal runs, moving the orchestration layer into dedicated agent frameworks solves a few critical limitations:
* **State & Memory Management:** As the deliberation protocol grows (e.g., cross-examination rounds), managing conversation state, history, and context windows becomes complex. Frameworks like **LangGraph** naturally handle structured state-charts and persistence.
* **Production-Grade Infrastructure:** Utilizing an ecosystem like **Agno (Phidata)** or LangGraph makes it significantly easier to integrate structured outputs, parallel tool calling, advanced logging, and future UI/API layers.

## 🚀 Core Concepts for the Evolution

1. **Interchangeable Engine Backends:** Moving the core protocol into a structured Python module. This would allow the council to seamlessly switch between different orchestration backends, starting with **Agno** and **LangGraph** (via StateGraph), while maintaining the exact same cognitive flow.
   
2. **Environment-Driven Configuration:** Decoupling API paths by introducing environment variables. This will allow users to seamlessly route the council's requests to OpenRouter, local **Ollama** instances, or enterprise **LiteLLM** proxies without hardcoding paths or relying heavily on global CLI binaries.

3. **Dynamic Council Scaling:** Upgrading the runner to dynamically parse, scale, and spin up any combination of the 18 personas currently defined in the `agents/` folder using a simple parametric flag (e.g., `--members socrates,feynman`).

4. **Resilience & Pacing:** Injecting basic fault tolerance, execution pacing (to easily avoid global provider rate limits), and strict validation handling into the sequential deliberation rounds to prevent silent parsing failures.

---

## 2. Core Architectural Enhancements

We have successfully engineered and structured the following key improvements into the repository:

```
council_engine/
  ├── __init__.py           # Unified exports
  ├── core.py               # Shared persona parser and config resolver
  ├── agno_engine.py        # Agno (Phidata) orchestration module
  └── langgraph_engine.py   # LangGraph StateGraph orchestration module
run_framework.py            # Parametric CLI runner
agno_council.py            # Backwards-compatible modular delegator
```

### A. Modular Package Separation (`council_engine/`)
* **Core Logic isolation (`core.py`):** Holds the Markdown persona parser (`parse_agent_file`) and the anonymization cross-examination algorithm (`anonymize_responses`). This ensures that no matter what agent library is used, the cognitive protocol remains identical.
* **Agno Backend (`agno_engine.py`):** Leverages Agno's `Agent` class for direct, high-level multi-persona coordination loops.
* **LangGraph Backend (`langgraph_engine.py`):** Leverages a fully state-chart mapped `StateGraph` containing isolated node operations (`round1`, `round2`, `round3`, `synthesis`). Perfect for long-running workflows and complex persistence.

### B. Platform-Agnostic Environment System
To prevent security leaks and platform-lockin, we removed all hardcoded fallback keys and direct dependencies on `OPENROUTER_API_KEY`:
* **Decoupled API Key & Endpoint Resolution (`get_config`):**
  * `COUNCIL_API_KEY`: Strictly reads the API key from environment variables (throws a clear `ValueError` if not set or if left as a placeholder).
  * `COUNCIL_BASE_URL`: Defines the destination endpoint. Makes the framework completely ready to map to a local **LiteLLM proxy** (`http://localhost:4000`) or an **Ollama** server, bypassing cloud aggregators entirely.
  * `COUNCIL_MODEL`: Set dynamically in the environment (e.g., `deepseek/deepseek-v4-flash`, `gpt-4o`, `claude-3-5-sonnet`).
  * `COUNCIL_REASONING`: Dynamically toggles DeepSeek's `"reasoning": {"enabled": true}` parameters in the JSON payload root.

### C. Dynamic Council Panel Scaling
* Modified the CLI runner to accept a dynamic `--members` parameter.
* Dynamically parses, scales, and instantiates any combination of the **18 high-intelligence agent personas** (Socrates, Sun Tzu, Feynman, Karpathy, Taleb, etc.) defined in the `agents/` folder.
* The anonymization algorithms automatically adapt the labels (`Member A`, `Member B`, ..., `Member N`) based on the length of the list, allowing completely generic scales (from a single member to a panel of ten).

### D. Pacing and Fault Tolerance
* Built-in pacing delays (`time.sleep(2)`) between sequential LLM calls to prevent global upstream Rate Limit (429) errors.
* Added strict response validators across all rounds to immediately raise readable `ValueError` exceptions if an LLM returns empty/None responses, preventing silent parsing failures.

---

## 3. Major Architectural Benefits

| Benefit | Before | After |
| :--- | :--- | :--- |
| **Security** | Hardcoded OpenRouter API keys in multiple files. | No API keys in the code. Secured with runtime environment checks. |
| **Decoupling** | Hardcoded to OpenRouter and DeepSeek. | Completely agnostic. Easily routed to LiteLLM, Ollama, OpenAI, or Anthropic. |
| **Scalability** | Fixed at 3 predefined council members. | Dynamically scales to any of the 18 personas via command-line arguments. |
| **Frameworks** | Legacy procedural Agno code only. | Clean Object-Oriented Agno and Stateful LangGraph compilation. |
| **Robustness** | Hit rate limits easily, threw silent NoneType errors. | Paced at 2s, validated at every round with strict ValueError traps. |

---

## 4. Verification & How to Test

Tests are performed utilizing a secure, key-less configuration. Credentials can be passed inline to run verification without editing any local repository files:

### 1. Test Agno Backend (with 1 member)
```bash
COUNCIL_API_KEY="your_api_key" python run_framework.py --framework agno --members socrates "State the word hello once."
```

### 2. Test LangGraph Backend (with 3 members)
```bash
COUNCIL_API_KEY="your_api_key" python run_framework.py --framework langgraph --members socrates,sun-tzu,aurelius "Is scaling a monolith always better?"
```

---

## 5. Next Steps & Recommendation

We recommend **approving and merging these changes** to form the official v1.0.0 release of the Council Framework. It turns the repository from a simple script into a robust Python library, setting a highly professional standard for upcoming integrations.
