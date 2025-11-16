"""
Lab 17: Graph-based Supervisory Workflow using LangGraph

Implements a supervisory workflow for due diligence dashboard generation with:
- Conditional branching based on risk signals
- Human-in-the-loop (HITL) approval for high-risk cases
- Multi-stage processing: Planning → Data Generation → Evaluation → Risk Detection
"""

import os
import json
import uuid
from typing import TypedDict, List, Dict, Optional, Literal, Any
from pathlib import Path
from datetime import datetime

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Fallback if langgraph not available
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
    MemorySaver = None
# Import dotenv with error handling to avoid logging conflicts
try:
    from dotenv import load_dotenv
except (ImportError, AttributeError) as e:
    # Fallback if dotenv import fails due to logging conflict
    def load_dotenv(*args, **kwargs):
        pass  # No-op if dotenv can't be loaded
    print(f"[WARNING] Could not load dotenv: {e}")

from openai import OpenAI
import requests

# Import HITL handler - handle both relative and absolute imports
try:
    # Try new lab18 path first
    from src.lab18.hitl_handler import pause_for_approval
except (ImportError, ValueError):
    # Fallback for absolute import
    try:
        from lab18.hitl_handler import pause_for_approval
    except ImportError:
        # Last resort: add src to path and import
        import sys
        from pathlib import Path
        src_path = Path(__file__).resolve().parents[3]
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        from src.lab18.hitl_handler import pause_for_approval

# Load environment variables
project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Please set it in .env file.")
client = OpenAI(api_key=api_key)

# API base URL for dashboard generation
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8002")


# ============================================================================
# STATE SCHEMA
# ============================================================================

class WorkflowState(TypedDict):
    """
    State schema for the due diligence workflow graph.
    
    All fields are optional to allow incremental updates as the graph progresses.
    """
    company_id: str  # Company identifier (e.g., "anthropic", "abridge")
    run_id: str  # Unique run identifier for tracking
    structured_data: Optional[Dict]  # Normalized structured payload from Lab 5/6
    rag_insights: Optional[List[Dict]]  # RAG retrieval results with chunks and metadata
    risk_signals: Optional[List[Dict]]  # Detected risk signals with severity
    dashboard: Optional[str]  # Generated dashboard markdown
    dashboard_score: Optional[float]  # Quality score from evaluator (1-10)
    requires_hitl: bool  # Flag indicating if human approval is needed
    hitl_approved: bool  # Flag indicating if human has approved
    hitl_reviewer: Optional[str]  # Name/ID of the reviewer
    hitl_timestamp: Optional[str]  # Timestamp of approval decision
    hitl_notes: Optional[str]  # Optional notes from reviewer
    execution_plan: Optional[Dict]  # Plan created by planner node
    error: Optional[str]  # Error message if any step fails


# ============================================================================
# GLOBAL TRACE STATE
# ============================================================================

# Global state for workflow trace logging
_workflow_trace_events: List[Dict[str, Any]] = []
_workflow_node_order: List[str] = []


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

def planner_node(state: WorkflowState) -> WorkflowState:
    """
    PLANNER NODE: Creates execution plan for dashboard generation.
    
    Responsibilities:
    - Analyze company_id and determine data requirements
    - Decide which pipelines to use (RAG, Structured, or both)
    - Set execution parameters (top_k for RAG, etc.)
    - Initialize run_id if not present
    
    Returns:
        Updated state with execution_plan and run_id
    """
    company_id = state.get("company_id", "")
    run_id = state.get("run_id", "")
    
    if not company_id:
        return {**state, "error": "company_id is required"}
    
    # Generate run_id if not present
    if not run_id:
        run_id = f"{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    # Log node execution
    _workflow_node_order.append("planner")
    _workflow_trace_events.append({
        "event_type": "NODE_EXECUTED",
        "timestamp": datetime.now().isoformat(),
        "node": "planner",
        "run_id": run_id,
        "company_id": company_id
    })
    
    # Create execution plan
    execution_plan = {
        "company_id": company_id,
        "run_id": run_id,
        "pipelines": {
            "structured": True,  # Always use structured pipeline
            "rag": True  # Also use RAG for comprehensive coverage
        },
        "rag_params": {
            "top_k": 10  # Default number of chunks to retrieve
        },
        "priority": "normal",  # Can be "high", "normal", "low"
        "created_at": datetime.now().isoformat()
    }
    
    print(f"[PLANNER] Created execution plan for {company_id} (run_id: {run_id})")
    
    return {
        **state,
        "run_id": run_id,
        "execution_plan": execution_plan
    }


