"""
Calculate evaluation matrix for top 5 companies with best structured outputs
"""

import json
from pathlib import Path
from typing import Dict, List
import re

def analyze_dashboard_quality(dashboard_text: str) -> Dict:
    """Analyze dashboard quality metrics"""
    if not dashboard_text:
        return {
            "has_8_sections": False,
            "sections_found": [],
            "not_disclosed_count": 0,
            "word_count": 0,
            "has_provenance": False,
            "sections_count": 0
        }
    
    # Check for 8 required sections
    required_sections = [
        "## Company Overview",
        "## Business Model and GTM",
        "## Funding & Investor Profile",
        "## Growth Momentum",
        "## Visibility & Market Sentiment",
        "## Risks and Challenges",
        "## Outlook",
        "## Disclosure Gaps"
    ]
    
    sections_found = []
    for section in required_sections:
        if section in dashboard_text:
            sections_found.append(section.replace("## ", ""))
    
    # Count "Not disclosed" usage
    not_disclosed_count = len(re.findall(r'Not disclosed\.?', dashboard_text, re.IGNORECASE))
    
    # Word count
    word_count = len(dashboard_text.split())
    
    # Check for provenance indicators
    has_provenance = any(indicator in dashboard_text.lower() for indicator in [
        "source", "according to", "based on", "from", "provenance"
    ])
    
    return {
        "has_8_sections": len(sections_found) == 8,
        "sections_found": sections_found,
        "sections_count": len(sections_found),
        "not_disclosed_count": not_disclosed_count,
        "word_count": word_count,
        "has_provenance": has_provenance
    }

