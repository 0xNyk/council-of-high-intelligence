import os
from typing import Dict, List, TypedDict
from langgraph.graph import StateGraph, END
from openai import OpenAI
from council_engine.core import parse_agent_file, anonymize_responses

# Define State Graph schema
class CouncilState(TypedDict):
    problem: str
    members: List[str]
    r1_outputs: Dict[str, str]
    r2_outputs: Dict[str, str]
    r3_outputs: Dict[str, str]
    anonymized_r1: str
    labels: Dict[str, str]
    verdict: str

def call_model(model_name, system_prompt, user_prompt):
    """Utility to make a reasoning-enabled call to the LLM."""
    from council_engine.core import get_config
    cfg = get_config()
    
    # Initialize client dynamically with base_url and api_key
    client = OpenAI(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"]
    )
    
    # Override default deepseek model with env configuration if applicable
    actual_model = model_name
    if model_name == "deepseek/deepseek-v4-flash":
        actual_model = cfg["model"]
        
    extra_body = {"reasoning": {"enabled": True}} if cfg["reasoning_enabled"] else None
    
    response = client.chat.completions.create(
        model=actual_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        extra_body=extra_body
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError(f"[ERROR] LLM returned empty response for model '{actual_model}'. Please verify your billing balance, API key, or rate limits.")
    return content

# 1. Round 1 Node: Parallel blind analysis
def round1_node(state: CouncilState) -> Dict:
    import time
    print("\n[ROUND 1] Collecting Blind Independent Analyses (LangGraph Node)...")
    r1_outputs = {}
    for m in state["members"]:
        print(f" > {m.capitalize()} is analyzing the problem...")
        parsed = parse_agent_file(m)
        prompt = f"""
Problem: {state['problem']}

Please evaluate this problem independently from your specific domain expertise and philosophical discipline. 
You do not know what other members have said. 
Use a maximum of 300 words.
"""
        r1_outputs[m] = call_model("deepseek/deepseek-v4-flash", parsed["instructions"], prompt)
        time.sleep(2)  # Pacing delay
    return {"r1_outputs": r1_outputs}

# 2. Round 2 Node: Anonymized peer critique
def round2_node(state: CouncilState) -> Dict:
    import time
    print("\n[ROUND 2] Anonymized Cross-Examination Started (LangGraph Node)...")
    anonymized_r1, labels = anonymize_responses(state["r1_outputs"], state["members"])
    
    r2_outputs = {}
    for m in state["members"]:
        print(f" > {m.capitalize()} is performing peer review...")
        parsed = parse_agent_file(m)
        r2_prompt = f"""
Identities are completely masked in this round. The Round 1 analyses from all other members are below:
{anonymized_r1}

**Anti-conformity directive.** If your Round 1 position was correct, defend it. Do not update merely because peers disagree, because consensus is forming, or because a position is repeated by multiple members. Update only when presented with sound, validity-aligned reasoning that exposes a specific flaw in your earlier argument. Naming that flaw is required when you update; if you cannot name it, you should not update.

Based on these analyses:
1. Challenge the analysis you disagree with the most (refer to them as 'Member X') and expose its logical flaws.
2. Support the analysis that strengthens your position the most (refer to them as 'Member Y').
3. Restate your position in light of this exchange, noting any changes and reasons.
Use a maximum of 200 words.
"""
        r2_outputs[m] = call_model("deepseek/deepseek-v4-flash", parsed["instructions"], r2_prompt)
        time.sleep(2)  # Pacing delay
        
    return {"r2_outputs": r2_outputs, "anonymized_r1": anonymized_r1, "labels": labels}

# 3. Round 3 Node: Final position crystallization
def round3_node(state: CouncilState) -> Dict:
    import time
    print("\n[ROUND 3] Final Crystallization of Positions (LangGraph Node)...")
    final_positions = {}
    for m in state["members"]:
        print(f" > {m.capitalize()} is writing their final position...")
        parsed = parse_agent_file(m)
        transcript = f"--- Round 1: Your Independent Analysis ---\n{state['r1_outputs'][m]}\n\n"
        transcript += f"--- Round 2: Peer Review & Critique ---\n{state['r2_outputs'][m]}\n\n"
        
        r3_prompt = f"""
Deliberations are complete. Here is your full history in this session:
{transcript}

Identities are now revealed. Please state your final stance on this decision in 75 words or less, clearly and decisively.
"""
        final_positions[m] = call_model("deepseek/deepseek-v4-flash", parsed["instructions"], r3_prompt)
        time.sleep(2)  # Pacing delay
        
    return {"r3_outputs": final_positions}

# 4. Synthesis Node: Chairman synthesis
def synthesis_node(state: CouncilState) -> Dict:
    print("\n[SYNTHESIS] Chairman is Synthesizing the Verdict (LangGraph Node)...")
    
    # Build complete named transcript for the Chairman
    full_transcript = "--- Full Deliberation Transcript ---\n\n"
    for m in state["members"]:
        figure_name = parse_agent_file(m)["name"]
        full_transcript += f"=== Member: {figure_name} ===\n"
        full_transcript += f"[Round 1 - Independent]:\n{state['r1_outputs'][m]}\n\n"
        full_transcript += f"[Round 2 - Cross-Examination]:\n{state['r2_outputs'][m]}\n\n"
        full_transcript += f"[Round 3 - Final Position]:\n{state['r3_outputs'][m]}\n\n"
        full_transcript += "=" * 40 + "\n\n"

    chairman_system = "You are the completely objective Chairman of the Council. You did not participate in the deliberation. Your task is to weigh arguments, identify genuine splits, and synthesize a rigorous operational verdict."
    
    synthesis_prompt = f"""
Original Problem: "{state['problem']}"

Weigh the following transcript objectively:
{full_transcript}

Please synthesize the final 'Council of High Intelligence Verdict' report in English. The report must contain:
1. **Consensus:** The survived decision and shared alignments.
2. **Key Disagreements:** Point of core friction or divergence between members.
3. **Acceptable Compromises:** What this decision gives up or sacrifices (tradeoffs).
4. **Concrete Next Step:** Exactly one owner-assigned, artifact-producing action to be executed within 15 days.
5. **Kill Criteria:** Measurable thresholds or events that would invalidate this verdict.
"""
    verdict = call_model("deepseek/deepseek-v4-flash", chairman_system, synthesis_prompt)
    return {"verdict": verdict}

# Compile state graph workflow
def build_council_workflow():
    workflow = StateGraph(CouncilState)
    
    # Add nodes
    workflow.add_node("round1", round1_node)
    workflow.add_node("round2", round2_node)
    workflow.add_node("round3", round3_node)
    workflow.add_node("synthesis", synthesis_node)
    
    # Set sequential edges
    workflow.set_entry_point("round1")
    workflow.add_edge("round1", "round2")
    workflow.add_edge("round2", "round3")
    workflow.add_edge("round3", "synthesis")
    workflow.add_edge("synthesis", END)
    
    return workflow.compile()

def run_langgraph_deliberation(problem, members_list):
    print("\n" + "=" * 60)
    print(" [ENGINE: LANGGRAPH (STATE CHART)] Deliberating...")
    print("=" * 60)
    
    app = build_council_workflow()
    
    # Initialize state
    initial_state = {
        "problem": problem,
        "members": members_list,
        "r1_outputs": {},
        "r2_outputs": {},
        "r3_outputs": {},
        "anonymized_r1": "",
        "labels": {},
        "verdict": ""
    }
    
    # Run the state graph synchronously
    result = app.invoke(initial_state)
    
    print("\n" + "=" * 60)
    print(" FINAL COUNCIL OF HIGH INTELLIGENCE VERDICT (LANGGRAPH) ")
    print("=" * 60)
    print(result["verdict"])
    print("=" * 60)
