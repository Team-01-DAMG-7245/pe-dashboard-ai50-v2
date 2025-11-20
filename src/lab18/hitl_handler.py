"""
Lab 18: Human-in-the-Loop (HITL) Approval Handler

Provides both CLI and HTTP interfaces for human approval of high-risk dashboards.
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from pydantic import BaseModel, Field
except ImportError:
    # Fallback if pydantic not available
    BaseModel = object
    Field = lambda **kwargs: None

try:
    import requests
except ImportError:
    requests = None

# In-memory store for pending approvals (in production, use a database)
_pending_approvals: Dict[str, Dict[str, Any]] = {}

# Trace logger callback (set by workflow)
_trace_logger: Optional[callable] = None


def set_trace_logger(logger_func: callable):
    """Set the trace logger function to be called for HITL events"""
    global _trace_logger
    _trace_logger = logger_func


def log_hitl_event(event_type: str, data: Dict[str, Any]):
    """Log HITL event to trace if logger is available"""
    if _trace_logger:
        _trace_logger({
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            **data
        })


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class HITLRequest(BaseModel):
    """Request model for HITL approval"""
    run_id: str
    company_id: str
    risk_signals: list
    dashboard_preview: Optional[str] = None
    reviewer: Optional[str] = None
    notes: Optional[str] = None


class HITLResponse(BaseModel):
    """Response model for HITL approval"""
    run_id: str
    approved: bool
    reviewer: str
    timestamp: str
    notes: Optional[str] = None


class HITLDecision(BaseModel):
    """Decision model for HITL approval"""
    approved: bool = Field(description="Whether the dashboard is approved")
    reviewer: str = Field(description="Name/ID of the reviewer")
    notes: Optional[str] = Field(None, description="Optional notes from reviewer")


# ============================================================================
# CLI HITL HANDLER
# ============================================================================

def pause_for_approval_cli(
    run_id: str,
    company_id: str,
    risk_signals: list,
    dashboard_preview: Optional[str] = None
) -> Dict[str, Any]:
    """
    CLI-based HITL approval handler.
    
    Pauses workflow execution and prompts user for approval in the terminal.
    
    Args:
        run_id: Unique workflow run identifier
        company_id: Company being reviewed
        risk_signals: List of detected risk signals
        dashboard_preview: Optional preview of dashboard content (first 500 chars)
    
    Returns:
        Dictionary with approval decision:
        {
            "approved": bool,
            "reviewer": str,
            "timestamp": str,
            "notes": Optional[str]
        }
    """
    print(f"\n{'='*70}")
    print(f"HUMAN-IN-THE-LOOP (HITL) APPROVAL REQUIRED")
    print(f"{'='*70}")
    print(f"Company: {company_id.upper()}")
    print(f"Run ID: {run_id}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n{'='*70}")
    
    # Display risk signals
    print(f"\n⚠️  RISK SIGNALS DETECTED ({len(risk_signals)}):")
    print(f"{'-'*70}")
    
    high_risks = [s for s in risk_signals if s.get("severity") == "high"]
    medium_risks = [s for s in risk_signals if s.get("severity") == "medium"]
    low_risks = [s for s in risk_signals if s.get("severity") == "low"]
    
    if high_risks:
        print(f"\n🔴 HIGH SEVERITY ({len(high_risks)}):")
        for i, risk in enumerate(high_risks, 1):
            print(f"  {i}. [{risk.get('type', 'unknown')}]")
            print(f"     Details: {risk.get('details', 'No details')}")
            if risk.get('keywords'):
                print(f"     Keywords: {', '.join(risk.get('keywords', []))}")
            if risk.get('source'):
                print(f"     Source: {risk.get('source')}")
    
    if medium_risks:
        print(f"\n🟡 MEDIUM SEVERITY ({len(medium_risks)}):")
        for i, risk in enumerate(medium_risks, 1):
            print(f"  {i}. [{risk.get('type', 'unknown')}]")
            print(f"     Details: {risk.get('details', 'No details')}")
    
    if low_risks:
        print(f"\n🟢 LOW SEVERITY ({len(low_risks)}):")
        for i, risk in enumerate(low_risks, 1):
            print(f"  {i}. [{risk.get('type', 'unknown')}]")
    
    # Display dashboard preview if available
    if dashboard_preview:
        print(f"\n{'='*70}")
        print(f"DASHBOARD PREVIEW (first 500 characters):")
        print(f"{'-'*70}")
        print(dashboard_preview[:500])
        if len(dashboard_preview) > 500:
            print(f"\n... ({len(dashboard_preview) - 500} more characters)")
    
    # Log HITL triggered event
    log_hitl_event("HITL_TRIGGERED", {
        "run_id": run_id,
        "company_id": company_id,
        "risk_signals_count": len(risk_signals),
        "high_severity_count": len([s for s in risk_signals if s.get("severity") == "high"])
    })
    
    # Prompt for approval
    print(f"\n{'='*70}")
    print(f"APPROVAL DECISION")
    print(f"{'='*70}")
    print(f"\nOptions:")
    print(f"  - Type 'yes' or 'y' to APPROVE and proceed")
    print(f"  - Type 'no' or 'n' to REJECT and terminate")
    print(f"  - Type 'notes' to add notes before deciding")
    print(f"\nYour decision: ", end="", flush=True)
    
    # Log HITL waiting event
    log_hitl_event("HITL_WAITING", {
        "run_id": run_id,
        "company_id": company_id
    })
    
    try:
        user_input = input().strip().lower()
        
        notes = None
        
        # Handle notes option
        if user_input == 'notes':
            print(f"\nEnter notes (press Enter when done):")
            notes = input().strip()
            if not notes:
                notes = None
            print(f"\nDecision (yes/no): ", end="", flush=True)
            user_input = input().strip().lower()
        
        # Determine approval
        approved = user_input in ['yes', 'y', 'approve', 'a']
        
        # Get reviewer name (optional)
        reviewer = os.getenv("USER", os.getenv("USERNAME", "cli_user"))
        
        decision = {
            "approved": approved,
            "reviewer": reviewer,
            "timestamp": datetime.now().isoformat(),
            "notes": notes
        }
        
        # Display decision
        print(f"\n{'='*70}")
        if approved:
            print(f"✅ APPROVED by {reviewer}")
            log_hitl_event("HITL_APPROVED", {
                "run_id": run_id,
                "company_id": company_id,
                "reviewer": reviewer,
                "notes": notes
            })
        else:
            print(f"❌ REJECTED by {reviewer}")
            log_hitl_event("HITL_REJECTED", {
                "run_id": run_id,
                "company_id": company_id,
                "reviewer": reviewer,
                "notes": notes
            })
        if notes:
            print(f"Notes: {notes}")
        print(f"Timestamp: {decision['timestamp']}")
        print(f"{'='*70}\n")
        
        # Log workflow resuming
        log_hitl_event("WORKFLOW_RESUMED", {
            "run_id": run_id,
            "company_id": company_id,
            "approved": approved
        })
        
        return decision
        
    except (EOFError, KeyboardInterrupt):
        # Handle non-interactive environments
        print(f"\n[WARNING] No user input available - auto-rejecting for safety")
        return {
            "approved": False,
            "reviewer": "system",
            "timestamp": datetime.now().isoformat(),
            "notes": "Auto-rejected: No user input available"
        }


# ============================================================================
# HTTP HITL HANDLER (FastAPI)
# ============================================================================

def create_hitl_endpoints():
    """
    Create FastAPI endpoints for HTTP-based HITL approval.
    
    Returns:
        FastAPI router with HITL endpoints
    """
    try:
        from fastapi import APIRouter, HTTPException, BackgroundTasks
        from fastapi.responses import JSONResponse
    except ImportError:
        raise ImportError("FastAPI is required for HTTP HITL. Install with: pip install fastapi")
    
    router = APIRouter(prefix="/hitl", tags=["HITL"])
    
    @router.post("/request", response_model=Dict[str, Any])
    async def request_approval(request: HITLRequest):
        """
        Submit a dashboard for HITL approval.
        
        This pauses the workflow and stores the approval request.
        Workflow will wait until approval decision is made via /approve or /reject endpoints.
        """
        # Store pending approval
        _pending_approvals[request.run_id] = {
            "run_id": request.run_id,
            "company_id": request.company_id,
            "risk_signals": request.risk_signals,
            "dashboard_preview": request.dashboard_preview,
            "status": "pending",
            "requested_at": datetime.now().isoformat(),
            "reviewer": request.reviewer,
            "notes": request.notes
        }
        
        return {
            "status": "pending",
            "run_id": request.run_id,
            "message": f"HITL approval requested for {request.company_id}",
            "approval_url": f"/hitl/approve/{request.run_id}",
            "rejection_url": f"/hitl/reject/{request.run_id}",
            "check_url": f"/hitl/status/{request.run_id}"
        }
    
    @router.get("/status/{run_id}", response_model=Dict[str, Any])
    async def get_approval_status(run_id: str):
        """Check the status of a pending HITL approval"""
        if run_id not in _pending_approvals:
            raise HTTPException(status_code=404, detail=f"No pending approval found for run_id: {run_id}")
        
        approval = _pending_approvals[run_id]
        return {
            "run_id": run_id,
            "status": approval.get("status", "pending"),
            "company_id": approval.get("company_id"),
            "risk_signals": approval.get("risk_signals", []),
            "requested_at": approval.get("requested_at"),
            "decided_at": approval.get("decided_at"),
            "reviewer": approval.get("reviewer"),
            "approved": approval.get("approved"),
            "notes": approval.get("notes")
        }
    
    @router.post("/approve/{run_id}", response_model=HITLResponse)
    async def approve_dashboard(run_id: str, decision: HITLDecision):
        """Approve a pending dashboard"""
        if run_id not in _pending_approvals:
            raise HTTPException(status_code=404, detail=f"No pending approval found for run_id: {run_id}")
        
        approval = _pending_approvals[run_id]
        if approval.get("status") != "pending":
            raise HTTPException(status_code=400, detail=f"Approval for {run_id} is not pending")
        
        # Update approval
        approval["status"] = "approved"
        approval["approved"] = True
        approval["reviewer"] = decision.reviewer
        approval["decided_at"] = datetime.now().isoformat()
        approval["notes"] = decision.notes
        
        return HITLResponse(
            run_id=run_id,
            approved=True,
            reviewer=decision.reviewer,
            timestamp=approval["decided_at"],
            notes=decision.notes
        )
    
    @router.post("/reject/{run_id}", response_model=HITLResponse)
    async def reject_dashboard(run_id: str, decision: HITLDecision):
        """Reject a pending dashboard"""
        if run_id not in _pending_approvals:
            raise HTTPException(status_code=404, detail=f"No pending approval found for run_id: {run_id}")
        
        approval = _pending_approvals[run_id]
        if approval.get("status") != "pending":
            raise HTTPException(status_code=400, detail=f"Approval for {run_id} is not pending")
        
        # Update approval
        approval["status"] = "rejected"
        approval["approved"] = False
        approval["reviewer"] = decision.reviewer
        approval["decided_at"] = datetime.now().isoformat()
        approval["notes"] = decision.notes
        
        return HITLResponse(
            run_id=run_id,
            approved=False,
            reviewer=decision.reviewer,
            timestamp=approval["decided_at"],
            notes=decision.notes
        )
    
    @router.get("/pending", response_model=Dict[str, Any])
    async def list_pending_approvals():
        """List all pending HITL approvals"""
        pending = {
            run_id: {
                "run_id": run_id,
                "company_id": approval.get("company_id"),
                "risk_signals_count": len(approval.get("risk_signals", [])),
                "requested_at": approval.get("requested_at")
            }
            for run_id, approval in _pending_approvals.items()
            if approval.get("status") == "pending"
        }
        
        return {
            "pending_count": len(pending),
            "pending_approvals": pending
        }
    
    return router


def wait_for_http_approval(
    run_id: str,
    timeout: int = 300,
    check_interval: int = 2
) -> Dict[str, Any]:
    """
    Wait for HTTP-based HITL approval decision.
    
    Polls the approval status until a decision is made or timeout occurs.
    
    Args:
        run_id: Unique workflow run identifier
        timeout: Maximum time to wait in seconds (default: 5 minutes)
        check_interval: How often to check status in seconds (default: 2 seconds)
    
    Returns:
        Dictionary with approval decision or timeout error
    """
    if requests is None:
        raise ImportError("requests library is required for HTTP HITL. Install with: pip install requests")
    
    hitl_base_url = os.getenv("HITL_BASE_URL", "http://localhost:8003")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{hitl_base_url}/hitl/status/{run_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "approved":
                    return {
                        "approved": True,
                        "reviewer": data.get("reviewer", "unknown"),
                        "timestamp": data.get("decided_at", datetime.now().isoformat()),
                        "notes": data.get("notes")
                    }
                elif status == "rejected":
                    return {
                        "approved": False,
                        "reviewer": data.get("reviewer", "unknown"),
                        "timestamp": data.get("decided_at", datetime.now().isoformat()),
                        "notes": data.get("notes")
                    }
                # Still pending, continue waiting
                time.sleep(check_interval)
            elif response.status_code == 404:
                # Approval request not found, wait a bit and retry
                time.sleep(check_interval)
            else:
                raise Exception(f"Unexpected status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            # API might not be ready yet, wait and retry
            time.sleep(check_interval)
    
    # Timeout
    return {
        "approved": False,
        "reviewer": "system",
        "timestamp": datetime.now().isoformat(),
        "notes": f"Timeout: No decision received within {timeout} seconds"
    }


# ============================================================================
# UNIFIED HITL HANDLER
# ============================================================================

def pause_for_approval(
    run_id: str,
    company_id: str,
    risk_signals: list,
    dashboard_preview: Optional[str] = None,
    method: str = "cli"
) -> Dict[str, Any]:
    """
    Unified HITL approval handler supporting both CLI and HTTP methods.
    
    Args:
        run_id: Unique workflow run identifier
        company_id: Company being reviewed
        risk_signals: List of detected risk signals
        dashboard_preview: Optional preview of dashboard content
        method: "cli" for terminal prompt, "http" for HTTP endpoint
    
    Returns:
        Dictionary with approval decision:
        {
            "approved": bool,
            "reviewer": str,
            "timestamp": str,
            "notes": Optional[str]
        }
    """
    if method == "cli":
        return pause_for_approval_cli(run_id, company_id, risk_signals, dashboard_preview)
    elif method == "http":
        # Submit approval request via HTTP
        if requests is None:
            raise ImportError("requests library is required for HTTP HITL. Install with: pip install requests")
        
        hitl_base_url = os.getenv("HITL_BASE_URL", "http://localhost:8003")
        
        try:
            # Submit request
            response = requests.post(
                f"{hitl_base_url}/hitl/request",
                json={
                    "run_id": run_id,
                    "company_id": company_id,
                    "risk_signals": risk_signals,
                    "dashboard_preview": dashboard_preview
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"\n[HITL] Approval request submitted. Waiting for decision...")
                print(f"[HITL] Check status at: {hitl_base_url}/hitl/status/{run_id}")
                print(f"[HITL] Approve at: {hitl_base_url}/hitl/approve/{run_id}")
                print(f"[HITL] Reject at: {hitl_base_url}/hitl/reject/{run_id}\n")
                
                # Wait for decision
                return wait_for_http_approval(run_id)
            else:
                raise Exception(f"Failed to submit approval request: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"[HITL] HTTP method failed: {e}")
            print(f"[HITL] Falling back to CLI method...")
            return pause_for_approval_cli(run_id, company_id, risk_signals, dashboard_preview)
    else:
        raise ValueError(f"Unknown HITL method: {method}. Use 'cli' or 'http'")


# ============================================================================
# HITL SERVER (Standalone FastAPI app)
# ============================================================================

def create_hitl_server():
    """Create standalone FastAPI server for HITL approvals"""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        raise ImportError("FastAPI is required. Install with: pip install fastapi uvicorn")
    
    app = FastAPI(
        title="HITL Approval Server",
        description="Human-in-the-Loop approval service for Lab 18",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include HITL router
    hitl_router = create_hitl_endpoints()
    app.include_router(hitl_router)
    
    @app.get("/")
    async def root():
        return {
            "service": "HITL Approval Server",
            "version": "1.0.0",
            "endpoints": {
                "request_approval": "POST /hitl/request",
                "check_status": "GET /hitl/status/{run_id}",
                "approve": "POST /hitl/approve/{run_id}",
                "reject": "POST /hitl/reject/{run_id}",
                "list_pending": "GET /hitl/pending"
            }
        }
    
    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "HITL Approval Server"}
    
    return app


if __name__ == "__main__":
    import uvicorn
    app = create_hitl_server()
    port = int(os.getenv("HITL_PORT", "8003"))
    print(f"Starting HITL Approval Server on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

