"""Check extracted metrics for priority companies"""

import json
from pathlib import Path

PRIORITY_COMPANIES = ['anthropic', 'hebbia', 'luminance', 'mercor', 'notion']

print("=" * 80)
print("PRIORITY COMPANIES - EXTRACTED METRICS SUMMARY")
print("=" * 80)

for company in PRIORITY_COMPANIES:
    json_path = Path(f"data/structured/{company}.json")
    if json_path.exists():
        data = json.load(open(json_path))
        snapshot = data.get('snapshots', [{}])[0] if data.get('snapshots') else {}
        company_data = data.get('company_record', {})
        
        print(f"\n{'='*80}")
        print(f"{company.upper()}")
        print("=" * 80)
        
        # Growth Momentum
        print("\n📈 GROWTH MOMENTUM:")
        print(f"  Headcount: {snapshot.get('headcount_total', 'N/A')}")
        print(f"  Job Openings: {snapshot.get('job_openings_count', 'N/A')}")
        print(f"  Headcount Velocity: {snapshot.get('headcount_velocity', 'N/A')}")
        print(f"  Funding Cadence: {snapshot.get('funding_cadence_months', 'N/A')} months")
        print(f"  Release Velocity: {snapshot.get('release_velocity', 'N/A')}")
        print(f"  Products Released (12m): {snapshot.get('products_released_last_12m', 'N/A')}")
        print(f"  Geography Expansion: {', '.join(snapshot.get('geography_expansion', [])) or 'N/A'}")
        
        # Risk & Challenges
        print("\n⚠️  RISK & CHALLENGES:")
        print(f"  Risk Score: {snapshot.get('risk_score', 'N/A')}/100")
        print(f"  Risk Level: {snapshot.get('risk_level', 'N/A')}")
        print(f"  Layoffs Mentioned: {snapshot.get('layoffs_mentioned', 'N/A')}")
        print(f"  Positive Events: {snapshot.get('positive_events_count', 'N/A')}")
        print(f"  Negative Events: {snapshot.get('negative_events_count', 'N/A')}")
        print(f"  Leadership Stability: {snapshot.get('leadership_stability', 'N/A')}")
        challenges = snapshot.get('key_challenges', [])
        if challenges:
            print(f"  Key Challenges: {', '.join(challenges[:3])}")
        
        # Durability
        print("\n💪 DURABILITY:")
        print(f"  Notable Customers: {len(snapshot.get('notable_customers', []))} listed")
        print(f"  Customer Quality: {snapshot.get('customer_quality_score', 'N/A')}")
        print(f"  Regulatory Exposure: {', '.join(snapshot.get('regulatory_exposure', [])[:3]) or 'None'}")
        print(f"  Churn Signals: {len(snapshot.get('churn_signals', []))} found")
        
        # Transparency & Disclosure
        print("\n🔍 TRANSPARENCY & DISCLOSURE:")
        print(f"  Transparency Score: {snapshot.get('transparency_score', 'N/A')}/100")
        print(f"  Transparency Level: {snapshot.get('transparency_level', 'N/A')}")
        print(f"  Marketing Claims: {len(snapshot.get('marketed_info_available', []))} found")
        print(f"  Case Studies: {len(snapshot.get('actual_case_studies', []))} found")
        print(f"  Marketing vs Reality: {snapshot.get('marketing_vs_reality_gap', 'N/A')}")
        gaps = snapshot.get('disclosure_gaps', [])
        if gaps:
            print(f"  Disclosure Gaps: {', '.join(gaps[:3])}")
        missing = snapshot.get('missing_key_info', [])
        if missing:
            print(f"  Missing Info: {', '.join(missing[:3])}")

print("\n" + "=" * 80)



