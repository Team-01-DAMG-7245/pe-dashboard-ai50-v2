"""HITL API Service"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

app = FastAPI()

class ApprovalDecision(BaseModel):
    approved: bool
    reviewer: str
    comments: Optional[str] = None

@app.get("/api/v1/hitl/pending")
def get_pending():
    """Get pending approvals"""
    hitl_dir = Path("data/hitl")
    pending = []
    
    if hitl_dir.exists():
        for f in hitl_dir.glob("approval_*.json"):
            with open(f) as file:
                approval = json.load(file)
                if approval.get("status") == "pending":
                    pending.append(approval)
    
    return {"pending_approvals": pending, "count": len(pending)}

@app.post("/api/v1/hitl/approve/{approval_id}")
def approve(approval_id: str, decision: ApprovalDecision):
    """Approve or reject"""
    approval_file = Path(f"data/hitl/approval_{approval_id}.json")
    
    if not approval_file.exists():
        raise HTTPException(status_code=404, detail="Approval not found")
    
    with open(approval_file) as f:
        approval = json.load(f)
    
    approval["status"] = "approved" if decision.approved else "rejected"
    approval["reviewer"] = decision.reviewer
    approval["comments"] = decision.comments
    approval["approved_at"] = datetime.now().isoformat()
    
    with open(approval_file, 'w') as f:
        json.dump(approval, f, indent=2)
    
    return {"status": approval["status"], "message": "Updated"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)