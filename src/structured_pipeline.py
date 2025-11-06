"""
Structured pipeline - loads payload from disk
"""
from pathlib import Path
from typing import Optional
from .models import Payload  # Fixed: added dot for relative import

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "payloads"

def load_payload(company_id: str) -> Optional[Payload]:
    """
    Load structured payload for a company
    
    Args:
        company_id: Company identifier
        
    Returns:
        Payload object or None if fallback to starter
    """
    fp = DATA_DIR / f"{company_id}.json"
    if not fp.exists():
        # fallback to starter
        starter = Path(__file__).resolve().parents[1] / "data" / "starter_payload.json"
        if starter.exists():
            return Payload.model_validate_json(starter.read_text())
        return None
    return Payload.model_validate_json(fp.read_text())
