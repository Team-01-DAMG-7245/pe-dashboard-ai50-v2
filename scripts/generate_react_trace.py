"""
Script to generate a real ReAct trace for Lab 16 documentation.
Runs the supervisor agent and captures a complete trace for documentation purposes.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.supervisor_agent_langchain import run_supervisor_agent_langchain
from dotenv import load_dotenv

load_dotenv()


async def generate_react_trace(company_id: str = "anthropic", run_id: str = None):
    """
    Generate a ReAct trace for documentation.
    
    Args:
        company_id: Company to analyze
        run_id: Optional custom run ID (auto-generated if None)
    """
    print("=" * 70)
    print("Generating ReAct Trace for Lab 16 Documentation")
    print("=" * 70)
    print(f"\nCompany: {company_id}")
    print(f"Run ID: {run_id or 'Auto-generated'}")
    print("\nRunning agent analysis...\n")
    
    # Run the agent with logging enabled
    results = await run_supervisor_agent_langchain(
        company_id=company_id,
        enable_logging=True,
        run_id=run_id
    )
    
    # Load the trace file
    trace_file = Path(results['trace_file'])
    with open(trace_file, 'r') as f:
        trace = json.load(f)
    
    print("\n" + "=" * 70)
    print("Trace Generated Successfully!")
    print("=" * 70)
    print(f"\nTrace File: {trace_file}")
    print(f"Run ID: {results['run_id']}")
    print(f"Total Steps: {len(trace['steps'])}")
    print(f"Duration: {trace['completed_at']} - {trace['started_at']}")
    
    # Count step types
    thoughts = sum(1 for s in trace['steps'] if s['step_type'] == 'thought')
    actions = sum(1 for s in trace['steps'] if s['step_type'] == 'action')
    observations = sum(1 for s in trace['steps'] if s['step_type'] == 'observation')
    
    print(f"\nStep Breakdown:")
    print(f"  Thoughts: {thoughts}")
    print(f"  Actions: {actions}")
    print(f"  Observations: {observations}")
    
    return results, trace


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate ReAct trace for documentation")
    parser.add_argument(
        "--company",
        type=str,
        default="anthropic",
        help="Company ID to analyze (default: anthropic)"
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Custom run ID (default: auto-generated)"
    )
    
    args = parser.parse_args()
    
    try:
        results, trace = asyncio.run(generate_react_trace(
            company_id=args.company,
            run_id=args.run_id
        ))
        
        print("\n" + "=" * 70)
        print("[OK] Trace generation complete!")
        print("=" * 70)
        print(f"\nNext steps:")
        print(f"1. Review trace file: {results['trace_file']}")
        print(f"2. Use this trace to create docs/REACT_TRACE_EXAMPLE.md")
        print(f"3. Run ID for documentation: {results['run_id']}")
        
    except Exception as e:
        print(f"\n[ERROR] Error generating trace: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

