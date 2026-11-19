import argparse
import sys
from .server import mcp

def main():
    parser = argparse.ArgumentParser(
        prog="council",
        description="Council of High Intelligence CLI"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    mcp_parser = subparsers.add_parser("mcp", help="Run the Council MCP server")
    
    args = parser.parse_args()
    
    if args.command == "mcp":
        mcp.run()
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
