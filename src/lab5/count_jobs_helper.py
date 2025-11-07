"""
Helper to count job listings from careers pages
This helps improve job counting accuracy
"""

import re
from pathlib import Path

def count_jobs_from_careers_text(careers_text: str) -> dict:
    """Count jobs from careers page text"""
    if not careers_text:
        return {"total": 0, "engineering": 0, "sales": 0, "departments": []}
    
    lines = [l.strip() for l in careers_text.split('\n') if l.strip()]
    
    # Find all "Apply" lines
    apply_indices = [i for i, line in enumerate(lines) if 'Apply' in line]
    
    # Get job titles (usually 1-2 lines before "Apply")
    job_titles = []
    for idx in apply_indices:
        # Look 1-2 lines before "Apply"
        for offset in [1, 2]:
            if idx >= offset:
                candidate = lines[idx - offset]
                # Skip if it's a location or department header
                if (len(candidate) > 5 and 
                    len(candidate) < 100 and
                    not any(skip in candidate.lower() for skip in [
                        'new york', 'london', 'san francisco', 'apply', 
                        'apply now', 'remote', 'hybrid', 'dublin', 'tokyo',
                        'engineering', 'sales', 'marketing', 'design', 'people',
                        'gtm', 'ai strategy', 'department', 'location'
                    ]) and
                    not re.match(r'^[A-Z][a-z]+,?\s+[A-Z][a-z]+$', candidate) and  # Skip "City, State"
                    not candidate.isupper()):  # Skip all-caps headers
                    job_titles.append(candidate)
                    break
    
    # Count engineering jobs
    engineering_keywords = ['engineer', 'developer', 'sre', 'platform', 'data engineer', 
                          'backend', 'frontend', 'fullstack', 'devops', 'infrastructure']
    engineering_jobs = [j for j in job_titles if any(kw in j.lower() for kw in engineering_keywords)]
    
    # Count sales jobs
    sales_keywords = ['sales', 'account executive', 'account manager', 'business development',
                     'bd', 'ae', 'strategist', 'client partner', 'revenue']
    sales_jobs = [j for j in job_titles if any(kw in j.lower() for kw in sales_keywords)]
    
    # Extract departments
    departments = []
    dept_keywords = {
        'Engineering': engineering_keywords,
        'Sales': sales_keywords,
        'Marketing': ['marketing', 'growth', 'content', 'brand'],
        'Product': ['product', 'design', 'ux', 'ui'],
        'Operations': ['operations', 'ops', 'business operations'],
        'People': ['people', 'hr', 'recruiter', 'talent'],
        'Finance': ['finance', 'accounting', 'billing'],
        'Legal': ['legal', 'counsel', 'compliance'],
        'Customer Success': ['customer success', 'customer experience', 'support']
    }
    
    for dept, keywords in dept_keywords.items():
        if any(kw in careers_text.lower() for kw in keywords):
            # Count jobs in this department
            dept_jobs = [j for j in job_titles if any(kw in j.lower() for kw in keywords)]
            if dept_jobs:
                departments.append(dept)
    
    return {
        "total": len(set(job_titles)),
        "engineering": len(engineering_jobs),
        "sales": len(sales_jobs),
        "departments": departments,
        "job_titles": list(set(job_titles))
    }

if __name__ == "__main__":
    # Test with priority companies
    companies = ['anthropic', 'hebbia', 'luminance', 'mercor', 'notion']
    project_root = Path(__file__).resolve().parents[2]
    
    print("=" * 60)
    print("Job Counting Helper - Priority Companies")
    print("=" * 60)
    
    for company in companies:
        careers_path = project_root / "data" / "raw" / company / "initial" / "careers_clean.txt"
        if not careers_path.exists():
            careers_path = project_root / "data" / "raw" / company / "initial" / "careers.txt"
        
        if careers_path.exists():
            text = careers_path.read_text(encoding='utf-8')
            counts = count_jobs_from_careers_text(text)
            print(f"\n{company.upper()}:")
            print(f"  Total Jobs: {counts['total']}")
            print(f"  Engineering: {counts['engineering']}")
            print(f"  Sales: {counts['sales']}")
            print(f"  Departments: {', '.join(counts['departments'])}")

