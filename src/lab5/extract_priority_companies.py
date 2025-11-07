"""
Re-extract structured data for priority companies with maximum focus on Growth Momentum
Priority companies: Anthropic, Hebbia, Luminance, Mercor, Notion
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from lab5.structured_extraction import process_company

# Priority companies for maximum extraction
PRIORITY_COMPANIES = ['anthropic', 'hebbia', 'luminance', 'mercor', 'notion']

def main():
    """Re-extract priority companies with maximum focus on Growth Momentum"""
    
    print("=" * 60)
    print("PRIORITY EXTRACTION: Growth Momentum Focus")
    print("=" * 60)
    print(f"\nCompanies: {', '.join(PRIORITY_COMPANIES)}")
    print("\nFocus Fields:")
    print("  - headcount_total")
    print("  - job_openings_count")
    print("  - hiring_focus")
    print("  - headcount_growth_pct")
    print("  - engineering_openings")
    print("  - sales_openings")
    print("=" * 60)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n[ERROR] OPENAI_API_KEY environment variable not set!")
        return
    
    results = []
    for company_id in PRIORITY_COMPANIES:
        print(f"\n{'='*60}")
        print(f"Processing {company_id.upper()}...")
        print("=" * 60)
        result = process_company(company_id)
        if result:
            results.append(result)
    
    print("\n" + "=" * 60)
    print(f"[OK] PRIORITY EXTRACTION COMPLETE!")
    print(f"   Processed {len(results)}/{len(PRIORITY_COMPANIES)} companies")
    print(f"   Output saved to data/structured/")
    print("=" * 60)

if __name__ == "__main__":
    main()

