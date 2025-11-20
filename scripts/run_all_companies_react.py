"""
Script to run ReAct logging against all companies.
Generates traces for each company in the payloads directory.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.supervisor_agent_langchain import run_supervisor_agent_langchain
from dotenv import load_dotenv

load_dotenv()


def get_all_company_ids() -> List[str]:
    """
    Get list of all company IDs from payloads directory.
    
    Returns:
        List of company IDs (without .json extension)
    """
    payloads_dir = Path("data/payloads")
    if not payloads_dir.exists():
        print(f"Error: {payloads_dir} does not exist")
        return []
    
    company_files = list(payloads_dir.glob("*.json"))
    # Exclude manifest.json if it exists
    company_ids = [f.stem for f in company_files if f.name != "manifest.json"]
    return sorted(company_ids)


async def run_company_analysis(company_id: str, run_id_prefix: str = "all-companies") -> Dict[str, Any]:
    """
    Run ReAct analysis for a single company.
    
    Args:
        company_id: Company to analyze
        run_id_prefix: Prefix for run ID
        
    Returns:
        Results dictionary with trace information
    """
    run_id = f"{run_id_prefix}-{company_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        print(f"\n{'='*70}")
        print(f"Analyzing: {company_id}")
        print(f"Run ID: {run_id}")
        print(f"{'='*70}")
        
        results = await run_supervisor_agent_langchain(
            company_id=company_id,
            enable_logging=True,
            run_id=run_id
        )
        
        return {
            "company_id": company_id,
            "run_id": run_id,
            "status": "success",
            "trace_file": results.get("trace_file"),
            "error": None
        }
    
    except Exception as e:
        print(f"\n[ERROR] Failed to analyze {company_id}: {str(e)}")
        return {
            "company_id": company_id,
            "run_id": run_id,
            "status": "error",
            "trace_file": None,
            "error": str(e)
        }


async def run_all_companies(
    limit: int = None,
    run_id_prefix: str = "all-companies",
    output_file: str = "logs/all_companies_react_summary.json"
):
    """
    Run ReAct analysis for all companies.
    
    Args:
        limit: Optional limit on number of companies to process
        run_id_prefix: Prefix for run IDs
        output_file: Path to save summary JSON
    """
    company_ids = get_all_company_ids()
    
    if not company_ids:
        print("No companies found in data/payloads/")
        return
    
    if limit:
        company_ids = company_ids[:limit]
        print(f"Processing first {limit} companies (limited)")
    else:
        print(f"Processing all {len(company_ids)} companies")
    
    print(f"\nCompanies to process: {', '.join(company_ids)}")
    print(f"\nStarting analysis at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    start_time = datetime.now()
    
    # Process companies sequentially (to avoid rate limits)
    for i, company_id in enumerate(company_ids, 1):
        print(f"\n[{i}/{len(company_ids)}] Processing {company_id}...")
        
        result = await run_company_analysis(company_id, run_id_prefix)
        results.append(result)
        
        # Small delay between companies to avoid overwhelming the system
        if i < len(company_ids):
            await asyncio.sleep(1)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Create summary
    summary = {
        "run_id_prefix": run_id_prefix,
        "started_at": start_time.isoformat(),
        "completed_at": end_time.isoformat(),
        "duration_seconds": duration,
        "total_companies": len(company_ids),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "failed": sum(1 for r in results if r["status"] == "error"),
        "results": results
    }
    
    # Save summary
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    # Print summary
    print(f"\n{'='*70}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f"Total Companies: {len(company_ids)}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    print(f"\nSummary saved to: {output_path}")
    print(f"\nTrace files saved to: logs/react_traces/")
    print(f"{'='*70}\n")
    
    # List successful runs
    if summary['successful'] > 0:
        print("Successful runs:")
        for r in results:
            if r["status"] == "success":
                print(f"  - {r['company_id']}: {r['run_id']}")
    
    # List failed runs
    if summary['failed'] > 0:
        print("\nFailed runs:")
        for r in results:
            if r["status"] == "error":
                print(f"  - {r['company_id']}: {r['error']}")
    
    return summary


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run ReAct analysis for all companies")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of companies to process (for testing)"
    )
    parser.add_argument(
        "--run-id-prefix",
        type=str,
        default="all-companies",
        help="Prefix for run IDs (default: all-companies)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="logs/all_companies_react_summary.json",
        help="Output file for summary (default: logs/all_companies_react_summary.json)"
    )
    
    args = parser.parse_args()
    
    try:
        summary = asyncio.run(run_all_companies(
            limit=args.limit,
            run_id_prefix=args.run_id_prefix,
            output_file=args.output
        ))
        
        print("\n[OK] All companies processed!")
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Analysis stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

