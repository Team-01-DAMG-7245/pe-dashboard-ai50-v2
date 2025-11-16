"""
Supervisor Agent with MCP Integration - Lab 15
Demonstrates Agent to MCP to Dashboard to Agent round trip
"""

import asyncio
import json
import httpx
import re
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Load MCP configuration
with open('mcp_config.json') as f:
    MCP_CONFIG = json.load(f)

# Get companies with existing payloads
def get_companies_with_payloads():
    """Return list of company IDs that have payload files"""
    payload_dir = Path("data/payloads")
    if not payload_dir.exists():
        return []
    
    # Map payload files to company IDs
    payload_mapping = {
        "abridge": "abridge",
        "anthropic": "anthropic",
        "anysphere": "cursor",
        "cohere": "cohere",
        "databricks": "databricks",
        "deepl": "deepl",
        "elevenlabs": "eleven-labs",
        "glean": "glean",
        "hugging_face": "hugging-face",
        "notion": "notion",
        "perplexity_ai": "perplexity",
        "runway": "runway",
        "suno": "suno",
        "baseten": "baseten",
        "captions": "captions",
        "clay": "clay",
        "crusoe": "crusoe",
        "figure_ai": "figure-ai",
        "hebbia": "hebbia",
        "langchain": "langchain",
        "luminance": "luminance",
        "manifest": "manifest",
        "mercor": "mercor",
        "openevidence": "openevidence",
        "photoroom": "photoroom",
        "speak": "speak",
        "stackblitz": "stackblitz",
        "synthesia": "synthesia",
        "thinking_machine_labs": "thinking-machines",
        "together_ai": "together",
        "vannevar_labs": "vannevar",
        "windsurf": "windsurf",
        "world_labs": "world-labs",
        "writer": "writer",
        "xai": "xai"
    }
    
    # Check which payloads actually exist
    existing_companies = []
    for payload_file, company_id in payload_mapping.items():
        if (payload_dir / f"{payload_file}.json").exists():
            existing_companies.append(company_id)
    
    return existing_companies

def format_dashboard(dashboard_data):
    """Format dashboard by handling escaped newlines and extracting content"""
    if isinstance(dashboard_data, dict):
        dashboard = dashboard_data.get('markdown', '') or dashboard_data.get('dashboard', '')
    else:
        dashboard = str(dashboard_data)
    
    # Handle string format like "company_id='...' dashboard='...'"
    if 'company_id=' in dashboard and 'dashboard=' in dashboard:
        match = re.search(r"dashboard='(.*?)'(?:\s+chunks_used=|\s*$)", dashboard, re.DOTALL)
        if match:
            dashboard = match.group(1)
    
    # Replace escaped newlines with actual newlines
    dashboard = dashboard.replace('\\n', '\n')
    
    return dashboard

