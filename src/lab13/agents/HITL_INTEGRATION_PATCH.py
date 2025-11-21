"""
HITL Integration Patch for Lab 13 Supervisor Agent
Add this code to your supervisor_agent.py to enable Human-in-the-Loop approval
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class HITLIntegration:
    """Minimal HITL integration for supervisor agent"""
    
    def __init__(self, storage_dir: str = "data/hitl"):
        """
        Initialize HITL storage
        
        Args:
            storage_dir: Directory to store approval requests
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Risk keywords that trigger HITL
        self.high_risk_keywords = [
            "breach", "fraud", "bankrupt", "lawsuit", 
            "investigation", "scandal"
        ]
        self.medium_risk_keywords = [
            "layoff", "downsize", "restructure", 
            "terminate", "reduction"
        ]
    
    def detect_risks(self, analysis_results: Dict) -> Tuple[bool, str]:
        """
        Detect if HITL is needed based on analysis results
        
        Args:
            analysis_results: Results from agent analysis
            
        Returns:
            (needs_hitl, risk_type)
        """
        # Check risk_signals
        risk_signals = analysis_results.get("risk_signals", [])
        
        # If we logged any risk signals, that's a red flag
        if len(risk_signals) > 0:
            logger.warning(f"🚨 Found {len(risk_signals)} risk signals")
            return True, "risk_signals_detected"
        
        # Check payload for keywords (if available)
        payload = analysis_results.get("payload")
        if payload:
            # Convert payload to string for keyword search
            payload_str = json.dumps(payload.model_dump() if hasattr(payload, 'model_dump') else str(payload)).lower()
            
            # Check for high-risk keywords
            for keyword in self.high_risk_keywords:
                if keyword in payload_str:
                    logger.warning(f"🚨 HIGH RISK keyword detected: {keyword}")
                    return True, keyword
            
            # Check for medium-risk keywords (need 2+)
            medium_count = sum(1 for kw in self.medium_risk_keywords if kw in payload_str)
            if medium_count >= 2:
                logger.warning(f"🚨 Multiple medium-risk keywords detected: {medium_count}")
                return True, "multiple_medium_risks"
        
        return False, None
    
    def request_approval(
        self, 
        company_id: str, 
        run_id: str, 
        risk_type: str
    ) -> str:
        """
        Create approval request
        
        Args:
            company_id: Company being analyzed
            run_id: Current run ID
            risk_type: Type of risk detected
            
        Returns:
            approval_id
        """
        import uuid
        approval_id = str(uuid.uuid4())[:8]
        
        approval_request = {
            "approval_id": approval_id,
            "company_id": company_id,
            "run_id": run_id,
            "risk_type": risk_type,
            "status": "pending",
            "requested_at": datetime.now().isoformat(),
            "approved_at": None,
            "reviewer": None,
            "comments": None
        }
        
        # Save to file
        approval_file = self.storage_dir / f"approval_{approval_id}.json"
        with open(approval_file, 'w') as f:
            json.dump(approval_request, f, indent=2)
        
        logger.warning("⏸️  WORKFLOW PAUSED - Awaiting human approval")
        logger.info(f"📋 Approval ID: {approval_id}")
        logger.info(f"🔍 Risk Type: {risk_type}")
        logger.info(f"📍 Company: {company_id}")
        logger.info(f"✅ Approve with: curl -X POST http://localhost:8001/api/v1/hitl/approve/{approval_id} -H 'Content-Type: application/json' -d '{{\"approved\": true, \"reviewer\": \"analyst\"}}'")
        
        return approval_id
    
    def wait_for_approval(
        self, 
        approval_id: str, 
        timeout: int = 300,
        poll_interval: int = 5
    ) -> str:
        """
        Wait for approval (blocks until approved/rejected/timeout)
        
        Args:
            approval_id: ID of approval request
            timeout: Max seconds to wait
            poll_interval: Seconds between checks
            
        Returns:
            Status: "approved", "rejected", or "timeout"
        """
        approval_file = self.storage_dir / f"approval_{approval_id}.json"
        start_time = time.time()
        
        logger.info(f"⏳ Waiting for approval (timeout: {timeout}s)...")
        
        while time.time() - start_time < timeout:
            # Check if approval file has been updated
            if approval_file.exists():
                with open(approval_file, 'r') as f:
                    approval = json.load(f)
                
                status = approval.get("status")
                
                if status == "approved":
                    logger.info("✅ HUMAN APPROVAL RECEIVED")
                    logger.info(f"👤 Reviewer: {approval.get('reviewer', 'unknown')}")
                    if approval.get('comments'):
                        logger.info(f"💬 Comments: {approval.get('comments')}")
                    return "approved"
                
                elif status == "rejected":
                    logger.warning("❌ APPROVAL REJECTED")
                    logger.info(f"👤 Reviewer: {approval.get('reviewer', 'unknown')}")
                    logger.info(f"💬 Reason: {approval.get('comments', 'No reason provided')}")
                    return "rejected"
            
            # Wait before checking again
            time.sleep(poll_interval)
        
        # Timeout
        logger.error("⏱️  APPROVAL TIMEOUT")
        
        # Update approval status
        if approval_file.exists():
            with open(approval_file, 'r') as f:
                approval = json.load(f)
            approval["status"] = "timeout"
            with open(approval_file, 'w') as f:
                json.dump(approval, f, indent=2)
        
        return "timeout"
    
    def get_pending_approvals(self) -> list:
        """Get all pending approval requests"""
        pending = []
        
        for approval_file in self.storage_dir.glob("approval_*.json"):
            with open(approval_file, 'r') as f:
                approval = json.load(f)
            
            if approval.get("status") == "pending":
                pending.append(approval)
        
        return pending


