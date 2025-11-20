"""
Test script for LangChain ReAct logging integration.
Demonstrates how the callback handler captures agent steps.
"""

import asyncio
import json
from pathlib import Path
from src.agents.supervisor_agent_langchain import run_supervisor_agent_langchain


async def test_langchain_react_logging():
    """Test LangChain agent with ReAct logging"""
    
    print("=" * 60)
    print("Testing LangChain ReAct Logging Integration")
    print("=" * 60)
    
    # Test with a company
    company_id = "anthropic"
    run_id = "test-langchain-001"
    
    print(f"\nRunning analysis for: {company_id}")
    print(f"Run ID: {run_id}\n")
    
    try:
        # Run the agent
        results = await run_supervisor_agent_langchain(
            company_id=company_id,
            enable_logging=True,
            run_id=run_id
        )
        
        # Verify results
        print("\n" + "=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        
        assert "trace_file" in results, "Trace file not in results"
        assert "run_id" in results, "Run ID not in results"
        assert results["run_id"] == run_id, "Run ID mismatch"
        
        trace_file = Path(results["trace_file"])
        assert trace_file.exists(), f"Trace file does not exist: {trace_file}"
        
        print(f"[OK] Trace file exists: {trace_file}")
        
        # Load and verify trace
        with open(trace_file, 'r') as f:
            trace = json.load(f)
        
        print(f"[OK] Trace loaded successfully")
        print(f"\n   Run ID: {trace['run_id']}")
        print(f"   Company: {trace['company_id']}")
        print(f"   Total Steps: {len(trace['steps'])}")
        
        # Count step types
        thoughts = sum(1 for s in trace['steps'] if s['step_type'] == 'thought')
        actions = sum(1 for s in trace['steps'] if s['step_type'] == 'action')
        observations = sum(1 for s in trace['steps'] if s['step_type'] == 'observation')
        
        print(f"   Thoughts: {thoughts}")
        print(f"   Actions: {actions}")
        print(f"   Observations: {observations}")
        
        # Verify required fields
        required_fields = ['timestamp', 'run_id', 'company_id', 'step_number', 'step_type']
        for step in trace['steps']:
            for field in required_fields:
                assert field in step, f"Missing field '{field}' in step {step.get('step_number')}"
        
        print(f"\n   [OK] All required fields present")
        
        # Show sample steps
        print(f"\n   Sample Steps:")
        for i, step in enumerate(trace['steps'][:3]):
            print(f"   Step {step['step_number']} ({step['step_type']}):")
            if step.get('thought'):
                print(f"      Thought: {step['thought'][:80]}...")
            if step.get('action'):
                print(f"      Action: {step['action']}")
            if step.get('observation'):
                print(f"      Observation: {step['observation'][:80]}...")
        
        print("\n" + "=" * 60)
        print("[OK] LangChain ReAct Logging Test: PASSED")
        print("=" * 60)
        
        return results
        
    except ImportError as e:
        print(f"\n[ERROR] Import Error: {e}")
        print("\nPlease install LangChain:")
        print("  pip install langchain langchain-openai langchain-core")
        return None
    
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(test_langchain_react_logging())

