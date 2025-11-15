"""
Due Diligence Supervisor Agent for Assignment 5.
Implements ReAct (Reasoning and Acting) pattern with the three core tools.
"""

import asyncio
import json
from datetime import date
from typing import Dict, Any, List
from enum import Enum

from src.tools.payload_tool import get_latest_structured_payload
from src.tools.rag_tool import rag_search_company
from src.tools.risk_logger import report_layoff_signal, LayoffSignal

class ActionType(Enum):
    """Available actions for the agent"""
    GET_PAYLOAD = "get_payload"
    SEARCH_RAG = "search_rag"
    LOG_RISK = "log_risk"
    COMPLETE = "complete"

class DueDiligenceSupervisor:
    """
    PE Due Diligence Supervisor Agent that uses tools to retrieve payloads,
    run RAG queries, log risks, and generate PE dashboards.
    """
    
    def __init__(self):
        self.system_prompt = (
            "You are a PE Due Diligence Supervisor Agent. "
            "Use tools to retrieve payloads, run RAG queries, "
            "log risks, and generate PE dashboards."
        )
        self.tools = {
            ActionType.GET_PAYLOAD: get_latest_structured_payload,
            ActionType.SEARCH_RAG: rag_search_company,
            ActionType.LOG_RISK: report_layoff_signal
        }
        self.execution_log = []
        
    def log_react_step(self, step_type: str, content: Any):
        """Log a ReAct step with structured format"""
        log_entry = {
            "step_type": step_type,
            "content": content
        }
        self.execution_log.append(log_entry)
        
        # Print formatted output
        if step_type == "THOUGHT":
            print(f"\n🤔 THOUGHT: {content}")
        elif step_type == "ACTION":
            print(f"🎯 ACTION: {content['action']} with params {content.get('params', {})}")
        elif step_type == "OBSERVATION":
            print(f"👁️ OBSERVATION: {str(content)[:200]}...")
    
    async def execute_action(self, action: ActionType, params: Dict) -> Any:
        """Execute a tool action and return the result"""
        tool = self.tools.get(action)
        if not tool:
            raise ValueError(f"Unknown action: {action}")
        
        # Execute the appropriate tool
        if action == ActionType.GET_PAYLOAD:
            return await tool(params['company_id'])
        elif action == ActionType.SEARCH_RAG:
            return await tool(params['company_id'], params['query'])
        elif action == ActionType.LOG_RISK:
            signal = LayoffSignal(**params)
            return await tool(signal)
        else:
            return None
    
    async def analyze_company(self, company_id: str) -> Dict[str, Any]:
        """
        Main ReAct loop for analyzing a company.
        Implements: Thought → Action → Observation sequence
        """
        print(f"\n{'='*60}")
        print(f"🔍 Starting Due Diligence Analysis for: {company_id}")
        print(f"System: {self.system_prompt}")
        print(f"{'='*60}")
        
        analysis_results = {
            "company_id": company_id,
            "payload": None,
            "risk_signals": [],
            "key_findings": []
        }
        
        # Step 1: Get Payload
        self.log_react_step("THOUGHT", 
            f"I need to retrieve the structured payload for {company_id} to understand the company.")
        
        self.log_react_step("ACTION", {
            "action": "GET_PAYLOAD",
            "params": {"company_id": company_id}
        })
        
        payload = await self.execute_action(ActionType.GET_PAYLOAD, {"company_id": company_id})
        
        self.log_react_step("OBSERVATION", 
            f"Retrieved payload with company: {payload.company_record.get('legal_name', 'Unknown')}, "
            f"events: {len(payload.events)}, products: {len(payload.products)}")
        
        analysis_results["payload"] = payload
        
        # Step 2: Search for Risk Signals
        risk_queries = [
            "layoffs workforce reduction",
            "lawsuit legal action litigation",
            "data breach security incident",
            "funding issues financial trouble"
        ]
        
        for query in risk_queries:
            self.log_react_step("THOUGHT", 
                f"I should search for potential risks related to '{query}'")
            
            self.log_react_step("ACTION", {
                "action": "SEARCH_RAG",
                "params": {"company_id": company_id, "query": query}
            })
            
            search_results = await self.execute_action(
                ActionType.SEARCH_RAG, 
                {"company_id": company_id, "query": query}
            )
            
            # Analyze search results
            relevant_results = [r for r in search_results if r['score'] > 0.3]
            
            self.log_react_step("OBSERVATION", 
                f"Found {len(relevant_results)} relevant results for '{query}'")
            
            # Step 3: Log risks if found
            if relevant_results and any(
                keyword in str(relevant_results).lower() 
                for keyword in ['layoff', 'reduction', 'cut', 'terminate']
            ):
                self.log_react_step("THOUGHT", 
                    "Risk signal detected! I should log this potential layoff/workforce event.")
                
                self.log_react_step("ACTION", {
                    "action": "LOG_RISK",
                    "params": {
                        "company_id": company_id,
                        "occurred_on": str(date.today()),
                        "description": f"Potential risk detected from RAG search: {query}",
                        "source_url": "https://example.com/analysis"
                    }
                })
                
                signal_logged = await self.execute_action(
                    ActionType.LOG_RISK,
                    {
                        "company_id": company_id,
                        "occurred_on": date.today(),
                        "description": f"Potential risk detected: {query}",
                        "source_url": "https://example.com/analysis"
                    }
                )
                
                self.log_react_step("OBSERVATION", 
                    f"Risk signal logged successfully: {signal_logged}")
                
                analysis_results["risk_signals"].append({
                    "query": query,
                    "results_count": len(relevant_results)
                })
        
        # Final Summary
        self.log_react_step("THOUGHT", 
            "Analysis complete. I should summarize my findings.")
        
        print(f"\n{'='*60}")
        print("📊 ANALYSIS SUMMARY")
        print(f"{'='*60}")
        print(f"Company: {company_id}")
        print(f"Payload Retrieved: ✅")
        print(f"Risk Queries Performed: {len(risk_queries)}")
        print(f"Risk Signals Found: {len(analysis_results['risk_signals'])}")
        print(f"{'='*60}\n")
        
        return analysis_results

# Convenience function for running the agent
async def run_supervisor_agent(company_id: str = "anthropic"):
    """Run the supervisor agent on a company"""
    supervisor = DueDiligenceSupervisor()
    results = await supervisor.analyze_company(company_id)
    
    # Save execution log
    log_file = f"logs/supervisor_run_{company_id}.json"
    with open(log_file, 'w') as f:
        json.dump({
            "execution_log": supervisor.execution_log,
            "results": {
                "company_id": results["company_id"],
                "risk_signals": results["risk_signals"]
            }
        }, f, indent=2, default=str)
    
    print(f"Execution log saved to: {log_file}")
    return results

if __name__ == "__main__":
    # Demo run
    import sys; company = sys.argv[1] if len(sys.argv) > 1 else "anthropic"; asyncio.run(run_supervisor_agent(company))