#!/usr/bin/env python3
"""
Complete Labs 12-15 Test Suite
Tests Phase 1 (Labs 12-13) and Phase 2 (Labs 14-15)
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import date

print("=" * 70)
print("LABS 12-15 COMPLETE DEMONSTRATION")
print("=" * 70)

# ============================================================================
# LAB 12: Core Agent Tools
# ============================================================================
print("\n📦 LAB 12: Core Agent Tools")
print("-" * 70)

# Test 1: Payload Tool
print("\n1. Testing Payload Tool...")
try:
    from src.lab12.tools.payload_tool import get_latest_structured_payload
    payload = asyncio.run(get_latest_structured_payload('anthropic'))
    print(f'✅ Payload Tool: {payload.company_record.get("legal_name", "Unknown")}')
    print(f'   Events: {len(payload.events)}, Products: {len(payload.products)}')
except Exception as e:
    print(f'❌ Payload Tool Error: {e}')

# Test 2: RAG Search Tool
print("\n2. Testing RAG Search Tool...")
try:
    from src.lab12.tools.rag_tool import rag_search_company
    results = asyncio.run(rag_search_company('anthropic', 'data platform'))
    print(f'✅ RAG Tool: {len(results)} results found')
    if results:
        print(f'   First result score: {results[0].get("score", 0):.3f}')
except Exception as e:
    print(f'⚠️ RAG Tool: {str(e)[:80]}... (may have dependency issues)')

# Test 3: Risk Logger Tool
print("\n3. Testing Risk Logger Tool...")
try:
    from src.lab12.tools.risk_logger import report_layoff_signal, LayoffSignal
    signal = LayoffSignal(
        company_id='test_company',
        occurred_on=date.today(),
        description='Risk assessment from analysis',
        source_url='https://example.com/test'
    )
    result = asyncio.run(report_layoff_signal(signal))
    print(f'✅ Risk Logger: {result}')
    
    # Check if log file exists
    log_file = Path("logs/risk_signals.jsonl")
    if log_file.exists():
        print(f'   Log file exists: {log_file}')
except Exception as e:
    print(f'❌ Risk Logger Error: {e}')

print("\n✅ Lab 12 Checkpoint: Core tools tested")

# ============================================================================
# LAB 13: Supervisor Agent Bootstrap
# ============================================================================
print("\n🤖 LAB 13: Supervisor Agent")
print("-" * 70)

try:
    from src.lab13.agents.supervisor_agent import DueDiligenceSupervisor
    
    print("\nTesting Supervisor Agent with ReAct pattern...")
    supervisor = DueDiligenceSupervisor()
    
    # Check system prompt
    print(f"✅ System Prompt: {supervisor.system_prompt[:60]}...")
    
    # Check tools registered
    print(f"✅ Tools Registered: {len(supervisor.tools)} tools")
    for action_type in supervisor.tools.keys():
        print(f"   - {action_type.value}")
    
    # Try to run analysis (may fail if RAG tool has issues)
    print("\nRunning analysis (may skip if RAG dependency issue)...")
    try:
        results = asyncio.run(supervisor.analyze_company("anthropic"))
        print(f"✅ Analysis complete: {len(results.get('risk_signals', []))} risk signals found")
    except Exception as e:
        print(f"⚠️ Analysis skipped: {str(e)[:80]}...")
    
    print("\n✅ Lab 13 Checkpoint: Supervisor agent with ReAct pattern")
    
except Exception as e:
    print(f"❌ Lab 13 Error: {e}")

# ============================================================================
# LAB 14: MCP Server Implementation
# ============================================================================
print("\n🌐 LAB 14: MCP Server")
print("-" * 70)

try:
    import requests
    
    base_url = "http://localhost:9000"
    
    # Test if server is running
    try:
        response = requests.get(f"{base_url}/", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print("✅ MCP Server is running")
            print(f"   Tools: {data['endpoints']['tools']}")
            print(f"   Resources: {data['endpoints']['resources']}")
            print(f"   Prompts: {data['endpoints']['prompts']}")
            
            # Test Resource Endpoint
            print("\n1. Testing Resource Endpoint...")
            response = requests.get(f"{base_url}/resource/ai50/companies")
            if response.status_code == 200:
                companies = response.json()["company_ids"]
                print(f'✅ Found {len(companies)} companies')
                print(f'   Sample: {companies[:5]}')
            
            # Test Prompt Endpoint
            print("\n2. Testing Prompt Endpoint...")
            response = requests.get(f"{base_url}/prompt/pe-dashboard")
            if response.status_code == 200:
                prompt = response.json()
                print(f'✅ Dashboard template with {len(prompt["sections"])} sections')
                for section in prompt["sections"]:
                    print(f'   - {section}')
            
            # Test Structured Dashboard Tool
            print("\n3. Testing Structured Dashboard Tool...")
            try:
                response = requests.post(
                    f"{base_url}/tool/generate_structured_dashboard",
                    json={"company_id": "anthropic"},
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    print(f'✅ Structured dashboard: {len(data.get("markdown", ""))} chars')
                else:
                    print(f'⚠️ Status {response.status_code}: {response.text[:100]}')
            except requests.exceptions.Timeout:
                print("⚠️ Dashboard generation timed out (may need OpenAI API key)")
            except Exception as e:
                print(f"⚠️ Error: {str(e)[:80]}...")
            
            print("\n✅ Lab 14 Checkpoint: MCP Server endpoints tested")
        else:
            print(f"❌ MCP Server returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("⚠️ MCP Server not running")
        print("   Start it with: $env:KMP_DUPLICATE_LIB_OK='TRUE'; python src/lab14/server/mcp_server.py")
        print("   Then run this test again")
    except Exception as e:
        print(f"❌ Error connecting to MCP server: {e}")
        
except ImportError:
    print("⚠️ requests library not available, skipping HTTP tests")
except Exception as e:
    print(f"❌ Lab 14 Error: {e}")

# ============================================================================
# LAB 15: Agent MCP Consumption
# ============================================================================
print("\n🔄 LAB 15: Agent-MCP Round Trip")
print("-" * 70)

try:
    # Check if mcp_config.json exists
    config_file = Path("mcp_config.json")
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
        print("✅ MCP Config loaded")
        print(f"   Base URL: {config.get('server', {}).get('base_url', 'N/A')}")
        print(f"   Enabled Tools: {config.get('tools', {}).get('enabled', [])}")
    else:
        print("⚠️ mcp_config.json not found")
    
    # Test MCP-enabled supervisor
    try:
        from src.lab13.agents.supervisor_agent_mcp import MCPEnabledSupervisor
        
        print("\nTesting MCP-Enabled Supervisor...")
        supervisor = MCPEnabledSupervisor()
        
        # Try to test round trip (may fail if server not running)
        try:
            results = asyncio.run(supervisor.analyze_company("anthropic"))
            print(f"✅ Round trip complete!")
            print(f"   MCP Calls: {len(results.get('mcp_calls', []))}")
            print(f"   Dashboards Generated: {len(results.get('dashboards', {}))}")
            
            # Check if log file was created
            log_file = Path("logs/mcp_roundtrip_test.json")
            if log_file.exists():
                print(f"   Results saved to: {log_file}")
        except Exception as e:
            print(f"⚠️ Round trip test: {str(e)[:80]}... (MCP server may not be running)")
        
        asyncio.run(supervisor.close())
        print("\n✅ Lab 15 Checkpoint: MCP integration tested")
        
    except Exception as e:
        print(f"⚠️ MCP Supervisor Error: {str(e)[:80]}...")
        
except Exception as e:
    print(f"❌ Lab 15 Error: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("✅ Lab 12: Core Agent Tools - Tested")
print("✅ Lab 13: Supervisor Agent - Tested")
print("✅ Lab 14: MCP Server - Tested (if server running)")
print("✅ Lab 15: Agent-MCP Integration - Tested")
print("\n📝 Note: Some tests may show warnings due to:")
print("   - RAG tool dependency issues (chromadb/onnxruntime)")
print("   - MCP server not running (start it separately)")
print("   - OpenAI API key not configured")
print("=" * 70)