# ============================================================================
# INTEGRATION WITH EXISTING SUPERVISOR AGENT
# ============================================================================

def add_hitl_to_supervisor(supervisor_class):
    """
    Decorator to add HITL capability to existing DueDiligenceSupervisor
    
    Usage:
        @add_hitl_to_supervisor
        class DueDiligenceSupervisor:
            ...
    """
    
    # Store original analyze_company method
    original_analyze = supervisor_class.analyze_company
    
    async def analyze_company_with_hitl(self, company_id: str) -> Dict:
        """Wrapped analyze_company with HITL integration"""
        
        # Initialize HITL if not already done
        if not hasattr(self, 'hitl'):
            self.hitl = HITLIntegration()
        
        # Run original analysis
        analysis_results = await original_analyze(self, company_id)
        
        # Check if HITL is needed
        needs_hitl, risk_type = self.hitl.detect_risks(analysis_results)
        
        if needs_hitl:
            # Log the pause
            if self.logger:
                self.logger.log_thought(
                    f"HIGH RISK DETECTED: {risk_type}. "
                    "Human approval required before proceeding."
                )
            
            # Request approval
            run_id = self.logger.run_id if self.logger else "unknown"
            approval_id = self.hitl.request_approval(
                company_id, 
                run_id, 
                risk_type
            )
            
            # Log the action
            if self.logger:
                self.logger.log_action("request_human_approval", {
                    "approval_id": approval_id,
                    "risk_type": risk_type,
                    "company_id": company_id
                })
            
            # WAIT FOR APPROVAL (this is where it pauses!)
            approval_status = self.hitl.wait_for_approval(approval_id)
            
            # Log the observation
            if self.logger:
                self.logger.log_observation(
                    f"Approval status: {approval_status}",
                    observation_data={
                        "approval_id": approval_id,
                        "status": approval_status
                    }
                )
            
            # Handle rejection
            if approval_status != "approved":
                analysis_results["hitl_status"] = approval_status
                analysis_results["hitl_rejected"] = True
                
                logger.error(f"❌ Analysis terminated due to {approval_status}")
                
                return analysis_results
            
            # Approved - continue
            analysis_results["hitl_status"] = "approved"
            analysis_results["hitl_triggered"] = True
            
            if self.logger:
                self.logger.log_thought(
                    "Approval received. Continuing with analysis finalization."
                )
        
        return analysis_results
    
    # Replace the method
    supervisor_class.analyze_company = analyze_company_with_hitl
    
    return supervisor_class


# ============================================================================
# FASTAPI ENDPOINTS FOR APPROVAL
# ============================================================================

