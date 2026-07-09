import os
import re
import yaml

def load_dotenv():
    """Manually load .env file into os.environ if it exists."""
    for dotenv_path in [".env", "../.env"]:
        if os.path.exists(dotenv_path):
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = val

# Run dotenv loading immediately upon package import
load_dotenv()

def get_config():
    """Returns the unified config values from environment variables with sensible defaults."""
    api_key = os.getenv("COUNCIL_API_KEY")
    if not api_key or api_key.strip() in ("", "your_api_key_here"):
        raise ValueError("[ERROR] No API key found. Please set COUNCIL_API_KEY in your environment or .env file.")
        
    base_url = os.getenv("COUNCIL_BASE_URL")
    model = os.getenv("COUNCIL_MODEL")
    reasoning_enabled = (os.getenv("COUNCIL_REASONING") or "true").lower() == "true"
    
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "reasoning_enabled": reasoning_enabled
    }

def parse_agent_file(agent_name):
    """
    Parses the council agent markdown file and extracts its name, domain,
    identity, grounding protocol, and analytical method.
    """
    # Look up in standard paths
    paths = [
        f"agents/council-{agent_name}.md",
        f"~/.claude/agents/council-{agent_name}.md",
        f"~/.codex/skills/council/agents/council-{agent_name}.md"
    ]
    
    path = None
    for p in paths:
        expanded = os.path.expanduser(p)
        if os.path.exists(expanded):
            path = expanded
            break
            
    if not path:
        return {
            "name": agent_name.capitalize(),
            "domain": "General Strategy",
            "instructions": f"You are a wise strategist named {agent_name.capitalize()}."
        }
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Extract YAML frontmatter
    frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    metadata = {}
    if frontmatter_match:
        try:
            metadata = yaml.safe_load(frontmatter_match.group(1))
        except Exception:
            pass
            
    council_meta = metadata.get("council", {})
    figure = council_meta.get("figure", agent_name.capitalize())
    domain = council_meta.get("domain", "General Deliberation")
    
    # Extract markdown sections for Identity, Grounding Protocol and Method
    identity = re.search(r"## Identity\n(.*?)(?=\n##|$)", content, re.DOTALL)
    grounding = re.search(r"## Grounding Protocol.*?\n(.*?)(?=\n##|$)", content, re.DOTALL)
    method = re.search(r"## Analytical Method\n(.*?)(?=\n##|$)", content, re.DOTALL)
    
    identity_text = identity.group(1).strip() if identity else ""
    grounding_text = grounding.group(1).strip() if grounding else ""
    method_text = method.group(1).strip() if method else ""
    
    instructions = f"""
You are operating as {figure} in a structured council deliberation.
Your domain expertise is: {domain}

### YOUR PERSONA IDENTITY
{identity_text}

### YOUR GROUNDING PROTOCOL (FOLLOW STRICTLY)
{grounding_text}

### YOUR ANALYTICAL METHOD
{method_text}
"""
    return {
        "name": figure,
        "domain": domain,
        "instructions": instructions.strip()
    }

def anonymize_responses(r1_outputs, members_list):
    """
    Masks the real names of the figures in the first round outputs to prevent
    conformity bias during Round 2.
    """
    labels = {m: f"Member {chr(65 + i)}" for i, m in enumerate(members_list)}
    anonymized_r1 = ""
    for m, output in r1_outputs.items():
        if not output:
            raise ValueError(f"Round 1 output for agent '{m.capitalize()}' is empty or None. This indicates that the LLM API call failed, possibly due to invalid OpenRouter credentials, insufficient credits, or rate limits.")
        masked_output = output
        # Replace real figures' names in the output with their anonymized labels
        for real_name, label in labels.items():
            masked_output = masked_output.replace(real_name.capitalize(), label)
        anonymized_r1 += f"### {labels[m]} Analysis:\n{masked_output}\n\n"
    return anonymized_r1, labels
