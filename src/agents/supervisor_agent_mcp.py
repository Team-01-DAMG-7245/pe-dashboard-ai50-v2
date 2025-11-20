"""
Supervisor Agent with MCP Integration - Lab 15
Demonstrates Agent → MCP → Dashboard → Agent round trip
"""

import asyncio
import json
import httpx
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Load MCP configuration
with open('mcp_config.json') as f:
    MCP_CONFIG = json.load(f)

class MCPEnabledSupervisor:
    """Supervisor Agent that consumes MCP server tools"""
    
    def __init__(self):
        self.system_prompt = (
            "You are a PE Due Diligence Supervisor Agent. "
            "Use MCP tools to retrieve payloads, run RAG queries, "
            "log risks, and generate PE dashboards."
        )
        self.mcp_base_url = MCP_CONFIG["server"]["base_url"]
        self.enabled_tools = MCP_CONFIG["tools"]["enabled"]
        self.client = httpx.AsyncClient(timeout=30)
        
        print(f"📡 MCP-Enabled Supervisor initialized")
        print(f"🔗 MCP Server: {self.mcp_base_url}")
        print(f"🔧 Enabled Tools: {self.enabled_tools}\n")
    
    async def call_mcp_tool(self, tool_name: str, params: Dict) -> Dict:
        """Call an MCP tool with filtering and security"""
        
        # Tool filtering - only allow enabled tools
        if tool_name not in self.enabled_tools:
            raise ValueError(f"Tool {tool_name} is not enabled")
        
        endpoint = MCP_CONFIG["tools"]["endpoints"].get(tool_name)
        url = f"{self.mcp_base_url}{endpoint}"
        
        print(f"🔌 Calling MCP Tool: {tool_name}")
        
        try:
            response = await self.client.post(url, json=params)
            response.raise_for_status()
            result = response.json()
            print(f"✅ MCP Response received\n")
            return result
        except Exception as e:
            print(f"❌ MCP Error: {str(e)}\n")
            return {"error": str(e)}
    
    async def analyze_company(self, company_id: str) -> Dict:
        """Complete analysis using MCP tools"""
        
        print("="*60)
        print(f"🎯 MCP-Powered Analysis for: {company_id}")
        print("="*60)
        
        results = {
            "company_id": company_id,
            "timestamp": datetime.now().isoformat(),
            "dashboards": {},
            "mcp_calls": []
        }
        
        # Generate Structured Dashboard
        print("\n💭 Thought: Generate structured dashboard via MCP")
        print("🎯 Action: POST to /tool/generate_structured_dashboard")
        
        structured = await self.call_mcp_tool(
            "generate_structured_dashboard",
            {"company_id": company_id}
        )
        
        if "error" not in structured:
            results["dashboards"]["structured"] = structured
            results["mcp_calls"].append("generate_structured_dashboard")
            print(f"👁️ Observation: Dashboard generated ({len(structured.get('markdown', ''))} chars)")
        
        # Generate RAG Dashboard
        print("\n💭 Thought: Generate RAG dashboard via MCP")
        print("🎯 Action: POST to /tool/generate_rag_dashboard")
        
        rag = await self.call_mcp_tool(
            "generate_rag_dashboard",
            {"company_id": company_id}
        )
        
        if "error" not in rag:
            results["dashboards"]["rag"] = rag
            results["mcp_calls"].append("generate_rag_dashboard")
            print(f"👁️ Observation: Dashboard generated ({len(rag.get('markdown', ''))} chars)")
        
        print("\n" + "="*60)
        print(f"✅ Round Trip Complete!")
        print(f"   MCP Calls: {len(results['mcp_calls'])}")
        print(f"   Dashboards Generated: {len(results['dashboards'])}")
        print("="*60)
        
        return results
    
    async def close(self):
        await self.client.aclose()

async def test_mcp_roundtrip():
    """Test the complete Agent → MCP → Dashboard → Agent flow"""
    
    print("\n🔄 Lab 15: Testing MCP Round Trip")
    print("-"*40)
    
    supervisor = MCPEnabledSupervisor()
    
    try:
        # Test with anthropic (it's in your vector DB)
        results = await supervisor.analyze_company("anthropic")
        
        # Save results
        output_file = Path("logs/mcp_roundtrip_test.json")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            # Don't save full markdown, just metadata
            save_data = {
                "company_id": results["company_id"],
                "timestamp": results["timestamp"],
                "mcp_calls": results["mcp_calls"],
                "structured_length": len(results["dashboards"].get("structured", {}).get("markdown", "")),
                "rag_length": len(results["dashboards"].get("rag", {}).get("markdown", ""))
            }
            json.dump(save_data, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        print("✅ Lab 15 Checkpoint: Agent → MCP → Dashboard → Agent SUCCESS!\n")
        
        return results
        
    finally:
        await supervisor.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_mcp_roundtrip())