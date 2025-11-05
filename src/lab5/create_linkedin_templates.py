"""
Create LinkedIn data templates for priority companies
These can be filled in manually by visiting LinkedIn company pages
"""

from pathlib import Path

PRIORITY_COMPANIES = ['anthropic', 'hebbia', 'luminance', 'mercor', 'notion']

LINKEDIN_TEMPLATE = """LinkedIn Company Page: https://www.linkedin.com/company/{company-name}

Company Size: [e.g., "201-500 employees" or exact number]
LinkedIn Followers: [number if available]
Active Job Postings: [count from LinkedIn jobs section]
Total Employees: [exact number if available, or use midpoint of range]

Hiring Departments:
- [List departments with open roles, e.g., Engineering, Sales, Marketing]

Recent Growth Information:
- [Any growth percentages mentioned]
- [Growth announcements]

Job Openings Breakdown:
- Engineering: [count]
- Sales: [count]
- Marketing: [count]
- Other: [count]

Notes:
[Any additional information from LinkedIn]
"""

def create_templates():
    """Create LinkedIn template files for priority companies"""
    project_root = Path(__file__).resolve().parents[2]
    
    print("=" * 60)
    print("Creating LinkedIn Data Templates")
    print("=" * 60)
    
    for company in PRIORITY_COMPANIES:
        linkedin_path = project_root / "data" / "raw" / company / "initial" / "linkedin_clean.txt"
        
        if not linkedin_path.exists():
            # Create template
            linkedin_path.parent.mkdir(parents=True, exist_ok=True)
            template = LINKEDIN_TEMPLATE.replace("{company-name}", company)
            linkedin_path.write_text(template, encoding='utf-8')
            print(f"\n[OK] Created template for {company}")
            print(f"     Path: {linkedin_path}")
        else:
            print(f"\n[SKIP] {company} - LinkedIn file already exists")
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("1. Visit each company's LinkedIn page")
    print("2. Fill in the linkedin_clean.txt files with actual data")
    print("3. Re-run extraction: python src/lab5/extract_priority_companies.py")
    print("=" * 60)

if __name__ == "__main__":
    create_templates()

