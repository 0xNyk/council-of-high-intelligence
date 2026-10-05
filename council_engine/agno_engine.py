import os
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from council_engine.core import parse_agent_file, anonymize_responses

def create_agno_member(agent_name, model_name=None):
    parsed = parse_agent_file(agent_name)
    from council_engine.core import get_config
    cfg = get_config()
    
    m_name = model_name or cfg["model"]
    extra_body = {"reasoning": {"enabled": True}} if cfg["reasoning_enabled"] else None
    
    # Configure model using env-driven settings
    model = OpenAIChat(
        id=m_name,
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
        extra_body=extra_body,
        role_map={
            "system": "system",
            "user": "user",
            "assistant": "assistant",
            "tool": "tool",
            "model": "assistant",
        }
    )
    
    return Agent(
        name=parsed["name"],
        role=parsed["domain"],
        model=model,
        instructions=[parsed["instructions"]],
        markdown=True
    )

def run_agno_deliberation(problem, members_list):
    import time
    print("\n" + "=" * 60)
    print(" [ENGINE: AGNO (PHIDATA)] Deliberating...")
    print("=" * 60)

    # 1. Instantiate Agno agents
    agents = {m: create_agno_member(m) for m in members_list}
    
    # 2. Round 1: Parallel/Blind independent analysis
    print("\n[ROUND 1] Collecting Blind Independent Analyses...")
    r1_outputs = {}
    for m, agent in agents.items():
        print(f" > {agent.name} is analyzing the problem...")
        prompt = f"""
Problem: {problem}

Please evaluate this problem independently from your specific domain expertise and philosophical discipline. 
You do not know what other members have said. 
Use a maximum of 300 words.
"""
        response = agent.run(prompt)
        if not response or not response.content:
            raise ValueError(f"[ERROR] Agent '{agent.name}' returned empty or None response in Round 1. Check your OpenRouter credentials, quota, or upstream rate limits.")
        r1_outputs[m] = response.content
        time.sleep(2)  # Pacing delay to avoid rate limit spikes

    # 3. Round 2: Anonymized Cross-Examination
    print("\n[ROUND 2] Anonymized Cross-Examination Started...")
    anonymized_r1, labels = anonymize_responses(r1_outputs, members_list)

    r2_outputs = {}
    for m, agent in agents.items():
        print(f" > {agent.name} is performing peer review...")
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
        response = agent.run(r2_prompt)
        if not response or not response.content:
            raise ValueError(f"[ERROR] Agent '{agent.name}' returned empty or None response in Round 2. Check your OpenRouter credentials, quota, or upstream rate limits.")
        r2_outputs[m] = response.content
        time.sleep(2)  # Pacing delay

    # 4. Round 3: Final Crystallization
    print("\n[ROUND 3] Final Crystallization of Positions (Identities Revealed)...")
    final_positions = {}
    for m, agent in agents.items():
        print(f" > {agent.name} is writing their final position...")
        transcript = f"--- Round 1: Your Independent Analysis ---\n{r1_outputs[m]}\n\n"
        transcript += f"--- Round 2: Peer Review & Critique ---\n{r2_outputs[m]}\n\n"
        
        r3_prompt = f"""
Deliberations are complete. Here is your full history in this session:
{transcript}

Identities are now revealed. Please state your final stance on this decision in 75 words or less, clearly and decisively.
"""
        response = agent.run(r3_prompt)
        if not response or not response.content:
            raise ValueError(f"[ERROR] Agent '{agent.name}' returned empty or None response in Round 3. Check your OpenRouter credentials, quota, or upstream rate limits.")
        final_positions[m] = response.content
        time.sleep(2)  # Pacing delay

    # 5. Synthesis: Chairman Verdict
    print("\n[SYNTHESIS] Chairman is Synthesizing the Verdict...")
    
    # Build complete named transcript for the Chairman
    full_transcript = "--- Full Deliberation Transcript ---\n\n"
    for m in members_list:
        full_transcript += f"=== Member: {agents[m].name} ===\n"
        full_transcript += f"[Round 1 - Independent]:\n{r1_outputs[m]}\n\n"
        full_transcript += f"[Round 2 - Cross-Examination]:\n{r2_outputs[m]}\n\n"
        full_transcript += f"[Round 3 - Final Position]:\n{final_positions[m]}\n\n"
        full_transcript += "=" * 40 + "\n\n"

    # Instantiate the Chairman (Objective high-tier model, using env-driven settings)
    from council_engine.core import get_config
    cfg = get_config()
    extra_body = {"reasoning": {"enabled": True}} if cfg["reasoning_enabled"] else None
    
    chairman = Agent(
        name="Objective Chairman",
        role="Verdict Synthesizer",
        model=OpenAIChat(
            id=cfg["model"],
            base_url=cfg["base_url"],
            api_key=cfg["api_key"],
            extra_body=extra_body,
            role_map={
                "system": "system",
                "user": "user",
                "assistant": "assistant",
                "tool": "tool",
                "model": "assistant",
            }
        ),
        instructions=["You are the completely objective Chairman of the Council. You did not participate in the deliberation. Your task is to weigh arguments, identify genuine splits, and synthesize a rigorous operational verdict."],
        markdown=True
    )
    
    synthesis_prompt = f"""
Original Problem: "{problem}"

Weigh the following transcript objectively:
{full_transcript}

Please synthesize the final 'Council of High Intelligence Verdict' report in English. The report must contain:
1. **Consensus:** The survived decision and shared alignments.
2. **Key Disagreements:** Point of core friction or divergence between members.
3. **Acceptable Compromises:** What this decision gives up or sacrifices (tradeoffs).
4. **Concrete Next Step:** Exactly one owner-assigned, artifact-producing action to be executed within 15 days.
5. **Kill Criteria:** Measurable thresholds or events that would invalidate this verdict.
"""
    
    verdict_response = chairman.run(synthesis_prompt)
    if not verdict_response or not verdict_response.content:
        raise ValueError(f"[ERROR] Chairman returned empty or None verdict. Check your OpenRouter credentials, quota, or upstream rate limits.")
    
    print("\n" + "=" * 60)
    print(" FINAL COUNCIL OF HIGH INTELLIGENCE VERDICT (AGNO) ")
    print("=" * 60)
    print(verdict_response.content)
    print("=" * 60)