def create_hitl_endpoints():
    """
    Creates FastAPI endpoints for HITL approval
    Add this to your agent service API
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    
    app = FastAPI()
    hitl = HITLIntegration()
    
    class ApprovalDecision(BaseModel):
        approved: bool
        reviewer: str
        comments: Optional[str] = None
    
    @app.get("/api/v1/hitl/pending")
    async def get_pending_approvals():
        """Get all pending approval requests"""
        pending = hitl.get_pending_approvals()
        return {
            "pending_approvals": pending,
            "count": len(pending)
        }
    
    @app.get("/api/v1/hitl/approval/{approval_id}")
    async def get_approval(approval_id: str):
        """Get specific approval request"""
        approval_file = hitl.storage_dir / f"approval_{approval_id}.json"
        
        if not approval_file.exists():
            raise HTTPException(status_code=404, detail="Approval not found")
        
        with open(approval_file, 'r') as f:
            approval = json.load(f)
        
        return approval
    
    @app.post("/api/v1/hitl/approve/{approval_id}")
    async def make_decision(approval_id: str, decision: ApprovalDecision):
        """Approve or reject a workflow"""
        approval_file = hitl.storage_dir / f"approval_{approval_id}.json"
        
        if not approval_file.exists():
            raise HTTPException(status_code=404, detail="Approval not found")
        
        # Load approval
        with open(approval_file, 'r') as f:
            approval = json.load(f)
        
        # Update status
        approval["status"] = "approved" if decision.approved else "rejected"
        approval["reviewer"] = decision.reviewer
        approval["comments"] = decision.comments
        approval["approved_at"] = datetime.now().isoformat()
        
        # Save
        with open(approval_file, 'w') as f:
            json.dump(approval, f, indent=2)
        
        return {
            "status": approval["status"],
            "approval_id": approval_id,
            "message": "Decision recorded"
        }
    
    return app


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================

"""
STEP 1: Add HITL to your supervisor_agent.py
==========================================

At the top of src/lab13/agents/supervisor_agent.py, add:

    from HITL_INTEGRATION_PATCH import add_hitl_to_supervisor, HITLIntegration

Then decorate your DueDiligenceSupervisor class:

    @add_hitl_to_supervisor
    class DueDiligenceSupervisor:
        # ... existing code ...

That's it! The decorator automatically adds HITL to analyze_company()


STEP 2: Add approval endpoints to your agent service
====================================================

In your agent service (wherever you have the FastAPI app), add:

    from HITL_INTEGRATION_PATCH import create_hitl_endpoints
    
    # Add HITL routes to your existing app
    hitl_app = create_hitl_endpoints()
    
    # Or merge them into your main app
    app.include_router(hitl_app.router)


STEP 3: Test it
===============

# Create a test payload with risk keywords
echo '{
  "company_id": "test_company",
  "risk_signals": [{"type": "breach", "severity": "high"}]
}' > data/payloads/test_company.json

# Run the agent (it will pause)
python -c "
import asyncio
from src.lab13.agents.supervisor_agent import run_supervisor_agent
asyncio.run(run_supervisor_agent('test_company'))
"

# In another terminal, approve it
curl -X POST http://localhost:8001/api/v1/hitl/approve/APPROVAL_ID \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "reviewer": "analyst", "comments": "Looks good"}'

# Agent will resume and complete!


STEP 4: Demo it
===============

Your DAG doesn't need any changes! It just calls the agent:
- Agent detects risk → pauses
- You approve via curl
- Agent resumes → DAG gets result

Watch the agent logs for:
- ⏸️ WORKFLOW PAUSED
- ✅ HUMAN APPROVAL RECEIVED
"""


# ============================================================================
# ALTERNATIVE: MANUAL INTEGRATION (if decorator doesn't work)
# ============================================================================

"""
If the decorator approach doesn't work with your code structure,
manually add this to the END of your analyze_company() method:

    async def analyze_company(self, company_id: str) -> Dict[str, Any]:
        # ... all your existing code ...
        
        # ADD THIS AT THE END (before return):
        
        # Initialize HITL
        if not hasattr(self, 'hitl'):
            from HITL_INTEGRATION_PATCH import HITLIntegration
            self.hitl = HITLIntegration()
        
        # Check for risks
        needs_hitl, risk_type = self.hitl.detect_risks(analysis_results)
        
        if needs_hitl:
            logger.warning(f"⏸️ HITL Required: {risk_type}")
            
            run_id = self.logger.run_id if self.logger else "unknown"
            approval_id = self.hitl.request_approval(company_id, run_id, risk_type)
            
            # PAUSE HERE!
            approval_status = self.hitl.wait_for_approval(approval_id)
            
            if approval_status != "approved":
                analysis_results["hitl_rejected"] = True
                return analysis_results
            
            logger.info("✅ HITL Approved - continuing")
            analysis_results["hitl_approved"] = True
        
        return analysis_results
"""