def calculate_evaluation_matrix():
    """Calculate evaluation matrix - rank all companies and show top 5"""
    # Evaluation directory is in lab9 folder
    lab9_dir = Path(__file__).resolve().parent
    evaluation_dir = lab9_dir / "evaluation_output"
    
    if not evaluation_dir.exists():
        print(f"[ERROR] Evaluation directory not found: {evaluation_dir}")
        print("Please run evaluate_comparison.py first to generate dashboards.")
        return
    
    # Get all companies with structured dashboards
    structured_files = list(evaluation_dir.glob("*_structured.md"))
    all_companies = sorted([f.stem.replace("_structured", "") for f in structured_files])
    
    if not all_companies:
        print("[ERROR] No structured dashboards found. Run Lab 9 first.")
        return
    
    print(f"Found {len(all_companies)} companies with structured dashboards")
    
    # Analyze all companies and rank by structured output quality
    company_scores = []
    
    for company in all_companies:
        structured_file = evaluation_dir / f"{company}_structured.md"
        if structured_file.exists():
            structured_text = structured_file.read_text(encoding='utf-8')
            metrics = analyze_dashboard_quality(structured_text)
            
            # Calculate quality score for structured output
            quality_score = (
                metrics['sections_count'] * 2 +  # Sections are important
                (1 if metrics['has_8_sections'] else 0) * 5 +  # Bonus for all 8
                min(metrics['word_count'] / 100, 5) +  # Reasonable length bonus
                (1 if metrics['has_provenance'] else 0) * 2 +  # Provenance bonus
                max(0, 5 - metrics['not_disclosed_count'])  # Fewer "Not disclosed" is better
            )
            
            company_scores.append({
                "company": company,
                "metrics": metrics,
                "quality_score": quality_score
            })
    
    # Sort by quality score
    company_scores.sort(key=lambda x: x['quality_score'], reverse=True)
    
    # Get top 5
    top_5_companies = [c['company'] for c in company_scores[:5]]
    
    print(f"\nTop 5 companies with best structured outputs:")
    for i, c in enumerate(company_scores[:5], 1):
        print(f"  {i}. {c['company']} (Score: {c['quality_score']:.1f})")
    
    # Now analyze top 5 with both RAG and Structured
    
    print("=" * 80)
    print("EVALUATION MATRIX FOR TOP 5 COMPANIES")
    print("=" * 80)
    
    results = {}
    
    for company in top_5_companies:
        print(f"\n{company.upper()}")
        print("-" * 80)
        
        company_results = {"company_id": company}
        
        # Read RAG dashboard
        rag_file = evaluation_dir / f"{company}_rag.md"
        if rag_file.exists():
            rag_text = rag_file.read_text(encoding='utf-8')
            rag_metrics = analyze_dashboard_quality(rag_text)
            company_results["rag"] = rag_metrics
            
            print(f"RAG Dashboard:")
            print(f"  - Sections: {rag_metrics['sections_count']}/8")
            print(f"  - All 8 sections: {'Yes' if rag_metrics['has_8_sections'] else 'No'}")
            print(f"  - 'Not disclosed' count: {rag_metrics['not_disclosed_count']}")
            print(f"  - Word count: {rag_metrics['word_count']}")
            print(f"  - Has provenance: {'Yes' if rag_metrics['has_provenance'] else 'No'}")
        else:
            print(f"RAG Dashboard: [NOT FOUND]")
            company_results["rag"] = None
        
        # Read Structured dashboard
        structured_file = evaluation_dir / f"{company}_structured.md"
        if structured_file.exists():
            structured_text = structured_file.read_text(encoding='utf-8')
            structured_metrics = analyze_dashboard_quality(structured_text)
            company_results["structured"] = structured_metrics
            
            print(f"Structured Dashboard:")
            print(f"  - Sections: {structured_metrics['sections_count']}/8")
            print(f"  - All 8 sections: {'Yes' if structured_metrics['has_8_sections'] else 'No'}")
            print(f"  - 'Not disclosed' count: {structured_metrics['not_disclosed_count']}")
            print(f"  - Word count: {structured_metrics['word_count']}")
            print(f"  - Has provenance: {'Yes' if structured_metrics['has_provenance'] else 'No'}")
        else:
            print(f"Structured Dashboard: [NOT FOUND]")
            company_results["structured"] = None
        
        results[company] = company_results
    
    # Generate comparison table
    print("\n" + "=" * 80)
    print("EVALUATION MATRIX - COMPARISON TABLE")
    print("=" * 80)
    
    print(f"\n{'Company':<15} {'Type':<12} {'Sections':<10} {'All 8?':<8} {'Not Disclosed':<15} {'Words':<8} {'Provenance':<12}")
    print("-" * 80)
    
    for company in top_5_companies:
        result = results.get(company, {})
        
        # RAG row
        if result.get("rag"):
            rag = result["rag"]
            print(f"{company:<15} {'RAG':<12} {rag['sections_count']}/8{'':<4} {'Yes' if rag['has_8_sections'] else 'No':<8} {rag['not_disclosed_count']:<15} {rag['word_count']:<8} {'Yes' if rag['has_provenance'] else 'No':<12}")
        else:
            print(f"{company:<15} {'RAG':<12} {'N/A':<10} {'N/A':<8} {'N/A':<15} {'N/A':<8} {'N/A':<12}")
        
        # Structured row
        if result.get("structured"):
            struct = result["structured"]
            print(f"{'':<15} {'Structured':<12} {struct['sections_count']}/8{'':<4} {'Yes' if struct['has_8_sections'] else 'No':<8} {struct['not_disclosed_count']:<15} {struct['word_count']:<8} {'Yes' if struct['has_provenance'] else 'No':<12}")
        else:
            print(f"{'':<15} {'Structured':<12} {'N/A':<10} {'N/A':<8} {'N/A':<15} {'N/A':<8} {'N/A':<12}")
        print()
    
    # Save detailed results
    output_file = evaluation_dir / "evaluation_matrix.json"
    evaluation_dir.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n[OK] Evaluation matrix saved to: {output_file}")
    
    # Summary recommendations
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)
    
    for company in top_5_companies:
        result = results.get(company, {})
        rag = result.get("rag", {})
        struct = result.get("structured", {})
        
        if rag and struct:
            print(f"\n{company.upper()}:")
            print(f"  - RAG sections: {rag['sections_count']}/8, Structured: {struct['sections_count']}/8")
            print(f"  - RAG completeness: {'Better' if rag['sections_count'] > struct['sections_count'] else 'Worse' if rag['sections_count'] < struct['sections_count'] else 'Equal'}")
            print(f"  - RAG uses 'Not disclosed': {rag['not_disclosed_count']} times")
            print(f"  - Structured uses 'Not disclosed': {struct['not_disclosed_count']} times")

if __name__ == "__main__":
    calculate_evaluation_matrix()

