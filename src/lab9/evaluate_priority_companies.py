"""
Lab 9: Evaluate RAG vs Structured dashboards for priority companies
"""

import requests
import json
from pathlib import Path
from typing import List

BASE_URL = "http://localhost:8002"
OUTPUT_DIR = "evaluation_output"  # Relative to lab9 folder
PRIORITY_COMPANIES = ['anthropic', 'hebbia', 'luminance', 'mercor', 'notion']

def generate_and_save_dashboards():
    """Generate both RAG and Structured dashboards for priority companies and save to files"""
    
    # Output directory is relative to lab9 folder
    lab9_dir = Path(__file__).resolve().parent
    output_dir = lab9_dir / OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("LAB 9: EVALUATION - Priority Companies")
    print("=" * 80)
    print(f"\nCompanies: {', '.join([c.title() for c in PRIORITY_COMPANIES])}")
    print(f"Output directory: {output_dir}\n")
    
    # Check API health
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code == 200:
            print("[OK] API Server is healthy\n")
        else:
            print(f"[WARNING] API Server returned status {health_response.status_code}\n")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Cannot connect to API server at {BASE_URL}")
        print(f"Error: {e}")
        print("\nPlease start the API server first:")
        print("  python src/lab7/rag_dashboard.py")
        return
    
    success_count = 0
    failed_companies = []
    
    for company_id in PRIORITY_COMPANIES:
        print(f"\n{'='*80}")
        print(f"Processing {company_id.upper()}")
        print("=" * 80)
        
        # Generate RAG dashboard
        print(f"\n[1/2] Generating RAG dashboard...")
        try:
            rag_response = requests.post(
                f"{BASE_URL}/dashboard/rag",
                json={"company_id": company_id},
                timeout=120
            )
            
            if rag_response.status_code == 200:
                rag_content = rag_response.json().get("dashboard", "")
                rag_file = output_dir / f"{company_id}_rag.md"
                rag_file.write_text(rag_content, encoding='utf-8')
                print(f"  [OK] Saved RAG dashboard: {rag_file.name} ({len(rag_content)} chars)")
            else:
                print(f"  [ERROR] RAG dashboard failed: {rag_response.status_code}")
                print(f"  Response: {rag_response.text[:200]}")
                failed_companies.append(f"{company_id} (RAG)")
        except Exception as e:
            print(f"  [ERROR] RAG dashboard failed: {e}")
            failed_companies.append(f"{company_id} (RAG)")
        
        # Generate Structured dashboard
        print(f"[2/2] Generating Structured dashboard...")
        try:
            structured_response = requests.post(
                f"{BASE_URL}/dashboard/structured",
                json={"company_id": company_id},
                timeout=120
            )
            
            if structured_response.status_code == 200:
                structured_content = structured_response.json().get("dashboard", "")
                structured_file = output_dir / f"{company_id}_structured.md"
                structured_file.write_text(structured_content, encoding='utf-8')
                print(f"  [OK] Saved Structured dashboard: {structured_file.name} ({len(structured_content)} chars)")
                success_count += 1
            else:
                print(f"  [ERROR] Structured dashboard failed: {structured_response.status_code}")
                print(f"  Response: {structured_response.text[:200]}")
                failed_companies.append(f"{company_id} (Structured)")
        except Exception as e:
            print(f"  [ERROR] Structured dashboard failed: {e}")
            failed_companies.append(f"{company_id} (Structured)")
    
    print("\n" + "=" * 80)
    print("EVALUATION COMPLETE")
    print("=" * 80)
    print(f"\n✅ Successfully generated dashboards for {success_count}/{len(PRIORITY_COMPANIES)} companies")
    
    if failed_companies:
        print(f"\n❌ Failed companies:")
        for company in failed_companies:
            print(f"   - {company}")
    
    print(f"\n📁 Output directory: {output_dir}")
    print(f"\nNext steps:")
    print("  1. Review generated dashboards")
    print("  2. Run: python src/lab9/calculate_evaluation_matrix.py")
    print("  3. Fill out EVAL.md with rubric scores")

if __name__ == "__main__":
    generate_and_save_dashboards()