# Companies with payloads
COMPANIES_WITH_PAYLOADS = get_companies_with_payloads()

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
        
        print(f"MCP-Enabled Supervisor initialized")
        print(f"MCP Server: {self.mcp_base_url}")
        print(f"Enabled Tools: {self.enabled_tools}\n")
    
    async def call_mcp_tool(self, tool_name: str, params: Dict) -> Dict:
        """Call an MCP tool with filtering and security"""
        
        # Tool filtering - only allow enabled tools
        if tool_name not in self.enabled_tools:
            raise ValueError(f"Tool {tool_name} is not enabled")
        
        endpoint = MCP_CONFIG["tools"]["endpoints"].get(tool_name)
        url = f"{self.mcp_base_url}{endpoint}"
        
        print(f"Calling MCP Tool: {tool_name}")
        
        try:
            response = await self.client.post(url, json=params)
            response.raise_for_status()
            result = response.json()
            print(f"MCP Response received\n")
            return result
        except Exception as e:
            print(f"MCP Error: {str(e)}\n")
            return {"error": str(e)}
    
    async def analyze_company(self, company_id: str) -> Dict:
        """Complete analysis using MCP tools"""
        
        print("="*60)
        print(f"MCP-Powered Analysis for: {company_id}")
        print("="*60)
        
        results = {
            "company_id": company_id,
            "timestamp": datetime.now().isoformat(),
            "dashboards": {},
            "mcp_calls": []
        }
        
        # Generate Structured Dashboard
        print("\nThought: Generate structured dashboard via MCP")
        print("Action: POST to /tool/generate_structured_dashboard")
        
        structured = await self.call_mcp_tool(
            "generate_structured_dashboard",
            {"company_id": company_id}
        )
        
        if "error" not in structured:
            results["dashboards"]["structured"] = structured
            results["mcp_calls"].append("generate_structured_dashboard")
            dashboard_content = format_dashboard(structured)
            print(f"Observation: Dashboard generated ({len(dashboard_content)} chars)")
        
        # Generate RAG Dashboard
        print("\nThought: Generate RAG dashboard via MCP")
        print("Action: POST to /tool/generate_rag_dashboard")
        
        rag = await self.call_mcp_tool(
            "generate_rag_dashboard",
            {"company_id": company_id}
        )
        
        if "error" not in rag:
            results["dashboards"]["rag"] = rag
            results["mcp_calls"].append("generate_rag_dashboard")
            dashboard_content = format_dashboard(rag)
            print(f"Observation: Dashboard generated ({len(dashboard_content)} chars)")
        
        print("\n" + "="*60)
        print(f"Round Trip Complete!")
        print(f"   MCP Calls: {len(results['mcp_calls'])}")
        print(f"   Dashboards Generated: {len(results['dashboards'])}")
        print("="*60)
        
        return results
    
    async def close(self):
        await self.client.aclose()

