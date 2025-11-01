"""
Lab 5: Structured extraction with Pydantic and Instructor
Extracts structured data from scraped company text using LLM
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
    About: {texts.get('about', '')[:2000]}
    Homepage: {texts.get('homepage', '')[:2000]}
    """
    
    prompt = f"""Extract company information from the following text about {company_id}.
    Look for: company name, website URL, headquarters location, founded year, funding information.
    Return ONLY information explicitly stated in the text. Leave fields as None if not found.
    
    {combined_text}
    """
    
    try:
        company = client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_model=Company,
            messages=[
                {"role": "system", "content": "Extract only factual information present in the text. Look for specific details like URLs, cities, years, and dollar amounts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # Set company_id
        company.company_id = company_id
        company.as_of = date.today()
        
        return company
    except Exception as e:
        print(f"Error extracting company info: {e}")
        return Company(
            company_id=company_id,
            legal_name=company_id.replace('_', ' ').title(),
            as_of=date.today()
        )

def extract_leadership(company_id: str, texts: Dict[str, str]) -> List[Leadership]:
    """Extract leadership information using LLM"""
    
    about_text = texts.get('about', '')
    
    prompt = f"""Extract leadership team information from the following text.
    
    IMPORTANT INSTRUCTIONS:
    1. Look for sections mentioning Board of Directors, Leadership, Team, Founders, CEO, CTO, etc.
    2. Extract ACTUAL NAMES, not placeholders
    3. Look for patterns like "Board of Directors: [names]" or "Founded by [names]"
    4. Common roles to look for: CEO, CTO, CFO, Founder, Co-founder, Board Member, Director
    
    For example, if you see "Anthropic Board of Directors: Dario Amodei, Daniela Amodei", 
    extract Dario Amodei as a Board Member and Daniela Amodei as a Board Member.
    
    Text to analyze:
    {about_text[:4000]}
    
    Return ONLY people with their actual names explicitly mentioned in the text.
    """
    
    try:
        leaders = client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_model=List[Leadership],
            messages=[
                {"role": "system", "content": "Extract actual names and roles. Look for 'Board of Directors:', 'Founded by', 'CEO:', etc. Do not use placeholders."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # Set company_id for each leader
        for leader in leaders:
            leader.company_id = company_id
            leader.person_id = f"{company_id}_{leader.name.lower().replace(' ', '_')}"
        
        return leaders
    except Exception as e:
        print(f"Error extracting leadership: {e}")
        return []

def extract_products(company_id: str, texts: Dict[str, str]) -> List[Product]:
    """Extract product information using LLM"""
    
    product_text = texts.get('product', '')
    homepage_text = texts.get('homepage', '')
    
    combined = f"{product_text[:2000]} {homepage_text[:1000]}"
    
    if not combined.strip():
        return []
    
    prompt = f"""Extract product information from the following text.
    
    Look for:
    - Product names (e.g., Claude, GPT, Databricks SQL)
    - Services or platforms mentioned
    - APIs or developer tools
    - Specific features or offerings
    
    {combined}
    
    Return specific product names and descriptions found in the text.
    """
    
    try:
        products = client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_model=List[Product],
            messages=[
                {"role": "system", "content": "Extract specific product names and descriptions. Look for capitalized product names, platforms, or services."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        # Set company_id and product_id
        for i, product in enumerate(products):
            product.company_id = company_id
            product.product_id = f"{company_id}_product_{i+1}"
        
        return products
    except Exception as e:
        print(f"Error extracting products: {e}")
        return []

def extract_snapshot(company_id: str, texts: Dict[str, str]) -> Snapshot:
    """Extract current snapshot information"""
    
    careers_text = texts.get('careers', '')[:3000]
    
    prompt = f"""Extract current company metrics from the following careers page text.
    
    Look for:
    - Number of employees or team size
    - Number of job openings
    - Departments hiring (Engineering, Sales, etc.)
    - Office locations
    - Benefits or perks mentioned
    
    {careers_text}
    
    Extract any numbers or metrics you find.
    """
    
    try:
        snapshot = client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_model=Snapshot,
            messages=[
                {"role": "system", "content": "Extract company metrics, job counts, and hiring information. Look for specific numbers."},
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
        events=[],  # Events would need news/blog parsing
        snapshots=[snapshot] if snapshot else [],
        products=products,
        leadership=leadership,
        visibility=[],  # Would need external data
        notes=f"Extracted from scraped data on {date.today()}",
        provenance_policy="Use only the sources you scraped. If a field is missing, write 'Not disclosed.' Do not infer valuation."
    )
    
    # Convert to dict for JSON serialization
    result = payload.model_dump(mode='json')
    
    # Save to file
    output_dir = "data/structured"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = f"{output_dir}/{company_id}.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"  ✅ Saved to {output_path}")
    print(f"     - Company: {company.legal_name}")
    print(f"     - Leaders: {len(leadership)}")
    print(f"     - Products: {len(products)}")
    
    return result

def main():
    """Process 5 test companies for Lab 5"""
    
    # Test companies
    test_companies = ['anthropic', 'databricks', 'glean', 'cohere', 'openevidence']
    
    print("=" * 60)
    print("LAB 5: STRUCTURED EXTRACTION")
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