def data_generator_node(state: WorkflowState) -> WorkflowState:
    """
    DATA GENERATOR NODE: Calls MCP tools/API endpoints to gather data.
    
    Responsibilities:
    - Load structured payload from data/payloads/
    - Call RAG endpoint to get vector DB insights
    - Aggregate data from both pipelines
    - Handle errors gracefully
    
    Returns:
        Updated state with structured_data and rag_insights
    """
    company_id = state.get("company_id", "")
    run_id = state.get("run_id", "")
    execution_plan = state.get("execution_plan", {})
    
    # Log node execution
    _workflow_node_order.append("data_generator")
    _workflow_trace_events.append({
        "event_type": "NODE_EXECUTED",
        "timestamp": datetime.now().isoformat(),
        "node": "data_generator",
        "run_id": run_id,
        "company_id": company_id
    })
    
    if not company_id:
        return {**state, "error": "company_id is required for data generation"}
    
    structured_data = None
    rag_insights = []
    
    try:
        # 1. Load structured payload
        payload_path = project_root / "data" / "payloads" / f"{company_id}.json"
        if payload_path.exists():
            with open(payload_path, 'r', encoding='utf-8') as f:
                structured_data = json.load(f)
            print(f"[DATA_GENERATOR] Loaded structured payload for {company_id}")
        else:
            print(f"[DATA_GENERATOR] Warning: No structured payload found for {company_id}")
        
        # 2. Get RAG insights from API
        if execution_plan.get("pipelines", {}).get("rag", True):
            try:
                rag_params = execution_plan.get("rag_params", {"top_k": 10})
                response = requests.post(
                    f"{API_BASE}/dashboard/rag",
                    json={
                        "company_id": company_id,
                        "top_k": rag_params.get("top_k", 10)
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    rag_data = response.json()
                    rag_insights = [{
                        "chunks_used": rag_data.get("chunks_used", 0),
                        "dashboard_preview": rag_data.get("dashboard", "")[:500],  # First 500 chars
                        "source": "vector_db",
                        "retrieved_at": datetime.now().isoformat()
                    }]
                    print(f"[DATA_GENERATOR] Retrieved {rag_data.get('chunks_used', 0)} RAG chunks for {company_id}")
                else:
                    print(f"[DATA_GENERATOR] Warning: RAG API returned {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"[DATA_GENERATOR] Warning: Could not fetch RAG data: {e}")
        
    except Exception as e:
        error_msg = f"Data generation failed: {str(e)}"
        print(f"[DATA_GENERATOR] ERROR: {error_msg}")
        return {**state, "error": error_msg}
    
    return {
        **state,
        "structured_data": structured_data,
        "rag_insights": rag_insights
    }


def evaluator_node(state: WorkflowState) -> WorkflowState:
    """
    EVALUATOR NODE: Scores dashboard quality using rubric criteria.
    
    Responsibilities:
    - Generate dashboard using structured pipeline
    - Evaluate dashboard against rubric (factual, schema, provenance, hallucination, readability)
    - Calculate overall score (1-10)
    - Store dashboard in state
    
    Returns:
        Updated state with dashboard and dashboard_score
    """
    company_id = state.get("company_id", "")
    run_id = state.get("run_id", "")
    structured_data = state.get("structured_data")
    
    # Log node execution
    _workflow_node_order.append("evaluator")
    _workflow_trace_events.append({
        "event_type": "NODE_EXECUTED",
        "timestamp": datetime.now().isoformat(),
        "node": "evaluator",
        "run_id": run_id,
        "company_id": company_id
    })
    
    if not company_id:
        return {**state, "error": "company_id is required for evaluation"}
    
    dashboard = None
    dashboard_score = None
    
    try:
        # Generate dashboard using structured pipeline
        response = requests.post(
            f"{API_BASE}/dashboard/structured",
            json={"company_id": company_id},
            timeout=120
        )
        
        if response.status_code == 200:
            dashboard = response.json().get("dashboard", "")
            print(f"[EVALUATOR] Generated dashboard for {company_id} ({len(dashboard)} chars)")
            
            # Score dashboard using rubric
            dashboard_score = score_dashboard(dashboard)
            print(f"[EVALUATOR] Dashboard score: {dashboard_score}/10")
        else:
            error_msg = f"Dashboard generation failed: {response.status_code} - {response.text}"
            print(f"[EVALUATOR] ERROR: {error_msg}")
            return {**state, "error": error_msg}
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Evaluation failed: {str(e)}"
        print(f"[EVALUATOR] ERROR: {error_msg}")
        return {**state, "error": error_msg}
    
    return {
        **state,
        "dashboard": dashboard,
        "dashboard_score": dashboard_score
    }


def risk_detector_node(state: WorkflowState) -> WorkflowState:
    """
    RISK DETECTOR NODE: Checks for red flags and risk signals with keyword-based detection.
    
    Responsibilities:
    - Analyze structured_data for risk indicators (layoffs, scandals, etc.)
    - Analyze rag_insights for risk keywords in retrieved content
    - Check dashboard content for concerning patterns
    - Classify risk severity (high/medium/low)
    - Set requires_hitl flag if high-severity risks found
    - Compile comprehensive risk_signals list with severity levels
    
    Risk Keywords Checked:
    - High severity: "layoff", "breach", "scandal", "lawsuit", "bankruptcy"
    - Medium severity: "investigation", "regulatory", "churn", "turnover"
    - Low severity: "concern", "risk", "challenge"
    
    Returns:
        Updated state with risk_signals and requires_hitl flag
    """
    company_id = state.get("company_id", "")
    run_id = state.get("run_id", "")
    structured_data = state.get("structured_data", {})
    rag_insights = state.get("rag_insights", [])
    dashboard = state.get("dashboard", "")
    
    # Log node execution
    _workflow_node_order.append("risk_detector")
    _workflow_trace_events.append({
        "event_type": "NODE_EXECUTED",
        "timestamp": datetime.now().isoformat(),
        "node": "risk_detector",
        "run_id": run_id,
        "company_id": company_id
    })
    
    risk_signals = []
    requires_hitl = False
    
    # Define risk keyword categories with severity levels
    HIGH_SEVERITY_KEYWORDS = [
        "layoff", "layoffs", "reduction in force", "rif",
        "breach", "data breach", "security breach", "cyber attack",
        "scandal", "fraud", "embezzlement", "corruption",
        "lawsuit", "litigation", "legal action", "class action",
        "bankruptcy", "chapter 11", "insolvency", "liquidation"
    ]
    
    MEDIUM_SEVERITY_KEYWORDS = [
        "investigation", "sec investigation", "regulatory investigation",
        "regulatory action", "compliance violation", "fined",
        "churn", "customer churn", "high churn",
        "turnover", "executive turnover", "leadership turnover",
        "restructuring", "downsizing", "cost cutting"
    ]
    
    LOW_SEVERITY_KEYWORDS = [
        "concern", "risk", "challenge", "uncertainty",
        "volatility", "market risk", "competition"
    ]
    
    try:
        # ========================================================================
        # 1. CHECK STRUCTURED DATA FOR RISK INDICATORS
        # ========================================================================
        if structured_data:
            snapshots = structured_data.get("snapshots", [])
            if snapshots:
                snapshot = snapshots[0]  # Use most recent snapshot
                
                # Check for layoffs (HIGH SEVERITY)
                if snapshot.get("layoffs_mentioned", False):
                    layoff_count = snapshot.get("layoffs_count", 0)
                    layoff_pct = snapshot.get("layoffs_percentage", 0)
                    severity = "high" if layoff_pct > 10 else "medium"
                    risk_signals.append({
                        "type": "layoffs",
                        "severity": severity,
                        "details": f"Layoffs mentioned: {layoff_count} employees ({layoff_pct}%)",
                        "source": "structured_data",
                        "keyword_matched": "layoff"
                    })
                    if severity == "high":
                        requires_hitl = True
                
                # Check for negative signals and scan for keywords
                negative_signals = snapshot.get("negative_signals", [])
                if negative_signals:
                    # Scan each negative signal for high-severity keywords
                    for neg_signal in negative_signals:
                        neg_lower = str(neg_signal).lower()
                        # Check for high-severity keywords
                        matched_high = [kw for kw in HIGH_SEVERITY_KEYWORDS if kw in neg_lower]
                        if matched_high:
                            risk_signals.append({
                                "type": "negative_news_high_severity",
                                "severity": "high",
                                "details": f"Negative signal with high-severity keyword: {neg_signal}",
                                "keywords": matched_high,
                                "source": "structured_data"
                            })
                            requires_hitl = True
                    
                    # Overall negative signals count
                    if len(negative_signals) >= 3:
                        risk_signals.append({
                            "type": "multiple_negative_signals",
                            "severity": "medium",
                            "details": f"{len(negative_signals)} negative signals detected",
                            "signals": negative_signals[:5],  # Top 5
                            "source": "structured_data"
                        })
                
                # Check for high risk score (HIGH SEVERITY)
                risk_score = snapshot.get("risk_score", 0)
                if risk_score and risk_score >= 70:
                    risk_signals.append({
                        "type": "high_risk_score",
                        "severity": "high",
                        "details": f"Risk score: {risk_score}/100 (threshold: 70)",
                        "source": "structured_data"
                    })
                    requires_hitl = True
                
                # Check for leadership instability
                leadership_stability = snapshot.get("leadership_stability", "")
                if leadership_stability and "turnover" in leadership_stability.lower():
                    risk_signals.append({
                        "type": "leadership_instability",
                        "severity": "medium",
                        "details": f"Leadership stability: {leadership_stability}",
                        "source": "structured_data",
                        "keyword_matched": "turnover"
                    })
        
        # ========================================================================
        # 2. CHECK RAG INSIGHTS FOR RISK KEYWORDS
        # ========================================================================
        # Analyze retrieved chunks from vector DB for risk indicators
        if rag_insights:
            for insight in rag_insights:
                # Get text content from RAG insight
                rag_text = ""
                if isinstance(insight, dict):
                    rag_text = insight.get("dashboard_preview", "") or insight.get("content", "") or str(insight)
                else:
                    rag_text = str(insight)
                
                rag_lower = rag_text.lower()
                
                # Check for HIGH severity keywords in RAG content
                matched_high = [kw for kw in HIGH_SEVERITY_KEYWORDS if kw in rag_lower]
                if matched_high:
                    risk_signals.append({
                        "type": "rag_high_severity_keyword",
                        "severity": "high",
                        "details": f"High-severity keyword found in RAG retrieved content",
                        "keywords": matched_high,
                        "source": "rag_insights",
                        "preview": rag_text[:200]  # First 200 chars for context
                    })
                    requires_hitl = True
                
                # Check for MEDIUM severity keywords
                matched_medium = [kw for kw in MEDIUM_SEVERITY_KEYWORDS if kw in rag_lower]
                if matched_medium:
                    risk_signals.append({
                        "type": "rag_medium_severity_keyword",
                        "severity": "medium",
                        "details": f"Medium-severity keyword found in RAG content",
                        "keywords": matched_medium,
                        "source": "rag_insights"
                    })
        
        # ========================================================================
        # 3. CHECK DASHBOARD CONTENT FOR RISK KEYWORDS
        # ========================================================================
        if dashboard:
            dashboard_lower = dashboard.lower()
            
            # Check for HIGH severity keywords in dashboard
            matched_high = [kw for kw in HIGH_SEVERITY_KEYWORDS if kw in dashboard_lower]
            if matched_high:
                risk_signals.append({
                    "type": "dashboard_high_severity_keyword",
                    "severity": "high",
                    "details": f"High-severity keyword found in generated dashboard",
                    "keywords": matched_high,
                    "source": "dashboard_content"
                })
                requires_hitl = True
            
            # Check for MEDIUM severity keywords
            matched_medium = [kw for kw in MEDIUM_SEVERITY_KEYWORDS if kw in dashboard_lower]
            if matched_medium:
                risk_signals.append({
                    "type": "dashboard_medium_severity_keyword",
                    "severity": "medium",
                    "details": f"Medium-severity keyword found in dashboard",
                    "keywords": matched_medium,
                    "source": "dashboard_content"
                })
        
        # ========================================================================
        # 4. FINAL DECISION LOGIC
        # ========================================================================
        # Count high-severity risks
        high_severity_count = sum(1 for signal in risk_signals if signal.get("severity") == "high")
        
        # Require HITL if:
        # - Any high-severity risk found, OR
        # - 3+ medium-severity risks found
        medium_severity_count = sum(1 for signal in risk_signals if signal.get("severity") == "medium")
        
        if high_severity_count > 0:
            requires_hitl = True
        elif medium_severity_count >= 3:
            requires_hitl = True
            risk_signals.append({
                "type": "multiple_medium_risks",
                "severity": "medium",
                "details": f"Multiple medium-severity risks detected ({medium_severity_count}) - elevating to HITL",
                "source": "risk_aggregation"
            })
        
        # Log results
        print(f"[RISK_DETECTOR] Detected {len(risk_signals)} risk signals for {company_id}")
        print(f"[RISK_DETECTOR]   - High severity: {high_severity_count}")
        print(f"[RISK_DETECTOR]   - Medium severity: {medium_severity_count}")
        print(f"[RISK_DETECTOR]   - Low severity: {len(risk_signals) - high_severity_count - medium_severity_count}")
        
        if requires_hitl:
            print(f"[RISK_DETECTOR] [WARNING] HITL approval REQUIRED due to risk signals")
        else:
            print(f"[RISK_DETECTOR] [OK] No high-severity risks - safe to proceed")
        
    except Exception as e:
        error_msg = f"Risk detection failed: {str(e)}"
        print(f"[RISK_DETECTOR] ERROR: {error_msg}")
        return {**state, "error": error_msg}
    
    return {
        **state,
        "risk_signals": risk_signals,
        "requires_hitl": requires_hitl
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def score_dashboard(dashboard: str) -> float:
    """
    Score dashboard quality using rubric (1-10 scale).
    
    Simplified scoring based on:
    - Schema adherence (8 sections): 0-2 points
    - "Not disclosed." usage: 0-2 points
    - Word count (readability): 0-1 point
    - Provenance indicators: 0-2 points
    - Factual correctness proxy: 0-3 points
    """
    if not dashboard:
        return 0.0
    
    score = 0.0
    
    # Check for 8 required sections (2 points)
    required_sections = [
        "## Company Overview",
        "## Business Model and GTM",
        "## Funding & Investor Profile",
        "## Growth Momentum",
        "## Visibility & Market Sentiment",
        "## Risks and Challenges",
        "## Outlook",
        "## Disclosure Gaps"
    ]
    sections_found = sum(1 for section in required_sections if section in dashboard)
    if sections_found == 8:
        score += 2.0
    elif sections_found >= 6:
        score += 1.0
    
    # Check for "Not disclosed." usage (2 points)
    not_disclosed_count = dashboard.lower().count("not disclosed")
    if not_disclosed_count >= 3:
        score += 2.0
    elif not_disclosed_count >= 1:
        score += 1.0
    
    # Word count check (1 point)
    word_count = len(dashboard.split())
    if 300 <= word_count <= 1200:
        score += 1.0
    
    # Provenance indicators (2 points)
    provenance_keywords = ["source", "according to", "based on", "from"]
    has_provenance = any(kw in dashboard.lower() for kw in provenance_keywords)
    if has_provenance:
        score += 2.0
    
    # Factual correctness proxy (3 points)
    # If has provenance and uses "Not disclosed", likely more factual
    if has_provenance and not_disclosed_count >= 1:
        score += 3.0
    elif has_provenance or not_disclosed_count >= 1:
        score += 2.0
    elif sections_found >= 6:
        score += 1.0
    
    return min(10.0, score)


def should_require_hitl(state: WorkflowState) -> Literal["hitl_required", "safe_to_proceed"]:
    """
    CONDITIONAL ROUTING FUNCTION: Determines workflow path based on risk assessment.
    
    Decision Logic:
    - Checks requires_hitl flag set by risk_detector_node
    - Returns "hitl_required" if high-severity risks detected
    - Returns "safe_to_proceed" if no high-severity risks or risks are manageable
    
    This function is used by LangGraph's add_conditional_edges() to route the workflow:
    - High risk path: risk_detector → hitl_node → END
    - Safe path: risk_detector → END
    
    Args:
        state: Current workflow state with risk_signals and requires_hitl flag
    
    Returns:
        "hitl_required" if human approval needed, "safe_to_proceed" otherwise
    """
    requires_hitl = state.get("requires_hitl", False)
    risk_signals = state.get("risk_signals", [])
    company_id = state.get("company_id", "unknown")
    
    # Log routing decision
    if requires_hitl:
        high_risks = [s for s in risk_signals if s.get("severity") == "high"]
        print(f"\n[ROUTING] [WARNING] Routing {company_id} to HITL path")
        print(f"[ROUTING]   Reason: {len(high_risks)} high-severity risk(s) detected")
        return "hitl_required"
    else:
        print(f"\n[ROUTING] [OK] Routing {company_id} to safe completion path")
        print(f"[ROUTING]   No high-severity risks - proceeding to END")
        return "safe_to_proceed"


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def hitl_approval_node(state: WorkflowState) -> WorkflowState:
    """
    HITL (Human-In-The-Loop) APPROVAL NODE: Handles high-risk cases requiring human review.
    
    Responsibilities:
    - Pause workflow execution
    - Display risk summary to human reviewer
    - Wait for approval/rejection (CLI or HTTP)
    - Store approval decision with metadata
    - Resume workflow based on decision
    
    Supports two methods:
    - CLI: Interactive terminal prompt (default)
    - HTTP: REST endpoint for approval UI
    
    Returns:
        Updated state with hitl_approved flag, reviewer, timestamp, and notes
    """
    company_id = state.get("company_id", "")
    run_id = state.get("run_id", "")
    risk_signals = state.get("risk_signals", [])
    dashboard = state.get("dashboard", "")
    
    # Log node execution
    _workflow_node_order.append("hitl_approval")
    _workflow_trace_events.append({
        "event_type": "NODE_EXECUTED",
        "timestamp": datetime.now().isoformat(),
        "node": "hitl_approval",
        "run_id": run_id,
        "company_id": company_id
    })
    
    # Determine HITL method (CLI or HTTP)
    hitl_method = os.getenv("HITL_METHOD", "cli").lower()
    
    # Get dashboard preview (first 500 chars)
    dashboard_preview = dashboard[:500] if dashboard else None
    
    # Pause workflow and request approval
    print(f"\n{'='*60}")
    print(f"[HITL] PAUSING WORKFLOW - Waiting for human approval")
    print(f"{'='*60}")
    
    try:
        # Set up trace logger for HITL events
        from src.lab18.hitl_handler import set_trace_logger
        
        def log_trace(event):
            _workflow_trace_events.append(event)
        
        set_trace_logger(log_trace)
        
        # Call HITL handler (pauses here until decision is made)
        decision = pause_for_approval(
            run_id=run_id,
            company_id=company_id,
            risk_signals=risk_signals,
            dashboard_preview=dashboard_preview,
            method=hitl_method
        )
        
        hitl_approved = decision.get("approved", False)
        reviewer = decision.get("reviewer", "unknown")
        timestamp = decision.get("timestamp", datetime.now().isoformat())
        notes = decision.get("notes")
        
        print(f"\n{'='*60}")
        print(f"[HITL] DECISION RECEIVED")
        print(f"{'='*60}")
        if hitl_approved:
            print(f"[HITL] ✅ APPROVED by {reviewer}")
        else:
            print(f"[HITL] ❌ REJECTED by {reviewer}")
        if notes:
            print(f"[HITL] Notes: {notes}")
        print(f"[HITL] Timestamp: {timestamp}")
        print(f"{'='*60}\n")
        
        # Update state with approval decision
        return {
            **state,
            "hitl_approved": hitl_approved,
            "hitl_reviewer": reviewer,
            "hitl_timestamp": timestamp,
            "hitl_notes": notes
        }
        
    except Exception as e:
        # Error in HITL handler - default to rejection for safety
        error_msg = f"HITL approval failed: {str(e)}"
        print(f"[HITL] ERROR: {error_msg}")
        print(f"[HITL] Defaulting to REJECTED for safety")
        
        return {
            **state,
            "hitl_approved": False,
            "hitl_reviewer": "system",
            "hitl_timestamp": datetime.now().isoformat(),
            "hitl_notes": error_msg,
            "error": error_msg
        }


def create_due_diligence_graph() -> StateGraph:
    """
    Creates and configures the LangGraph StateGraph for due diligence workflow.
    
    Graph Structure:
        START → planner → data_generator → evaluator → risk_detector → [HITL or END]
    
    Conditional Routing:
        - High Risk Path: risk_detector → hitl_approval → END
        - Safe Path: risk_detector → END
    
    Decision Logic:
        - risk_detector analyzes data and sets requires_hitl flag
        - should_require_hitl() routing function checks the flag
        - Routes to HITL if high-severity risks found
        - Routes to END if safe to proceed
    
    Returns:
        Compiled StateGraph ready for execution
    """
    if not LANGGRAPH_AVAILABLE:
        raise ImportError("langgraph is not installed. Install it with: pip install langgraph")
    
    # Create graph
    workflow = StateGraph(WorkflowState)
    
    # ========================================================================
    # ADD NODES
    # ========================================================================
    workflow.add_node("planner", planner_node)
    workflow.add_node("data_generator", data_generator_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("risk_detector", risk_detector_node)
    workflow.add_node("hitl_approval", hitl_approval_node)
    
    # ========================================================================
    # DEFINE LINEAR EDGES (Sequential flow)
    # ========================================================================
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "data_generator")
    workflow.add_edge("data_generator", "evaluator")
    workflow.add_edge("evaluator", "risk_detector")
    
    # ========================================================================
    # CONDITIONAL ROUTING FROM RISK_DETECTOR
    # ========================================================================
    # This is where the branching happens based on risk assessment
    workflow.add_conditional_edges(
        "risk_detector",  # Source node
        should_require_hitl,  # Routing function that returns "hitl_required" or "safe_to_proceed"
        {
            "hitl_required": "hitl_approval",  # High risk path: go to HITL node
            "safe_to_proceed": END  # Safe path: end workflow
        }
    )
    
    # ========================================================================
    # HITL APPROVAL NODE EDGES
    # ========================================================================
    # After HITL approval, workflow ends
    workflow.add_edge("hitl_approval", END)
    
    return workflow


# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def run_due_diligence_workflow(
    company_id: str,
    run_id: Optional[str] = None,
    checkpoint: Optional[MemorySaver] = None
) -> WorkflowState:
    """
    Execute the complete due diligence workflow for a company.
    
    Args:
        company_id: Company identifier (e.g., "anthropic")
        run_id: Optional run identifier (auto-generated if not provided)
        checkpoint: Optional checkpoint for state persistence
    
    Returns:
        Final workflow state with all results
    """
    # Create graph
    workflow = create_due_diligence_graph()
    
    # Compile with optional checkpoint
    if checkpoint:
        app = workflow.compile(checkpointer=checkpoint)
    else:
        app = workflow.compile()
    
    # Initial state
    initial_state: WorkflowState = {
        "company_id": company_id,
        "run_id": run_id or f"{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "structured_data": None,
        "rag_insights": None,
        "risk_signals": None,
        "dashboard": None,
        "dashboard_score": None,
        "requires_hitl": False,
        "hitl_approved": False,
        "hitl_reviewer": None,
        "hitl_timestamp": None,
        "hitl_notes": None,
        "execution_plan": None,
        "error": None
    }
    
    # Reset global trace state for this run
    global _workflow_trace_events, _workflow_node_order
    _workflow_trace_events.clear()
    _workflow_node_order.clear()
    
    # Execute workflow
    print(f"\n{'='*60}")
    print(f"Starting Due Diligence Workflow for: {company_id}")
    print(f"Run ID: {initial_state['run_id']}")
    print(f"{'='*60}\n")
    
    # Log workflow start
    _workflow_trace_events.append({
        "event_type": "WORKFLOW_START",
        "timestamp": datetime.now().isoformat(),
        "run_id": initial_state['run_id'],
        "company_id": company_id
    })
    
    try:
        if checkpoint:
            # Use checkpoint for stateful execution
            config = {"configurable": {"thread_id": initial_state["run_id"]}}
            final_state = app.invoke(initial_state, config)
        else:
            final_state = app.invoke(initial_state)
        
        print(f"\n{'='*60}")
        print(f"Workflow completed for: {company_id}")
        print(f"Dashboard Score: {final_state.get('dashboard_score', 'N/A')}/10")
        print(f"Risk Signals: {len(final_state.get('risk_signals', []))}")
        print(f"Requires HITL: {final_state.get('requires_hitl', False)}")
        
        # Print branch taken (CHECKPOINT REQUIREMENT)
        if final_state.get('requires_hitl', False):
            print(f"[BRANCH] HIGH-RISK PATH -> HITL Approval -> END")
        else:
            print(f"[BRANCH] SAFE PATH -> END (Direct)")
        
        # Save dashboard to file
        dashboard = final_state.get('dashboard')
        if dashboard:
            try:
                output_dir = project_root / "data" / "workflow_dashboards"
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Create filename with run_id and timestamp
                run_id = final_state.get('run_id', 'unknown')
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{company_id}_{run_id}_{timestamp}.md"
                output_path = output_dir / filename
                
                # Prepare dashboard content with metadata
                dashboard_content = f"""# Due Diligence Dashboard: {company_id.upper()}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Run ID:** {run_id}  
**Dashboard Score:** {final_state.get('dashboard_score', 'N/A')}/10  
**Risk Signals:** {len(final_state.get('risk_signals', []))}  
**Requires HITL:** {final_state.get('requires_hitl', False)}  
**HITL Approved:** {final_state.get('hitl_approved', False)}  
**HITL Reviewer:** {final_state.get('hitl_reviewer', 'N/A')}  
**HITL Timestamp:** {final_state.get('hitl_timestamp', 'N/A')}  
**HITL Notes:** {final_state.get('hitl_notes', 'None')}  
**Branch Taken:** {'HIGH-RISK PATH -> HITL Approval -> END' if final_state.get('requires_hitl', False) else 'SAFE PATH -> END (Direct)'}

---

## Risk Signals

"""
                
                # Add risk signals if any
                risk_signals = final_state.get('risk_signals', [])
                if risk_signals:
                    for signal in risk_signals:
                        severity = signal.get('severity', 'unknown').upper()
                        signal_type = signal.get('type', 'unknown')
                        details = signal.get('details', 'No details')
                        dashboard_content += f"- **[{severity}]** {signal_type}: {details}\n"
                else:
                    dashboard_content += "No risk signals detected.\n"
                
                dashboard_content += f"\n---\n\n{dashboard}"
                
                # Write to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(dashboard_content)
                
                print(f"[OUTPUT] Dashboard saved to: {output_path}")
                print(f"[OUTPUT] File size: {len(dashboard_content)} bytes")
            except Exception as e:
                print(f"[ERROR] Failed to save dashboard: {e}")
        else:
            print(f"[WARNING] No dashboard to save (dashboard is None or empty)")
        
        print(f"{'='*60}\n")
        
        # Save execution trace
        trace_data = {
            "run_id": initial_state['run_id'],
            "company_id": company_id,
            "start_time": _workflow_trace_events[0]['timestamp'] if _workflow_trace_events else datetime.now().isoformat(),
            "end_time": datetime.now().isoformat(),
            "node_execution_order": _workflow_node_order.copy(),
            "events": _workflow_trace_events.copy(),
            "final_state": {
                "requires_hitl": final_state.get('requires_hitl', False),
                "hitl_approved": final_state.get('hitl_approved', False),
                "hitl_reviewer": final_state.get('hitl_reviewer'),
                "dashboard_score": final_state.get('dashboard_score'),
                "risk_signals_count": len(final_state.get('risk_signals', []))
            }
        }
        
        # Save trace to file
        trace_dir = project_root / "logs" / "workflow_traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_file = trace_dir / f"workflow_trace_{initial_state['run_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(trace_file, 'w', encoding='utf-8') as f:
            json.dump(trace_data, f, indent=2)
        
        print(f"[TRACE] Execution trace saved to: {trace_file}")
        
        return final_state
        
    except Exception as e:
        error_msg = f"Workflow execution failed: {str(e)}"
        print(f"\n[ERROR] {error_msg}\n")
        return {**initial_state, "error": error_msg}


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run due diligence workflow for a company",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python due_diligence_graph.py anthropic
  python due_diligence_graph.py --company anthropic --verbose
  python due_diligence_graph.py --company anthropic --run-id custom_123
        """
    )
    
    parser.add_argument(
        "company_id",
        nargs="?",
        help="Company ID to process (e.g., 'anthropic', 'abridge')"
    )
    parser.add_argument(
        "--company",
        dest="company_id_flag",
        help="Company ID to process (alternative to positional argument)"
    )
    parser.add_argument(
        "--run-id",
        dest="run_id",
        help="Custom run ID for tracking (auto-generated if not provided)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed logging"
    )
    
    args = parser.parse_args()
    
    # Determine company_id from positional or flag
    company_id = args.company_id or args.company_id_flag
    
    if not company_id:
        parser.print_help()
        print("\n[ERROR] Company ID is required. Use positional argument or --company flag.")
        sys.exit(1)
    
    # Set verbose mode
    verbose = args.verbose
    
    if verbose:
        print("="*60)
        print("VERBOSE MODE ENABLED")
        print("="*60)
        print(f"Company ID: {company_id}")
        print(f"Run ID: {args.run_id or 'auto-generated'}")
        print(f"API Base URL: {API_BASE}")
        print("="*60 + "\n")
    
    # Run workflow
    try:
        result = run_due_diligence_workflow(company_id, args.run_id)
        
        # Print summary
        print("\n" + "="*60)
        print("WORKFLOW RESULTS SUMMARY")
        print("="*60)
        print(f"Company: {result.get('company_id')}")
        print(f"Run ID: {result.get('run_id')}")
        print(f"Dashboard Score: {result.get('dashboard_score', 'N/A')}/10")
        risk_signals = result.get('risk_signals', [])
        print(f"Risk Signals: {len(risk_signals) if risk_signals else 0}")
        
        if result.get('risk_signals'):
            print("\nRisk Signals Detected:")
            for signal in result.get('risk_signals', []):
                severity = signal.get('severity', 'unknown').upper()
                signal_type = signal.get('type', 'unknown')
                details = signal.get('details', 'No details')
                print(f"  - [{severity}] {signal_type}: {details}")
                
                if verbose and signal.get('keywords'):
                    print(f"      Keywords: {', '.join(signal.get('keywords', []))}")
                if verbose and signal.get('source'):
                    print(f"      Source: {signal.get('source')}")
        
        print(f"\nRequires HITL: {result.get('requires_hitl', False)}")
        
        if result.get('requires_hitl'):
            print(f"HITL Approved: {result.get('hitl_approved', False)}")
            print(f"HITL Reviewer: {result.get('hitl_reviewer', 'N/A')}")
            print(f"HITL Timestamp: {result.get('hitl_timestamp', 'N/A')}")
            if result.get('hitl_notes'):
                print(f"HITL Notes: {result.get('hitl_notes')}")
        
        if verbose:
            print("\n" + "="*60)
            print("VERBOSE DETAILS")
            print("="*60)
            print(f"Execution Plan: {result.get('execution_plan')}")
            print(f"Structured Data Loaded: {result.get('structured_data') is not None}")
            print(f"RAG Insights Count: {len(result.get('rag_insights', []))}")
            print(f"Dashboard Length: {len(result.get('dashboard', ''))} characters")
            if result.get('dashboard'):
                print(f"Dashboard Preview (first 200 chars):")
                print(f"  {result.get('dashboard', '')[:200]}...")
        
        if result.get('error'):
            print(f"\n[ERROR] {result.get('error')}")
            sys.exit(1)
        
        print("="*60)
        
        # Exit code based on workflow result
        if result.get('requires_hitl') and not result.get('hitl_approved'):
            sys.exit(2)  # HITL required but not approved
        elif result.get('error'):
            sys.exit(1)  # Error occurred
        else:
            sys.exit(0)  # Success
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Workflow cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[FATAL ERROR] {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


# ============================================================================
# STATE FLOW EXAMPLES AND DOCUMENTATION
# ============================================================================
"""
STATE FLOW EXAMPLES
===================

EXAMPLE 1: SAFE PATH (No High-Severity Risks)
----------------------------------------------
State Flow:
1. START → planner → data_generator → evaluator → risk_detector
2. risk_detector sets: requires_hitl = False
3. should_require_hitl() returns: "safe_to_proceed"
4. Route: risk_detector → END

Final State:
{
    "company_id": "anthropic",
    "run_id": "anthropic_20250114_143022_abc123",
    "structured_data": {...},
    "rag_insights": [...],
    "dashboard": "## Company Overview\n...",
    "dashboard_score": 8.5,
    "risk_signals": [
        {"type": "leadership_instability", "severity": "medium", ...}
    ],
    "requires_hitl": False
}


EXAMPLE 2: HIGH RISK PATH (HITL Required)
------------------------------------------
State Flow:
1. START → planner → data_generator → evaluator → risk_detector
2. risk_detector sets: requires_hitl = True (high-severity risk found)
3. should_require_hitl() returns: "hitl_required"
4. Route: risk_detector → hitl_approval → END

Final State:
{
    "company_id": "anthropic",
    "run_id": "anthropic_20250114_143022_abc123",
    "structured_data": {...},
    "rag_insights": [...],
    "dashboard": "## Company Overview\n...",
    "dashboard_score": 8.5,
    "risk_signals": [
        {
            "type": "layoffs",
            "severity": "high",
            "details": "Layoffs mentioned: 500 employees (15%)",
            "source": "structured_data",
            "keyword_matched": "layoff"
        },
        {
            "type": "rag_high_severity_keyword",
            "severity": "high",
            "keywords": ["breach", "data breach"],
            "source": "rag_insights"
        }
    ],
    "requires_hitl": True,
    "hitl_approved": True
}


DECISION LOGIC SUMMARY
======================

Risk Detection:
- Scans structured_data, rag_insights, and dashboard for keywords
- High-severity keywords: "layoff", "breach", "scandal", "lawsuit", "bankruptcy"
- Medium-severity keywords: "investigation", "regulatory", "churn", "turnover"
- Low-severity keywords: "concern", "risk", "challenge"

HITL Trigger Conditions:
1. Any high-severity risk found → requires_hitl = True
2. 3+ medium-severity risks found → requires_hitl = True
3. High risk_score (>=70) in structured_data → requires_hitl = True
4. Layoffs >10% of workforce → requires_hitl = True

Routing:
- requires_hitl=True → "hitl_required" → hitl_approval_node → END
- requires_hitl=False → "safe_to_proceed" → END
"""

