"""
Lab 9: Evaluation & Comparison
Compare RAG vs Structured dashboards for at least 5 companies
Generate evaluation dashboards and prepare for rubric scoring
"""

import requests
import json
import os
from datetime import datetime
from pathlib import Path

BASE_URL = "http://localhost:8002"
OUTPUT_DIR = "evaluation_output"  # Relative to lab9 folder

def get_evaluation_companies():
    """Get ALL companies with payloads for evaluation"""
    project_root = Path(__file__).resolve().parents[2]
    payloads_dir = project_root / "data" / "payloads"
    
    if not payloads_dir.exists():
        # Fallback to default companies
        return ["anthropic", "cohere", "databricks", "glean", "openevidence"]
    
    # Get all companies with payloads
    payload_files = list(payloads_dir.glob("*.json"))
    companies = sorted([f.stem for f in payload_files])
    
    return companies  # Return all companies

def generate_and_save_dashboards():
    """Generate both RAG and Structured dashboards and save to files"""
    
    # Output directory is relative to lab9 folder
    lab9_dir = Path(__file__).resolve().parent
    output_dir = lab9_dir / OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)
    
    # Get companies to evaluate
    companies = get_evaluation_companies()
    
    print("=" * 60)
    print("LAB 9: Generating Dashboards for Evaluation")
    print("=" * 60)
    print(f"\nEvaluating {len(companies)} companies: {', '.join(companies)}")
    
    # Check API
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"\n[ERROR] API not running. Start with: python src/lab7/rag_dashboard.py")
            return
    except:
        print(f"\n[ERROR] API not running. Start with: python src/lab7/rag_dashboard.py")
        print("       The API server must be running for Lab 9 to work.")
        return
    
    print(f"\n[OK] API is running at {BASE_URL}")
    
    results = {}
    
    for company in companies:
        print(f"\n{'='*60}")
        print(f"Processing: {company.upper()}")
        print(f"{'='*60}")
        
        company_results = {"company_id": company}
        
        # Generate RAG dashboard
        print(f"Generating RAG dashboard...")
        try:
            rag_response = requests.post(
                f"{BASE_URL}/dashboard/rag",
                json={"company_id": company, "top_k": 10},
                timeout=90
            )
            if rag_response.status_code == 200:
                rag_data = rag_response.json()
                rag_dashboard = rag_data.get("dashboard", "")
                chunks_used = rag_data.get("chunks_used", 0)
                
                # Save to file
                rag_file = output_dir / f"{company}_rag.md"
                with open(rag_file, "w", encoding="utf-8") as f:
                    f.write(f"# RAG Dashboard: {company.upper()}\n\n")
                    f.write(f"Generated: {datetime.now().isoformat()}\n")
                    f.write(f"Chunks Used: {chunks_used}\n\n")
                    f.write("---\n\n")
                    f.write(rag_dashboard)
                
                company_results["rag"] = {
                    "file": str(rag_file),
                    "chunks_used": chunks_used,
                    "length": len(rag_dashboard)
                }
                print(f"  [OK] Saved to {rag_file}")
            else:
                print(f"  [FAIL] RAG failed: {rag_response.status_code}")
                company_results["rag"] = None
        except Exception as e:
            print(f"  [FAIL] RAG error: {e}")
            company_results["rag"] = None
        
        # Generate Structured dashboard
        print(f"Generating Structured dashboard...")
        try:
            structured_response = requests.post(
                f"{BASE_URL}/dashboard/structured",
                json={"company_id": company},
                timeout=90
            )
            if structured_response.status_code == 200:
                structured_data = structured_response.json()
                structured_dashboard = structured_data.get("dashboard", "")
                
                # Save to file
                structured_file = output_dir / f"{company}_structured.md"
                with open(structured_file, "w", encoding="utf-8") as f:
                    f.write(f"# Structured Dashboard: {company.upper()}\n\n")
                    f.write(f"Generated: {datetime.now().isoformat()}\n")
                    f.write(f"Source: Structured Payload (data/payloads/{company}.json)\n\n")
                    f.write("---\n\n")
                    f.write(structured_dashboard)
                
                company_results["structured"] = {
                    "file": str(structured_file),
                    "length": len(structured_dashboard)
                }
                print(f"  [OK] Saved to {structured_file}")
            else:
                print(f"  [FAIL] Structured failed: {structured_response.status_code}")
                company_results["structured"] = None
        except Exception as e:
            print(f"  [FAIL] Structured error: {e}")
            company_results["structured"] = None
        
        results[company] = company_results
    
    # Generate comparison summary
    summary_file = output_dir / "summary.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("# Evaluation Dashboard Summary\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write("## Companies Evaluated\n\n")
        
        for company in companies:
            result = results.get(company, {})
            f.write(f"### {company.upper()}\n\n")
            
            if result.get("rag"):
                rag = result["rag"]
                f.write(f"- **RAG:** {rag['file']} ({rag['chunks_used']} chunks, {rag['length']} chars)\n")
            else:
                f.write(f"- **RAG:** [FAIL] Failed to generate\n")
            
            if result.get("structured"):
                struct = result["structured"]
                f.write(f"- **Structured:** {struct['file']} ({struct['length']} chars)\n")
            else:
                f.write(f"- **Structured:** [FAIL] Failed to generate\n")
            
            f.write("\n")
    
    print(f"\n{'='*60}")
    print(f"[OK] Evaluation dashboards generated!")
    print(f"   Output directory: {output_dir}/")
    print(f"   Summary: {summary_file}")
    print(f"\nNext steps:")
    print(f"  1. Review dashboards in {output_dir}/")
    print(f"  2. Fill out EVAL.md with rubric scores")
    print(f"  3. Run calculate_evaluation_matrix.py to generate evaluation matrix")

if __name__ == "__main__":
    generate_and_save_dashboards()

