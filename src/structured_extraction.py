"""
Lab 5: Structured extraction with Pydantic and Instructor
Extracts structured data from scraped company text using LLM
Updated version with better extraction prompts
"""

import os
import json
import instructor
from openai import OpenAI
from typing import Dict, List
from datetime import date, datetime
from pydantic import ValidationError

from models import (
    Company, Event, Snapshot, Product, 
    Leadership, Visibility, Payload, Provenance
)

# Initialize instructor with OpenAI
client = instructor.from_openai(OpenAI())

def read_company_texts(company_id: str) -> Dict[str, str]:
    """Read all text files for a company"""
    texts = {}
    initial_path = f"data/raw/{company_id}/initial"
    
    if not os.path.exists(initial_path):
        print(f"No data found for {company_id}")
        return texts
    
    # Read each text file
    for txt_file in ['about.txt', 'homepage.txt', 'careers.txt', 'blog.txt', 'product.txt']:
        file_path = os.path.join(initial_path, txt_file)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                texts[txt_file.replace('.txt', '')] = f.read()
    
    return texts

def extract_company_info(company_id: str, texts: Dict[str, str]) -> Company:
    """Extract company information using LLM"""
    
    combined_text = f"""
    About: {texts.get('about', '')[:3000]}
    Homepage: {texts.get('homepage', '')[:2000]}
    Careers: {texts.get('careers', '')[:1000]}
    """
    
    prompt = f"""Extract company information from the following text about {company_id}.
    
    IMPORTANT: Look carefully for these specific items:
    
    1. Website URL: Look for patterns like "anthropic.com", "www.{company_id}.com", "visit us at", "our website"
       If you see "{company_id}.com" mentioned anywhere, set website to "https://{company_id}.com"
    
    2. Headquarters: Look for:
       - "based in [city]", "located in [city]", "headquarters in [city]"
       - "offices in [city]", "[City] office", "[City], [State/Country]"
       - Common tech hubs: San Francisco, Palo Alto, New York, London, Seattle
    
    3. Founded Year: Look for:
       - "founded in [year]", "established [year]", "since [year]"
       - "started in [year]", "[year] startup", "launched in [year]"
    
    4. Funding Information: Look for:
       - "$X million", "$X billion", "raised $X", "Series A/B/C"
       - "valued at $X", "valuation of $X", "$X in funding"
       - Convert text amounts: "124 million" = 124000000
    
    5. Company Categories: Look for industry terms like:
       - "AI", "machine learning", "artificial intelligence"
       - "enterprise software", "SaaS", "platform", "cloud"
    
    Text to analyze:
    {combined_text}
    
    Extract any partial information you find. If unsure about exact format, make reasonable inferences based on context.
    """
    
    try:
        company = client.chat.completions.create(
            model="gpt-4o-mini",  # Better model for extraction
            response_model=Company,
            messages=[
                {"role": "system", "content": "Extract company information. If you see partial info, extract it. For example, if text mentions 'San Francisco', set hq_city='San Francisco'. If it mentions '2021', set founded_year=2021."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # Set required fields
        company.company_id = company_id
        company.as_of = date.today()
        
        # Set website if not found but company name is known
        if not company.website and company_id:
            company.website = f"https://{company_id.replace('_', '')}.com"
        
        # Set legal name if not found
        if not company.legal_name:
            company.legal_name = company_id.replace('_', ' ').title()
        
        return company
    except Exception as e:
        print(f"Error extracting company info: {e}")
        return Company(
            company_id=company_id,
            legal_name=company_id.replace('_', ' ').title(),
            website=f"https://{company_id.replace('_', '')}.com",
            as_of=date.today()
        )

def extract_leadership(company_id: str, texts: Dict[str, str]) -> List[Leadership]:
    """Extract leadership information using LLM"""
    
    # Combine multiple sources for better extraction
    combined_text = f"""
    About Page: {texts.get('about', '')[:3000]}
    Homepage: {texts.get('homepage', '')[:1500]}
    """
    
    prompt = f"""Extract leadership team information from the following text.
    
    CRITICAL: Extract ALL people mentioned with titles. Look for:
    
    1. Board of Directors section - extract ALL names listed
    2. Leadership/Team sections - extract ALL executives
    3. Founders - anyone described as "founded by", "co-founder"
    4. C-Suite: CEO, CTO, CFO, COO, CMO, CPO, etc.
    5. VPs and SVPs: "VP of", "SVP of", "Vice President"
    6. Other leaders: "Head of", "Director of", "General Manager"
    
    EXAMPLES to look for:
    - "Board of Directors: Dario Amodei, Daniela Amodei" → Extract both as Board Members
    - "Founded by Sam Altman" → Extract as Founder
    - "CEO John Smith" → Extract as CEO
    - "Our leadership team includes..." → Extract all names that follow
    
    Text to analyze:
    {combined_text}
    
    Extract EVERY person with a title. Include founders, board members, executives, and senior leaders.
    """
    
    try:
        leaders = client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=List[Leadership],
            messages=[
                {"role": "system", "content": "Extract ALL people with titles. Be thorough - include board members, founders, executives, VPs, directors. If someone has multiple roles, use their highest role."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_retries=2
        )
        
        # Set company_id and person_id
        for leader in leaders:
            leader.company_id = company_id
            leader.person_id = f"{company_id}_{leader.name.lower().replace(' ', '_')}"
            
            # Set is_founder flag
            if 'founder' in leader.role.lower():
                leader.is_founder = True
        
        return leaders
    except Exception as e:
        print(f"Error extracting leadership: {e}")
        return []

def extract_products(company_id: str, texts: Dict[str, str]) -> List[Product]:
    """Extract product information using LLM"""
    
    combined = f"""
    Product Page: {texts.get('product', '')[:3000]}
    Homepage: {texts.get('homepage', '')[:2000]}
    About: {texts.get('about', '')[:1000]}
    """
    
    if not combined.strip():
        return []
    
    prompt = f"""Extract ALL products and services from the following text.
    
    Look for:
    1. Named products: Claude, GPT-4, Databricks SQL, etc.
    2. Platforms: "X Platform", "X Cloud", "X Suite"
    3. APIs: "X API", "Developer API", "REST API"
    4. Services: "X Service", "managed X", "X solution"
    5. Tools: "X Tool", "X Builder", "X Studio"
    6. Models: AI models, ML models, language models
    7. Features described as products
    
    Include:
    - Main products (prominently featured)
    - Sub-products or product variations
    - Developer tools and APIs
    - Enterprise solutions
    - Any named offering with a capital letter
    
    Text to analyze:
    {combined}
    
    Extract ALL products, services, and tools mentioned. Include brief descriptions.
    """
    
    try:
        products = client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=List[Product],
            messages=[
                {"role": "system", "content": "Extract ALL products, platforms, APIs, and services. Be comprehensive - if it has a product name or is described as an offering, include it."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # Set IDs and clean up
        for i, product in enumerate(products):
            product.company_id = company_id
            product.product_id = f"{company_id}_product_{i+1}"
            
            # Set schema version if not set
            if not hasattr(product, 'schema_version'):
                product.schema_version = "2.0.0"
        
        return products
    except Exception as e:
        print(f"Error extracting products: {e}")
        return []

def extract_snapshot(company_id: str, texts: Dict[str, str]) -> Snapshot:
    """Extract current snapshot information"""
    
    careers_text = texts.get('careers', '')[:4000]
    about_text = texts.get('about', '')[:2000]
    
    prompt = f"""Extract current company metrics and status from the following text.
    
    Look for:
    1. Employee count: "X employees", "team of X", "X+ people", "X-person team"
    2. Job openings: "X open positions", "hiring for X roles", "X jobs"
    3. Office locations: Cities mentioned as office locations
    4. Growth metrics: "X% growth", "doubled in size", "growing by X"
    5. Departments hiring: Engineering, Sales, Marketing, Product, etc.
    6. Geographic presence: Countries or regions with offices
    
    Careers page:
    {careers_text}
    
    About page:
    {about_text}
    
    Extract specific numbers and metrics. If you see "100+ employees", set headcount_total=100.
    """
    
    try:
        snapshot = client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=Snapshot,
            messages=[
                {"role": "system", "content": "Extract company metrics and current status. Look for employee counts, job openings, office locations, and growth indicators. Extract actual numbers when available."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        snapshot.company_id = company_id
        snapshot.as_of = date.today()
        
        return snapshot
    except Exception as e:
        print(f"Error extracting snapshot: {e}")
        return Snapshot(
            company_id=company_id,
            as_of=date.today()
        )

def process_company(company_id: str) -> Dict:
    """Process a single company and extract all structured data"""
    
    print(f"\nProcessing {company_id}...")
    
    # Read company texts
    texts = read_company_texts(company_id)
    
    if not texts:
        print(f"  No text data found for {company_id}")
        return None
    
    print(f"  Found {len(texts)} text files")
    
    # Extract structured data
    print("  Extracting company info...")
    company = extract_company_info(company_id, texts)
    
    print("  Extracting leadership...")
    leadership = extract_leadership(company_id, texts)
    
    print("  Extracting products...")
    products = extract_products(company_id, texts)
    
    print("  Extracting snapshot...")
    snapshot = extract_snapshot(company_id, texts)
    
    # Create payload
    payload = Payload(
        company_record=company,
        events=[],
        snapshots=[snapshot] if snapshot else [],
        products=products,
        leadership=leadership,
        visibility=[],
        notes=f"Extracted from scraped data on {date.today()}",
        provenance_policy="Use only the sources you scraped. If a field is missing, write 'Not disclosed.' Do not infer valuation."
    )
    
    # Convert to dict
    result = payload.model_dump(mode='json')
    
    # Save to file
    output_dir = "data/structured"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = f"{output_dir}/{company_id}.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    # Print summary
    print(f"  ✅ Saved to {output_path}")
    print(f"     - Company: {company.legal_name}")
    print(f"     - Website: {company.website}")
    print(f"     - HQ: {company.hq_city}, {company.hq_state}")
    print(f"     - Founded: {company.founded_year}")
    print(f"     - Leaders: {len(leadership)}")
    print(f"     - Products: {len(products)}")
    
    return result

def main():
    """Process 5 test companies for Lab 5"""
    
    # Test companies
    test_companies = ['anthropic', 'databricks', 'glean', 'cohere', 'openevidence']
    
    print("=" * 60)
    print("LAB 5: STRUCTURED EXTRACTION (ENHANCED)")
    print("=" * 60)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY environment variable not set!")
        print("Please set it: export OPENAI_API_KEY='your-key-here'")
        return
    
    results = []
    for company_id in test_companies:
        result = process_company(company_id)
        if result:
            results.append(result)
    
    print("\n" + "=" * 60)
    print(f"✅ LAB 5 COMPLETE!")
    print(f"   Processed {len(results)}/{len(test_companies)} companies")
    print(f"   Output saved to data/structured/")
    print("=" * 60)

if __name__ == "__main__":
    main()