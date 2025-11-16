import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class Payload(BaseModel):
    """Full payload model matching Assignment 2 structure"""
    company_record: dict
    events: List[Dict[str, Any]] = []
    snapshots: List[Dict[str, Any]] = []
    products: List[Dict[str, Any]] = []
    leadership: List[Dict[str, Any]] = []
    visibility: List[Dict[str, Any]] = []
    notes: str = ""
    provenance_policy: str = ""

async def get_latest_structured_payload(company_id: str) -> Payload:
    """
    Tool: get_latest_structured_payload
    Retrieve the latest fully assembled structured payload for a company.
    """
    try:
        payload_path = Path(f"data/payloads/{company_id}.json")
        
        if not payload_path.exists():
            return Payload(
                company_record={"company_id": company_id, "error": f"Payload not found"}
            )
        
        with open(payload_path, 'r') as f:
            data = json.load(f)
        
        return Payload(**data)
    
    except Exception as e:
        print(f"Error loading payload: {str(e)}")
        return Payload(
            company_record={"company_id": company_id, "error": str(e)}
        )
