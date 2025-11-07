"""
Structured pipeline - loads payload from disk
"""
from pathlib import Path
from typing import Optional
from .lab5.models import Payload

# Simple path for Docker container
DATA_DIR = Path("/app/data/payloads")
starter_payload_path = Path("/app/data/starter_payload.json")

def load_payload(company_id: str) -> Optional[Payload]:
    fp = DATA_DIR / f"{company_id}.json"
    if not fp.exists():
        # fallback to starter if exists
        if starter_payload_path.exists():
            return Payload.model_validate_json(starter_payload_path.read_text())
        else:
            raise FileNotFoundError(f"Payload not found for {company_id} and no starter_payload.json available")
    return Payload.model_validate_json(fp.read_text())
