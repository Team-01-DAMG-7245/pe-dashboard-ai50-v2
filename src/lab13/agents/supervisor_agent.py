"""
Due Diligence Supervisor Agent for Assignment 5.
Implements ReAct (Reasoning and Acting) pattern with the three core tools.
Lab 16: Integrated with structured ReAct logging.
"""

import asyncio
import json
from datetime import date
from typing import Dict, Any, List, Optional
from enum import Enum

from src.lab12.tools.payload_tool import get_latest_structured_payload
from src.lab12.tools.rag_tool import rag_search_company
from src.lab12.tools.risk_logger import report_layoff_signal, LayoffSignal
from .HITL_INTEGRATION_PATCH import add_hitl_to_supervisor
from src.lab16.react_logging.react_logger import ReActLogger

class ActionType(Enum):
    """Available actions for the agent"""
    GET_PAYLOAD = "get_payload"
    SEARCH_RAG = "search_rag"
    LOG_RISK = "log_risk"
    COMPLETE = "complete"

@add_hitl_to_supervisor
class DueDiligenceSupervisor:
    """
    PE Due Diligence Supervisor Agent that uses tools to retrieve payloads,
    run RAG queries, log risks, and generate PE dashboards.
    Lab 16: Uses structured ReAct logging for full traceability.
    """
    
    def __init__(self, run_id: Optional[str] = None, enable_logging: bool = True):
        """
        Initialize supervisor agent.
        
        Args:
            run_id: Optional correlation ID for logging (auto-generated if None)
            enable_logging: Whether to enable structured ReAct logging
        """
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
        
        # Initialize ReAct logger (Lab 16)
        self.enable_logging = enable_logging
        self.logger: Optional[ReActLogger] = None
        if enable_logging:
            self.logger = ReActLogger(run_id=run_id, company_id=None)  # Will be set in analyze_company
        
        # Keep backward compatibility
        self.execution_log = []
    
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
        Lab 16: Uses structured ReAct logging for full traceability.
        """
        # Initialize logger for this company if not already set
        if self.logger:
            if self.logger.company_id == "unknown" or not self.logger.company_id:
                self.logger.company_id = company_id
            # Update trace company_id as well
            self.logger.trace.company_id = company_id
        
        print(f"\n{'='*60}")
        try:
            print(f"🔍 Starting Due Diligence Analysis for: {company_id}")
        except UnicodeEncodeError:
            print(f"Starting Due Diligence Analysis for: {company_id}")
        print(f"System: {self.system_prompt}")
        if self.logger:
            print(f"Run ID: {self.logger.run_id}")
        print(f"{'='*60}")
        
        analysis_results = {
            "company_id": company_id,
            "payload": None,
            "risk_signals": [],
            "key_findings": []
        }
        
        # Step 1: Get Payload
        thought = f"I need to retrieve the structured payload for {company_id} to understand the company."
        if self.logger:
            self.logger.log_thought(thought)
        else:
            try:
                print(f"\n🤔 THOUGHT: {thought}")
            except UnicodeEncodeError:
                print(f"\nTHOUGHT: {thought}")
        
        action_input = {"company_id": company_id}
        if self.logger:
            self.logger.log_action("get_latest_structured_payload", action_input)
        else:
            try:
                print(f"🎯 ACTION: GET_PAYLOAD with params {action_input}")
            except UnicodeEncodeError:
                print(f"ACTION: GET_PAYLOAD with params {action_input}")
        
        payload = await self.execute_action(ActionType.GET_PAYLOAD, {"company_id": company_id})
        
        observation = (
            f"Retrieved payload with company: {payload.company_record.get('legal_name', 'Unknown')}, "
            f"events: {len(payload.events)}, products: {len(payload.products)}"
        )
        observation_data = {
            "company_name": payload.company_record.get('legal_name', 'Unknown'),
            "events_count": len(payload.events),
            "products_count": len(payload.products)
        }
        
        if self.logger:
            self.logger.log_observation(observation, observation_data=observation_data)
        else:
            try:
                print(f"👁️ OBSERVATION: {observation}")
            except UnicodeEncodeError:
                print(f"OBSERVATION: {observation}")
        
        analysis_results["payload"] = payload
        
        # Step 2: Search for Risk Signals
        risk_queries = [
            "layoffs workforce reduction",
            "lawsuit legal action litigation",
            "data breach security incident",
            "funding issues financial trouble"
        ]
        
        for query in risk_queries:
            thought = f"I should search for potential risks related to '{query}'"
            if self.logger:
                self.logger.log_thought(thought)
            else:
                try:
                    print(f"\n🤔 THOUGHT: {thought}")
                except UnicodeEncodeError:
                    print(f"\nTHOUGHT: {thought}")
            
            action_input = {"company_id": company_id, "query": query}
            if self.logger:
                self.logger.log_action("rag_search_company", action_input)
            else:
                try:
                    print(f"🎯 ACTION: SEARCH_RAG with params {action_input}")
                except UnicodeEncodeError:
                    print(f"ACTION: SEARCH_RAG with params {action_input}")
            
            search_results = await self.execute_action(
                ActionType.SEARCH_RAG, 
                {"company_id": company_id, "query": query}
            )
            
            # Analyze search results
            relevant_results = [r for r in search_results if r['score'] > 0.3]
            
            observation = f"Found {len(relevant_results)} relevant results for '{query}'"
            observation_data = {
                "total_results": len(search_results),
                "relevant_results": len(relevant_results),
                "query": query,
                "top_scores": [r['score'] for r in relevant_results[:3]]
            }
            
            if self.logger:
                self.logger.log_observation(observation, observation_data=observation_data)
            else:
                try:
                    print(f"👁️ OBSERVATION: {observation}")
                except UnicodeEncodeError:
                    print(f"OBSERVATION: {observation}")
            
            # Step 3: Log risks if found
            if relevant_results and any(
                keyword in str(relevant_results).lower() 
                for keyword in ['layoff', 'reduction', 'cut', 'terminate']
            ):
                thought = "Risk signal detected! I should log this potential layoff/workforce event."
                if self.logger:
                    self.logger.log_thought(thought)
                else:
                    try:
                        print(f"\n🤔 THOUGHT: {thought}")
                    except UnicodeEncodeError:
                        print(f"\nTHOUGHT: {thought}")
                
                action_input = {
                    "company_id": company_id,
                    "occurred_on": str(date.today()),
                    "description": f"Potential risk detected from RAG search: {query}",
                    "source_url": "https://example.com/analysis"
                }
                
                if self.logger:
                    self.logger.log_action("report_layoff_signal", action_input)
                else:
                    try:
                        print(f"🎯 ACTION: LOG_RISK with params {action_input}")
                    except UnicodeEncodeError:
                        print(f"ACTION: LOG_RISK with params {action_input}")
                
                signal_logged = await self.execute_action(
                    ActionType.LOG_RISK,
                    {
                        "company_id": company_id,
                        "occurred_on": date.today(),
                        "description": f"Potential risk detected: {query}",
                        "source_url": "https://example.com/analysis"
                    }
                )
                
                observation = f"Risk signal logged successfully: {signal_logged}"
                if self.logger:
                    self.logger.log_observation(observation, observation_data={"logged": signal_logged})
                else:
                    try:
                        print(f"👁️ OBSERVATION: {observation}")
                    except UnicodeEncodeError:
                        print(f"OBSERVATION: {observation}")
                
                analysis_results["risk_signals"].append({
                    "query": query,
                    "results_count": len(relevant_results)
                })
        
        # Final Summary
        thought = "Analysis complete. I should summarize my findings."
        if self.logger:
            self.logger.log_thought(thought)
        else:
            try:
                print(f"\n🤔 THOUGHT: {thought}")
            except UnicodeEncodeError:
                print(f"\nTHOUGHT: {thought}")
        
        print(f"\n{'='*60}")
        try:
            print("📊 ANALYSIS SUMMARY")
        except UnicodeEncodeError:
            print("ANALYSIS SUMMARY")
        print(f"{'='*60}")
        print(f"Company: {company_id}")
        try:
            print(f"Payload Retrieved: ✅")
        except UnicodeEncodeError:
            print(f"Payload Retrieved: OK")
        print(f"Risk Queries Performed: {len(risk_queries)}")
        print(f"Risk Signals Found: {len(analysis_results['risk_signals'])}")
        if self.logger:
            print(f"Total Steps Logged: {len(self.logger.get_steps())}")
        print(f"{'='*60}\n")
        
        # Save trace if logging is enabled (Lab 16)
        if self.logger:
            summary = {
                "company_id": company_id,
                "payload_retrieved": True,
                "risk_queries_performed": len(risk_queries),
                "risk_signals_found": len(analysis_results['risk_signals']),
                "total_steps": len(self.logger.get_steps())
            }
            trace_file = self.logger.save_trace(summary=summary)
            analysis_results["trace_file"] = str(trace_file)
            analysis_results["run_id"] = self.logger.run_id
        
        return analysis_results

# Convenience function for running the agent
async def run_supervisor_agent(company_id: str = "anthropic", enable_logging: bool = True):
    """
    Run the supervisor agent on a company.
    
    Args:
        company_id: Company to analyze
        enable_logging: Whether to enable structured ReAct logging (Lab 16)
    
    Returns:
        Analysis results with trace information
    """
    supervisor = DueDiligenceSupervisor(enable_logging=enable_logging)
    results = await supervisor.analyze_company(company_id)
    
    # Save execution log (backward compatibility)
    log_file = f"logs/supervisor_run_{company_id}.json"
    with open(log_file, 'w') as f:
        json.dump({
            "execution_log": supervisor.execution_log,
            "results": {
                "company_id": results["company_id"],
                "risk_signals": results["risk_signals"]
            },
            "trace_file": results.get("trace_file"),
            "run_id": results.get("run_id")
        }, f, indent=2, default=str)
    
    print(f"Execution log saved to: {log_file}")
    if results.get("trace_file"):
        print(f"ReAct trace saved to: {results['trace_file']}")
    
    return results

if __name__ == "__main__":
    # Demo run
    import sys; company = sys.argv[1] if len(sys.argv) > 1 else "anthropic"; asyncio.run(run_supervisor_agent(company))