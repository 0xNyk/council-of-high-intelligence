from council_engine.agno_engine import run_agno_deliberation

if __name__ == "__main__":
    problem_statement = "Should we split our AI-based SaaS product's entire infrastructure into microservices, or stay with a monolithic architecture and focus on database optimization?"
    # Strategy Triad
    konsey = ["socrates", "sun-tzu", "aurelius"]
    
    # Run the cleaned modular Agno engine
    run_agno_deliberation(problem_statement, konsey)
