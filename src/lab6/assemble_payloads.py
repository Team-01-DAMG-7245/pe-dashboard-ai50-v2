"""
Lab 6: Payload Assembly
Copies structured data to payloads directory
"""

import json
from pathlib import Path
from lab5.models import Payload

# Get project root
project_root = Path(__file__).resolve().parents[2]
STRUCTURED_DIR = project_root / "data" / "structured"
PAYLOADS_DIR = project_root / "data" / "payloads"

def assemble_payload(company_id: str) -> bool:
    """Copy structured data to payloads directory"""
    structured_path = STRUCTURED_DIR / f"{company_id}.json"
    payload_path = PAYLOADS_DIR / f"{company_id}.json"
    
    if not structured_path.exists():
        print(f"  [WARNING] No structured data found for {company_id}")
        return False
    
    try:
        # Load structured data
        with open(structured_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate it's a valid Payload
        payload = Payload.model_validate(data)
        
        # Save to payloads directory
        PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)
        with open(payload_path, 'w', encoding='utf-8') as f:
            json.dump(payload.model_dump(mode='json'), f, indent=2, default=str)
        
        print(f"  [OK] Assembled payload for {company_id}")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to assemble payload for {company_id}: {e}")
        return False

def main():
    """Assemble payloads for all companies with structured data"""
    print("=" * 60)
    print("LAB 6: PAYLOAD ASSEMBLY")
    print("=" * 60)
    
    if not STRUCTURED_DIR.exists():
        print(f"\n[ERROR] Structured data directory not found: {STRUCTURED_DIR}")
        return
    
    # Get all structured JSON files
    structured_files = list(STRUCTURED_DIR.glob("*.json"))
    
    if not structured_files:
        print(f"\n[WARNING] No structured data files found in {STRUCTURED_DIR}")
        return
    
    print(f"\nFound {len(structured_files)} structured data files")
    print(f"Assembling payloads...\n")
    
    success_count = 0
    for structured_file in sorted(structured_files):
        company_id = structured_file.stem
        if assemble_payload(company_id):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"[OK] LAB 6 COMPLETE!")
    print(f"   Assembled {success_count}/{len(structured_files)} payloads")
    print(f"   Output saved to {PAYLOADS_DIR}/")
    print("=" * 60)

if __name__ == "__main__":
    main()

