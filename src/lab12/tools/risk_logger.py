import json
import logging
from datetime import date, datetime
from pathlib import Path
from pydantic import BaseModel, HttpUrl

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("risk_logger")

class LayoffSignal(BaseModel):
    """Structured description of a potential layoff / risk signal."""
    company_id: str
    occurred_on: date
    description: str
    source_url: HttpUrl

async def report_layoff_signal(signal_data: LayoffSignal) -> bool:
    """
    Tool: report_layoff_signal
    Record a high-risk layoff / workforce reduction / negative event.
    """
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logger.warning(
            f"⚠️ RISK SIGNAL DETECTED:\n"
            f"  Company: {signal_data.company_id}\n"
            f"  Date: {signal_data.occurred_on}\n"
            f"  Description: {signal_data.description}\n"
            f"  Source: {signal_data.source_url}"
        )
        
        risk_log_file = log_dir / "risk_signals.jsonl"
        with open(risk_log_file, 'a') as f:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "company_id": signal_data.company_id,
                "occurred_on": str(signal_data.occurred_on),
                "description": signal_data.description,
                "source_url": str(signal_data.source_url)
            }
            f.write(json.dumps(log_entry) + '\n')
        
        return True
    
    except Exception as e:
        logger.error(f"Failed to log risk signal: {str(e)}")
        return False