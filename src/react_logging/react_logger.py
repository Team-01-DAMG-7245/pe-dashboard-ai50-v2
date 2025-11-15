"""
ReAct Logger for Lab 16
Structured logging system for Thought/Action/Observation patterns
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Try to import rich for pretty console output, fallback to basic print
try:
    from rich.console import Console
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from src.logging.schemas import ReActLogEntry, ReActTrace, StepType


class ReActLogger:
    """
    Structured logger for ReAct (Reasoning and Acting) pattern.
    Logs Thought → Action → Observation triplets with full context.
    """
    
    def __init__(
        self,
        run_id: Optional[str] = None,
        company_id: Optional[str] = None,
        log_dir: str = "logs",
        console_output: bool = True,
        file_output: bool = True
    ):
        """
        Initialize ReAct logger.
        
        Args:
            run_id: Correlation ID for this execution session (auto-generated if None)
            company_id: Company being analyzed
            log_dir: Directory to save log files (will create react_traces subdirectory)
            console_output: Whether to print to console
            file_output: Whether to save to file
        """
        self.run_id = run_id or str(uuid.uuid4())
        self.company_id = company_id or "unknown"
        self.log_dir = Path(log_dir)
        
        # Create react_traces subdirectory
        self.trace_dir = self.log_dir / "react_traces"
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        
        self.console_output = console_output
        self.file_output = file_output
        self.console = Console() if (console_output and RICH_AVAILABLE) else None
        
        self.step_number = 0
        self.steps: list[ReActLogEntry] = []
        self.trace = ReActTrace(
            run_id=self.run_id,
            company_id=self.company_id,
            started_at=datetime.now()
        )
    
    def log_thought(self, thought: str, metadata: Optional[Dict[str, Any]] = None) -> ReActLogEntry:
        """
        Log a Thought step (reasoning).
        
        Args:
            thought: The reasoning/thought content
            metadata: Additional metadata
            
        Returns:
            ReActLogEntry: The created log entry
        """
        self.step_number += 1
        entry = ReActLogEntry(
            timestamp=datetime.now(),
            run_id=self.run_id,
            company_id=self.company_id,
            step_number=self.step_number,
            step_type=StepType.THOUGHT,
            thought=thought,
            metadata=metadata or {}
        )
        
        self.steps.append(entry)
        self.trace.steps.append(entry)
        
        if self.console_output:
            self._print_thought(entry)
        
        if self.file_output:
            self._append_to_file(entry)
        
        return entry
    
    def log_action(
        self,
        action: str,
        action_input: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReActLogEntry:
        """
        Log an Action step (tool execution).
        
        Args:
            action: Name of the action/tool
            action_input: Input parameters for the action
            metadata: Additional metadata
            
        Returns:
            ReActLogEntry: The created log entry
        """
        self.step_number += 1
        entry = ReActLogEntry(
            timestamp=datetime.now(),
            run_id=self.run_id,
            company_id=self.company_id,
            step_number=self.step_number,
            step_type=StepType.ACTION,
            action=action,
            action_input=action_input,
            metadata=metadata or {}
        )
        
        self.steps.append(entry)
        self.trace.steps.append(entry)
        
        if self.console_output:
            self._print_action(entry)
        
        if self.file_output:
            self._append_to_file(entry)
        
        return entry
    
    def log_observation(
        self,
        observation: str,
        observation_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReActLogEntry:
        """
        Log an Observation step (result from action).
        
        Args:
            observation: Text description of the observation
            observation_data: Structured observation data
            metadata: Additional metadata
            
        Returns:
            ReActLogEntry: The created log entry
        """
        self.step_number += 1
        entry = ReActLogEntry(
            timestamp=datetime.now(),
            run_id=self.run_id,
            company_id=self.company_id,
            step_number=self.step_number,
            step_type=StepType.OBSERVATION,
            observation=observation,
            observation_data=observation_data,
            metadata=metadata or {}
        )
        
        self.steps.append(entry)
        self.trace.steps.append(entry)
        
        if self.console_output:
            self._print_observation(entry)
        
        if self.file_output:
            self._append_to_file(entry)
        
        return entry
    
    def _print_thought(self, entry: ReActLogEntry):
        """Print thought to console with pretty formatting"""
        try:
            if self.console:
                text = Text(f"🤔 THOUGHT: {entry.thought}", style="cyan")
                self.console.print(text)
            else:
                print(f"\n🤔 THOUGHT: {entry.thought}")
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(f"\nTHOUGHT: {entry.thought}")
    
    def _print_action(self, entry: ReActLogEntry):
        """Print action to console with pretty formatting"""
        try:
            action_text = f"🎯 ACTION: {entry.action}"
            params_text = f"   Input: {json.dumps(entry.action_input, indent=2, default=str)}"
            
            if self.console:
                text = Text(action_text, style="yellow")
                self.console.print(text)
                if entry.action_input:
                    self.console.print(Text(params_text, style="dim"))
            else:
                print(f"\n{action_text}")
                if entry.action_input:
                    print(params_text)
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(f"\nACTION: {entry.action}")
            if entry.action_input:
                print(f"   Input: {json.dumps(entry.action_input, indent=2, default=str)}")
    
    def _print_observation(self, entry: ReActLogEntry):
        """Print observation to console with pretty formatting"""
        # Truncate long observations for console
        obs_text = entry.observation
        if len(obs_text) > 300:
            obs_text = obs_text[:300] + "..."
        
        try:
            if self.console:
                text = Text(f"👁️  OBSERVATION: {obs_text}", style="green")
                self.console.print(text)
            else:
                print(f"👁️  OBSERVATION: {obs_text}")
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(f"OBSERVATION: {obs_text}")
    
    def _append_to_file(self, entry: ReActLogEntry):
        """Append log entry to JSONL file"""
        log_file = self.trace_dir / f"react_trace_{self.run_id}.jsonl"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry.to_dict(), default=str) + '\n')
    
    def save_trace(self, summary: Optional[Dict[str, Any]] = None) -> Path:
        """
        Save complete trace to JSON file in logs/react_traces/ directory.
        
        Args:
            summary: Optional summary data to include
            
        Returns:
            Path: Path to saved trace file
        """
        self.trace.completed_at = datetime.now()
        self.trace.summary = summary
        
        trace_file = self.trace_dir / f"react_trace_{self.run_id}.json"
        with open(trace_file, 'w', encoding='utf-8') as f:
            json.dump(self.trace.to_dict(), f, indent=2, default=str)
        
        if self.console_output:
            try:
                if self.console:
                    self.console.print(f"\n💾 Trace saved to: {trace_file}")
                else:
                    print(f"\n💾 Trace saved to: {trace_file}")
            except UnicodeEncodeError:
                print(f"\nTrace saved to: {trace_file}")
        
        return trace_file
    
    def get_trace(self) -> ReActTrace:
        """Get the current trace object"""
        return self.trace
    
    def get_steps(self) -> list[ReActLogEntry]:
        """Get all logged steps"""
        return self.steps.copy()
    
    def reset(self, new_run_id: Optional[str] = None, new_company_id: Optional[str] = None):
        """Reset logger for a new execution"""
        if new_run_id:
            self.run_id = new_run_id
        else:
            self.run_id = str(uuid.uuid4())
        
        if new_company_id:
            self.company_id = new_company_id
        
        self.step_number = 0
        self.steps = []
        self.trace = ReActTrace(
            run_id=self.run_id,
            company_id=self.company_id,
            started_at=datetime.now()
        )
