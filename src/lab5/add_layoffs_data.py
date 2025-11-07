"""
Helper script to add Layoffs.fyi data to company extraction
This can be used to manually add layoff data or integrate with Layoffs.fyi API
"""

import json
from pathlib import Path
from datetime import date
from typing import Dict, Optional

# Example: Manual layoff data for companies
# Format: {company_id: {layoffs_count, layoffs_date, layoffs_percentage, source}}
LAYOFFS_DATA = {
    # Add layoff data here if known
    # Example:
    # "anthropic": {
    #     "layoffs_count": 0,
    #     "layoffs_date": None,
    #     "layoffs_percentage": 0,
    #     "source": "Layoffs.fyi"
    # }
}

def add_layoffs_to_snapshot(company_id: str, snapshot_data: Dict) -> Dict:
    """Add layoff data to snapshot if available"""
    if company_id in LAYOFFS_DATA:
        layoff_info = LAYOFFS_DATA[company_id]
        snapshot_data["layoffs_mentioned"] = layoff_info.get("layoffs_count", 0) > 0
        snapshot_data["layoffs_count"] = layoff_info.get("layoffs_count")
        snapshot_data["layoffs_date"] = layoff_info.get("layoffs_date")
        snapshot_data["layoffs_percentage"] = layoff_info.get("layoffs_percentage")
    return snapshot_data

def update_structured_json_with_layoffs():
    """Update existing structured JSON files with layoff data"""
    project_root = Path(__file__).resolve().parents[2]
    structured_dir = project_root / "data" / "structured"
    
    if not structured_dir.exists():
        print("No structured data directory found")
        return
    
    updated_count = 0
    for json_file in structured_dir.glob("*.json"):
        company_id = json_file.stem
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        if data.get("snapshots") and len(data["snapshots"]) > 0:
            original_snapshot = data["snapshots"][0]
            updated_snapshot = add_layoffs_to_snapshot(company_id, original_snapshot)
            
            if updated_snapshot != original_snapshot:
                data["snapshots"][0] = updated_snapshot
                with open(json_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                updated_count += 1
                print(f"Updated {company_id}")
    
    print(f"\nUpdated {updated_count} companies with layoff data")

if __name__ == "__main__":
    print("=" * 60)
    print("Layoffs Data Integration")
    print("=" * 60)
    print("\nTo add layoff data:")
    print("1. Visit Layoffs.fyi (https://layoffs.fyi)")
    print("2. Search for companies")
    print("3. Add data to LAYOFFS_DATA dictionary in this script")
    print("4. Run this script to update structured JSON files\n")
    
    update_structured_json_with_layoffs()

