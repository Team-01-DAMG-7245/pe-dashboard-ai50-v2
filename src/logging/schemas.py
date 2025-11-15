"""
Pydantic schemas for ReAct logging entries
Lab 16: Structured logging for Thought/Action/Observation patterns
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Type of ReAct step"""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"


class ReActLogEntry(BaseModel):
    """
    Structured log entry for a single ReAct step.
    Captures Thought, Action, or Observation with full context.
    """
    timestamp: datetime = Field(default_factory=datetime.now, description="When the step occurred")
    run_id: str = Field(..., description="Correlation ID for tracking full execution session")
    company_id: str = Field(..., description="Company being analyzed")
    step_number: int = Field(..., description="Sequential step number in the execution")
    step_type: StepType = Field(..., description="Type of step: thought, action, or observation")
    
    # Thought fields
    thought: Optional[str] = Field(None, description="Reasoning/thought content")
    
    # Action fields
    action: Optional[str] = Field(None, description="Action/tool name being executed")
    action_input: Optional[Dict[str, Any]] = Field(None, description="Input parameters for the action")
    
    # Observation fields
    observation: Optional[str] = Field(None, description="Result/observation from action")
    observation_data: Optional[Dict[str, Any]] = Field(None, description="Structured observation data")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "run_id": self.run_id,
            "company_id": self.company_id,
            "step_number": self.step_number,
            "step_type": self.step_type,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
            "observation_data": self.observation_data,
            "metadata": self.metadata
        }


class ReActTrace(BaseModel):
    """
    Complete trace of a ReAct execution session.
    Contains all steps for a single run.
    """
    run_id: str = Field(..., description="Correlation ID for this execution")
    company_id: str = Field(..., description="Company analyzed")
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None)
    steps: list[ReActLogEntry] = Field(default_factory=list, description="All ReAct steps")
    summary: Optional[Dict[str, Any]] = Field(None, description="Execution summary")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "run_id": self.run_id,
            "company_id": self.company_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [step.to_dict() for step in self.steps],
            "summary": self.summary
        }

