"""
Due Diligence Supervisor Agent using LangChain AgentExecutor.
Implements ReAct (Reasoning and Acting) pattern with LangChain callbacks.
Lab 16: Integrated with structured ReAct logging via custom callback handler.
"""

import asyncio
import json
import os
from datetime import date
from typing import Dict, Any, List, Optional, Type
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# LangChain imports
try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain.tools import StructuredTool
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.schema import AgentAction, AgentFinish, LLMResult
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("Warning: LangChain not available. Install with: pip install langchain langchain-openai")

from src.tools.payload_tool import get_latest_structured_payload, Payload
from src.tools.rag_tool import rag_search_company
from src.tools.risk_logger import report_layoff_signal, LayoffSignal
from src.logging.react_logger import ReActLogger


class ReActCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback handler that intercepts agent steps and logs them
    using the ReActLogger for structured logging.
    """
    
    def __init__(self, react_logger: ReActLogger):
        """
        Initialize callback handler with ReAct logger.
        
        Args:
            react_logger: ReActLogger instance to use for logging
        """
        super().__init__()
        self.logger = react_logger
        self.current_thought: Optional[str] = None
        self.current_action: Optional[str] = None
        self.current_action_input: Optional[Dict[str, Any]] = None
        self.logged_actions: set = set()  # Track logged actions to prevent duplicates
    
    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Called when LLM starts running."""
        # Extract thought/reasoning from prompts if available
        if prompts:
            prompt_text = prompts[0]
            # Try to extract reasoning from the prompt
            if "Thought:" in prompt_text or "I need" in prompt_text or "I should" in prompt_text:
                # Extract the thought portion
                thought_lines = []
                for line in prompt_text.split('\n'):
                    if any(keyword in line for keyword in ['Thought:', 'I need', 'I should', 'Let me']):
                        thought_lines.append(line.strip())
                if thought_lines:
                    self.current_thought = ' '.join(thought_lines)
                    self.logger.log_thought(self.current_thought)
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM ends running."""
        pass
    
    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when LLM errors."""
        self.logger.log_observation(
            f"LLM Error: {str(error)}",
            observation_data={"error": str(error), "error_type": type(error).__name__}
        )
    
    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Called when chain starts running."""
        pass
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when chain ends running."""
        pass
    
    def on_chain_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when chain errors."""
        self.logger.log_observation(
            f"Chain Error: {str(error)}",
            observation_data={"error": str(error), "error_type": type(error).__name__}
        )
    
    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """
        Called when a tool starts running.
        This captures the ACTION step in ReAct pattern.
        """
        tool_name = serialized.get("name", "unknown_tool")
        
        # Handle different input formats
        if input_str is None:
            input_str = ""
        if not isinstance(input_str, str):
            input_str = str(input_str)
        
        # Parse input_str to extract parameters
        try:
            # Try to parse as JSON if it's a JSON string
            if input_str.strip().startswith('{') or input_str.strip().startswith('['):
                action_input = json.loads(input_str)
            else:
                # Otherwise, treat as a simple string parameter
                action_input = {"input": input_str}
        except (json.JSONDecodeError, ValueError):
            action_input = {"input": input_str}
        
        self.current_action = tool_name
        self.current_action_input = action_input
        
        # Create unique key for this action to prevent duplicates
        action_key = f"{tool_name}_{hash(str(action_input))}"
        
        # Log the action only if not already logged
        if action_key not in self.logged_actions:
            self.logged_actions.add(action_key)
            self.logger.log_action(tool_name, action_input)
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """
        Called when a tool ends running.
        This captures the OBSERVATION step in ReAct pattern.
        """
        # Handle None or empty output
        if output is None:
            output = ""
        
        # Convert output to string if it's not already
        if not isinstance(output, str):
            output = str(output)
        
        # Parse output if it's JSON
        observation_data = None
        try:
            if output.strip().startswith('{') or output.strip().startswith('['):
                observation_data = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Create observation text
        if output:
            observation_text = output[:500] if len(output) > 500 else output
        else:
            observation_text = f"Tool {self.current_action} completed (no output)"
        
        # Log the observation
        self.logger.log_observation(
            observation_text,
            observation_data=observation_data or {"raw_output": output}
        )
        
        # Reset current action
        self.current_action = None
        self.current_action_input = None
    
    def on_tool_error(self, error: Exception, **kwargs: Any) -> None:
        """Called when a tool errors."""
        self.logger.log_observation(
            f"Tool Error: {str(error)}",
            observation_data={
                "error": str(error),
                "error_type": type(error).__name__,
                "tool": self.current_action
            }
        )
    
    def on_agent_action(
        self, action: AgentAction, **kwargs: Any
    ) -> None:
        """
        Called when agent takes an action.
        This is where we capture the agent's decision to use a tool.
        We log the action here as a fallback if on_tool_start doesn't fire.
        """
        # Extract thought from log if available
        if action.log:
            # Try to extract reasoning from the log
            log_lines = action.log.split('\n')
            for line in log_lines:
                if 'Thought:' in line or 'I need' in line or 'I should' in line:
                    thought = line.replace('Thought:', '').strip()
                    if thought and thought != self.current_thought:
                        self.logger.log_thought(thought)
                        self.current_thought = thought
        
        # Log action here as fallback (on_tool_start may not fire for async tools)
        # Check if we already logged this action to avoid duplicates
        tool_name = action.tool
        tool_input = action.tool_input
        
        if tool_name:
            # Parse tool_input
            if isinstance(tool_input, dict):
                action_input = {"tool_input": tool_input}
            elif isinstance(tool_input, str):
                try:
                    action_input = {"tool_input": json.loads(tool_input)}
                except (json.JSONDecodeError, ValueError):
                    action_input = {"tool_input": {"input": tool_input}}
            else:
                action_input = {"tool_input": {"input": str(tool_input)}}
            
            # Create unique key for this action to prevent duplicates
            action_key = f"{tool_name}_{hash(str(action_input))}"
            
            # Only log if we haven't already logged this action
            # (on_tool_start might have already logged it)
            if action_key not in self.logged_actions:
                self.logged_actions.add(action_key)
                self.current_action = tool_name
                self.current_action_input = action_input
                self.logger.log_action(tool_name, action_input)
    
    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """
        Called when agent finishes.
        This captures the final observation/result.
        """
        if finish.return_values:
            self.logger.log_observation(
                f"Agent finished: {finish.return_values.get('output', 'Analysis complete')}",
                observation_data=finish.return_values
            )


def create_langchain_tools():
    """
    Convert our async tools to LangChain StructuredTool format.
    Uses the 'coroutine' parameter to support async functions directly.
    """
    # Tool 1: Get Payload
    async def _get_payload(company_id: str) -> str:
        """Get the latest structured payload for a company."""
        payload = await get_latest_structured_payload(company_id)
        return json.dumps({
            "company_name": payload.company_record.get("legal_name", "Unknown"),
            "events_count": len(payload.events),
            "products_count": len(payload.products),
            "payload": payload.model_dump()
        }, default=str)
    
    payload_tool = StructuredTool.from_function(
        coroutine=_get_payload,  # Use coroutine parameter for async functions
        name="get_latest_structured_payload",
        description=(
            "Retrieve the latest fully assembled structured payload for a company. "
            "Returns company information, events, products, and other structured data. "
            "Input should be a company_id string (e.g., 'anthropic', 'databricks')."
        )
    )
    
    # Tool 2: RAG Search
    async def _rag_search(company_id: str, query: str) -> str:
        """Search for information about a company using RAG."""
        results = await rag_search_company(company_id, query)
        return json.dumps(results, default=str)
    
    rag_tool = StructuredTool.from_function(
        coroutine=_rag_search,  # Use coroutine parameter for async functions
        name="rag_search_company",
        description=(
            "Perform retrieval-augmented search for a company. "
            "Searches the vector database for relevant information. "
            "Takes two parameters: company_id (string) and query (string). "
            "Example: rag_search_company('anthropic', 'layoffs')"
        )
    )
    
    # Tool 3: Report Risk Signal
    async def _report_risk(company_id: str, occurred_on: str, description: str, source_url: str) -> str:
        """Report a risk signal (layoff, breach, etc.) for a company."""
        signal = LayoffSignal(
            company_id=company_id,
            occurred_on=date.fromisoformat(occurred_on) if isinstance(occurred_on, str) else occurred_on,
            description=description,
            source_url=source_url
        )
        result = await report_layoff_signal(signal)
        return json.dumps({"logged": result, "signal": signal.model_dump()}, default=str)
    
    risk_tool = StructuredTool.from_function(
        coroutine=_report_risk,  # Use coroutine parameter for async functions
        name="report_layoff_signal",
        description=(
            "Log a high-risk signal (layoff, workforce reduction, data breach, etc.) for a company. "
            "Takes four parameters: company_id (string), occurred_on (YYYY-MM-DD string), "
            "description (string), and source_url (string)."
        )
    )
    
    return [payload_tool, rag_tool, risk_tool]


class DueDiligenceSupervisorLangChain:
    """
    PE Due Diligence Supervisor Agent using LangChain AgentExecutor.
    Implements ReAct pattern with structured logging via callbacks.
    """
    
    def __init__(
        self,
        run_id: Optional[str] = None,
        enable_logging: bool = True,
        llm_model: str = "gpt-4o-mini",
        temperature: float = 0.0
    ):
        """
        Initialize supervisor agent with LangChain.
        
        Args:
            run_id: Optional correlation ID for logging (auto-generated if None)
            enable_logging: Whether to enable structured ReAct logging
            llm_model: OpenAI model to use
            temperature: LLM temperature
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is required. Install with: "
                "pip install langchain langchain-openai"
            )
        
        # Initialize ReAct logger
        self.enable_logging = enable_logging
        self.logger: Optional[ReActLogger] = None
        if enable_logging:
            self.logger = ReActLogger(run_id=run_id, company_id=None)
        
        # Initialize LLM
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.llm = ChatOpenAI(
            model=llm_model,
            temperature=temperature,
            openai_api_key=openai_api_key
        )
        
        # Create tools
        self.tools = create_langchain_tools()
        
        # Create system prompt
        self.system_prompt = (
            "You are a PE Due Diligence Supervisor Agent. "
            "Your job is to analyze companies by:\n"
            "1. Retrieving their structured payload data\n"
            "2. Searching for potential risks (layoffs, lawsuits, breaches, funding issues)\n"
            "3. Logging any detected risk signals\n"
            "4. Providing a comprehensive analysis\n\n"
            "Always think step by step. Use the available tools to gather information. "
            "When you detect risks, log them using report_layoff_signal."
        )
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent
        self.agent = create_openai_tools_agent(self.llm, self.tools, self.prompt)
        
        # Agent executor will be created per-company with callbacks
        self.agent_executor: Optional[AgentExecutor] = None
    
    async def analyze_company(self, company_id: str) -> Dict[str, Any]:
        """
        Analyze a company using LangChain agent with ReAct logging.
        
        Args:
            company_id: Company to analyze
            
        Returns:
            Analysis results with trace information
        """
        # Initialize logger for this company
        if self.logger:
            if self.logger.company_id == "unknown" or not self.logger.company_id:
                self.logger.company_id = company_id
            self.logger.trace.company_id = company_id
        
        print(f"\n{'='*60}")
        try:
            print(f"🔍 Starting LangChain Agent Analysis for: {company_id}")
        except UnicodeEncodeError:
            print(f"Starting LangChain Agent Analysis for: {company_id}")
        if self.logger:
            print(f"Run ID: {self.logger.run_id}")
        print(f"{'='*60}\n")
        
        # Create callback handler
        callbacks = []
        if self.logger:
            callback_handler = ReActCallbackHandler(self.logger)
            callbacks = [callback_handler]
        
        # Create agent executor with callbacks
        agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            callbacks=callbacks,
            handle_parsing_errors=True,
            max_iterations=15,
            max_execution_time=300  # 5 minutes max
        )
        
        # Log initial thought
        if self.logger:
            initial_thought = (
                f"I need to analyze {company_id} by retrieving its payload, "
                "searching for risks, and logging any detected signals."
            )
            self.logger.log_thought(initial_thought)
        
        # Prepare input
        user_input = (
            f"Analyze the company '{company_id}'. "
            "First, retrieve the structured payload. "
            "Then search for potential risks related to: "
            "1. Layoffs or workforce reductions, "
            "2. Lawsuits or legal actions, "
            "3. Data breaches or security incidents, "
            "4. Funding issues or financial trouble. "
            "If you find any risks, log them using report_layoff_signal. "
            "Provide a summary of your findings."
        )
        
        try:
            # Run agent
            result = await agent_executor.ainvoke(
                {
                    "input": user_input,
                    "chat_history": []
                }
            )
            
            # Extract output
            output = result.get("output", "Analysis completed")
            
            # Log final observation
            if self.logger:
                self.logger.log_observation(
                    f"Analysis complete: {output[:500]}",
                    observation_data={"output": output, "result": result}
                )
            
            # Save trace
            summary = {
                "company_id": company_id,
                "analysis_complete": True,
                "output_length": len(output),
                "total_steps": len(self.logger.get_steps()) if self.logger else 0
            }
            
            if self.logger:
                trace_file = self.logger.save_trace(summary=summary)
                return {
                    "company_id": company_id,
                    "output": output,
                    "result": result,
                    "trace_file": str(trace_file),
                    "run_id": self.logger.run_id,
                    "summary": summary
                }
            else:
                return {
                    "company_id": company_id,
                    "output": output,
                    "result": result
                }
        
        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}"
            if self.logger:
                self.logger.log_observation(
                    error_msg,
                    observation_data={"error": str(e), "error_type": type(e).__name__}
                )
                trace_file = self.logger.save_trace(summary={"error": str(e)})
                return {
                    "company_id": company_id,
                    "error": str(e),
                    "trace_file": str(trace_file),
                    "run_id": self.logger.run_id
                }
            else:
                return {
                    "company_id": company_id,
                    "error": str(e)
                }


# Convenience function
async def run_supervisor_agent_langchain(
    company_id: str = "anthropic",
    enable_logging: bool = True,
    run_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the LangChain-based supervisor agent on a company.
    
    Args:
        company_id: Company to analyze
        enable_logging: Whether to enable structured ReAct logging
        run_id: Optional correlation ID
        
    Returns:
        Analysis results with trace information
    """
    supervisor = DueDiligenceSupervisorLangChain(
        run_id=run_id,
        enable_logging=enable_logging
    )
    results = await supervisor.analyze_company(company_id)
    
    print(f"\n{'='*60}")
    try:
        print("📊 ANALYSIS COMPLETE")
    except UnicodeEncodeError:
        print("ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Company: {company_id}")
    if results.get("trace_file"):
        print(f"Trace File: {results['trace_file']}")
    if results.get("run_id"):
        print(f"Run ID: {results['run_id']}")
    if results.get("error"):
        print(f"Error: {results['error']}")
    else:
        try:
            print("Status: ✅ Success")
        except UnicodeEncodeError:
            print("Status: OK Success")
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    import sys
    company = sys.argv[1] if len(sys.argv) > 1 else "anthropic"
    asyncio.run(run_supervisor_agent_langchain(company))