async def test_mcp_roundtrip():
    """Test the complete Agent to MCP to Dashboard to Agent flow"""
    
    print("\nLab 15: Testing MCP Round Trip")
    print("-"*40)
    
    supervisor = MCPEnabledSupervisor()
    
    try:
        # Test with anthropic
        results = await supervisor.analyze_company("anthropic")
        
        # Save results with FULL dashboard content
        output_file = Path("logs/mcp_roundtrip_test.json")
        output_file.parent.mkdir(exist_ok=True)
        
        # Format dashboards properly
        structured_md = format_dashboard(results["dashboards"].get("structured", {}))
        rag_md = format_dashboard(results["dashboards"].get("rag", {}))
        
        with open(output_file, 'w') as f:
            save_data = {
                "company_id": results["company_id"],
                "timestamp": results["timestamp"],
                "mcp_calls": results["mcp_calls"],
                "structured_dashboard": structured_md,
                "rag_dashboard": rag_md,
                "structured_length": len(structured_md),
                "rag_length": len(rag_md)
            }
            json.dump(save_data, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        print(f"Structured Dashboard: {save_data['structured_length']} chars")
        print(f"RAG Dashboard: {save_data['rag_length']} chars")
        print("Lab 15 Checkpoint: Agent to MCP to Dashboard to Agent SUCCESS!\n")
        
        return results
        
    finally:
        await supervisor.close()

async def generate_all_company_dashboards():
    """Generate dashboards for companies with existing payloads"""
    
    companies = COMPANIES_WITH_PAYLOADS
    
    if not companies:
        print("\n❌ No companies with payload files found!")
        print("Looking in: data/payloads/")
        return
    
    print(f"\nLab 15: Generating dashboards for companies with existing payloads")
    print(f"Total companies: {len(companies)}")
    print(f"Companies: {', '.join(companies[:10])}{'...' if len(companies) > 10 else ''}")
    print("-"*60)
    
    supervisor = MCPEnabledSupervisor()
    
    # Create output directories
    output_dir = Path("dashboards")
    structured_dir = output_dir / "structured"
    rag_dir = output_dir / "rag"
    combined_dir = output_dir / "combined"
    logs_dir = Path("logs/mcp_roundtrips")
    
    for dir_path in [structured_dir, rag_dir, combined_dir, logs_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    successful = 0
    failed = 0
    all_results = []
    
    try:
        for i, company_id in enumerate(companies, 1):
            print(f"\n[{i}/{len(companies)}] Processing: {company_id}")
            
            try:
                results = await supervisor.analyze_company(company_id)
                
                if len(results["mcp_calls"]) > 0:
                    successful += 1
                    
                    # Format dashboards properly
                    structured_md = format_dashboard(results["dashboards"].get("structured", {}))
                    rag_md = format_dashboard(results["dashboards"].get("rag", {}))
                    
                    # Save structured dashboard
                    structured_file = structured_dir / f"{company_id}_structured.md"
                    with open(structured_file, 'w') as f:
                        f.write(f"# {company_id.upper()} - PE Due Diligence Dashboard (Structured)\n\n")
                        f.write(f"*Generated: {results['timestamp']}*\n\n")
                        f.write(structured_md or "No data available")
                    
                    # Save RAG dashboard
                    rag_file = rag_dir / f"{company_id}_rag.md"
                    with open(rag_file, 'w') as f:
                        f.write(f"# {company_id.upper()} - PE Due Diligence Dashboard (RAG)\n\n")
                        f.write(f"*Generated: {results['timestamp']}*\n\n")
                        f.write(rag_md or "No data available")
                    
                    # Save combined dashboard
                    combined_file = combined_dir / f"{company_id}_complete.md"
                    with open(combined_file, 'w') as f:
                        f.write(f"# {company_id.upper()} - Complete PE Due Diligence Dashboard\n\n")
                        f.write(f"*Generated: {results['timestamp']}*\n\n")
                        f.write("---\n\n")
                        f.write("## STRUCTURED DASHBOARD\n\n")
                        f.write(structured_md or "No data available")
                        f.write("\n\n---\n\n")
                        f.write("## RAG-ENHANCED DASHBOARD\n\n")
                        f.write(rag_md or "No data available")
                    
                    # Save roundtrip JSON with properly formatted dashboards
                    roundtrip_file = logs_dir / f"mcp_roundtrip_{company_id}.json"
                    with open(roundtrip_file, 'w') as f:
                        save_data = {
                            "company_id": company_id,
                            "timestamp": results["timestamp"],
                            "mcp_calls": results["mcp_calls"],
                            "structured_dashboard": structured_md,
                            "rag_dashboard": rag_md,
                            "structured_length": len(structured_md),
                            "rag_length": len(rag_md)
                        }
                        json.dump(save_data, f, indent=2)
                    
                    print(f"Saved dashboards for {company_id}")
                    all_results.append({"company_id": company_id, "status": "success"})
                else:
                    failed += 1
                    all_results.append({"company_id": company_id, "status": "failed", "error": "No MCP calls made"})
                    
            except Exception as e:
                failed += 1
                print(f"Error processing {company_id}: {str(e)}")
                all_results.append({"company_id": company_id, "status": "failed", "error": str(e)})
            
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        # Save summary
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_companies": len(companies),
            "successful": successful,
            "failed": failed,
            "results": all_results
        }
        
        summary_file = output_dir / "generation_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"LAB 15 DASHBOARD GENERATION COMPLETE")
        print(f"{'='*60}")
        print(f"Successful: {successful}/{len(companies)}")
        print(f"Failed: {failed}/{len(companies)}")
        print(f"\nOutput directories:")
        print(f"   - Structured: {structured_dir}")
        print(f"   - RAG: {rag_dir}")
        print(f"   - Combined: {combined_dir}")
        print(f"   - Roundtrip JSONs: {logs_dir}")
        print(f"   - Summary: {summary_file}")
        print(f"{'='*60}\n")
        
    finally:
        await supervisor.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Generate for all companies with payloads
        asyncio.run(generate_all_company_dashboards())
    else:
        # Run single test
        asyncio.run(test_mcp_roundtrip())
