import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Council of High Intelligence - Multi-Backend Agent Framework")
    parser.add_argument(
        "--framework",
        choices=["agno", "langgraph"],
        default="agno",
        help="Select the multi-agent framework backend (default: agno)"
    )
    parser.add_argument(
        "--members",
        default="socrates,sun-tzu,aurelius",
        help="Comma-separated list of council members (e.g. socrates,sun-tzu,aurelius,feynman,ada)"
    )
    parser.add_argument(
        "problem",
        nargs="?",
        default="Should we split our AI-based SaaS product's entire infrastructure into microservices, or stay with a monolithic architecture and focus on database optimization?",
        help="The decision or problem to be analyzed by the council"
    )
    
    args = parser.parse_args()
    
    # Parse dynamic list of members from arguments
    members = [m.strip().lower() for m in args.members.split(",") if m.strip()]
    
    print("=" * 60)
    print("  COUNCIL OF HIGH INTELLIGENCE — PYTHON AGENT FRAMEWORK  ")
    print("=" * 60)
    print(f"Problem: \"{args.problem}\"")
    print(f"Framework Backend: {args.framework.upper()}")
    print(f"Active Panel: {', '.join([m.capitalize() for m in members])}")
    print("-" * 60)

    try:
        if args.framework == "agno":
            from council_engine.agno_engine import run_agno_deliberation
            run_agno_deliberation(args.problem, members)
        elif args.framework == "langgraph":
            from council_engine.langgraph_engine import run_langgraph_deliberation
            run_langgraph_deliberation(args.problem, members)
    except ImportError as e:
        print(f"\n[ERROR] Failed to import the backend dependencies for {args.framework.upper()}:")
        print(e)
        print("\nPlease install the required libraries:")
        if args.framework == "agno":
            print("  pip install agno pyyaml openai")
        elif args.framework == "langgraph":
            print("  pip install langgraph pyyaml openai")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An error occurred during deliberation:")
        print(e)
        sys.exit(1)

if __name__ == "__main__":
    main()
