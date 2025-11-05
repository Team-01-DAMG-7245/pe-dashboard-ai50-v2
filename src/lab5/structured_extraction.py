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
from pathlib import Path

from lab5.models import (
    Company, Event, Snapshot, Product, 
    Leadership, Visibility, Payload, Provenance,
    EventsList, LeadershipList, ProductsList
)

# Import job counting helper
try:
    from lab5.count_jobs_helper import count_jobs_from_careers_text
    HAS_JOB_HELPER = True
except ImportError:
    HAS_JOB_HELPER = False

# Initialize instructor with OpenAI
openai_client = OpenAI()
client = instructor.patch(openai_client)

def read_company_texts(company_id: str) -> Dict[str, str]:
    """Read all text files for a company"""
    # Get project root (3 levels up from lab5/structured_extraction.py)
    project_root = Path(__file__).resolve().parents[2]
    texts = {}
    initial_path = project_root / "data" / "raw" / company_id / "initial"
    
    if not initial_path.exists():
        print(f"No data found for {company_id} at {initial_path}")
        return texts
    
    # Read each text file - prefer clean versions if available
    file_mappings = {
        'about': ['about_clean.txt', 'about.txt'],
        'homepage': ['homepage_clean.txt', 'homepage.txt'],
        'careers': ['careers_clean.txt', 'careers.txt'],
        'blog': ['blog_clean.txt', 'blog.txt'],
        'product': ['product_clean.txt', 'product.txt'],
        'news': ['news_clean.txt', 'news.txt'],
        'linkedin': ['linkedin_clean.txt', 'linkedin.txt']  # LinkedIn data if available
    }
    
    for key, file_options in file_mappings.items():
        for txt_file in file_options:
            file_path = initial_path / txt_file
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    texts[key] = f.read()
                break  # Use first available file
    
    return texts

def extract_company_info(company_id: str, texts: Dict[str, str]) -> Company:
    """Extract company information using LLM - MAXIMUM EXTRACTION MODE"""
    
    # Use FULL text content (no truncation) for maximum extraction
    about_text = texts.get('about', '')
    homepage_text = texts.get('homepage', '')
    blog_text = texts.get('blog', '')
    news_text = texts.get('news', '')
    careers_text = texts.get('careers', '')
    product_text = texts.get('product', '')
    
    # Combine ALL available text sources
    combined_text = f"""
    === ABOUT PAGE (Company Information) ===
    {about_text}
    
    === HOMEPAGE (Main Website Content) ===
    {homepage_text}
    
    === BLOG (Company Blog Posts) ===
    {blog_text}
    
    === NEWS (News & Announcements) ===
    {news_text}
    
    === CAREERS (Job Postings & Company Info) ===
    {careers_text}
    
    === PRODUCT (Product Information) ===
    {product_text}
    """
    
    prompt = f"""You are extracting structured company information from scraped web pages for {company_id}.

    CRITICAL EXTRACTION MODE - Extract MAXIMUM information from the text. Be aggressive and thorough!

    EXTRACTION RULES - READ EVERYTHING CAREFULLY:

    1. legal_name: The official company name
       - Look in: page headers, About section, copyright notices, footer
       - Check: "Company Name", "Legal Name", "Incorporated as", "DBA", "doing business as"
       - Examples: "Anthropic PBC", "Databricks Inc.", "Cohere Inc."
    
    2. website: Full URL with https://
       - Look for: domain names, "visit", "website", "www.", company.com
       - Extract full URL: https://www.company.com or https://company.com
       - Usually found in: footer, contact section, social media links
    
    3. hq_city, hq_state, hq_country: Headquarters location
       - Look for: "headquarters", "HQ", "headquartered in", "based in", "located in", "offices in", "based out of"
       - Also check: "San Francisco", "New York", "Toronto", "London" - often mentioned with context
       - Look in: About page, careers page, contact section, footer
       - Examples: 
         * "Based in San Francisco, CA" → city: "San Francisco", state: "CA", country: "USA"
         * "Headquartered in Toronto, Canada" → city: "Toronto", state: None, country: "Canada"
         * "New York, NY" → city: "New York", state: "NY", country: "USA"
    
    4. founded_year: Year company was founded (INTEGER, 4 digits like 2019, 2020)
       - Look for: "founded in 2019", "founded 2019", "established in", "since 2019", "launched in", "started in", "created in"
       - Also check: "in 2019, we started", "2019 marked the beginning", "since our founding in 2019"
       - Look in: About page, company history section, blog posts about company story
       - Extract the YEAR only (e.g., 2019, not "2019-01-01")
       - If multiple years mentioned, use the founding year (earliest)
    
    5. categories: List of industry/business categories (REQUIRED - extract at least 3-5 categories)
       - Look for: product descriptions, service types, industry tags, company focus
       - Extract from EVERYTHING: product pages, About page, homepage, blog topics
       - Common categories: AI, Machine Learning, Enterprise Software, SaaS, Data Analytics, 
         Cloud Computing, Natural Language Processing, Computer Vision, Healthcare Tech, 
         FinTech, Cybersecurity, Developer Tools, API Platform, Search, etc.
       - Be comprehensive: If company does "AI-powered enterprise search" → ["AI", "Enterprise Software", "Search", "Machine Learning", "SaaS"]
       - If company mentions "we build X, Y, Z" → extract all relevant categories
       - ALWAYS infer categories from product/service descriptions
    
    6. total_raised_usd: Total funding raised (FLOAT, in USD)
       - Search ALL sections: About, Blog, News, homepage
       - Look for: "raised $X", "raised nearly $X", "funding of $X", "raised over $X", "raised $X billion/million"
       - Also check: "total funding", "raised to date", "cumulative funding", "has raised"
       - Convert carefully: "$1 billion" = 1000000000, "$450 million" = 450000000, "$124M" = 124000000
       - If multiple rounds: sum all amounts OR use explicit total if stated
       - Examples: "raised nearly $1 billion" = 1000000000, "raised $450M" = 450000000, "raised $13B" = 13000000000
       - Look for totals: "raised $X across Y rounds" = extract X
    
    7. last_disclosed_valuation_usd: Most recent post-money valuation (FLOAT, in USD)
       - Look for: "valuation", "valued at", "post-money valuation", "worth $X", "$X billion valuation", "at a $X valuation"
       - Also check: "valued at $X", "valuation of $X", "at valuation of $X"
       - Convert to USD: "$183 billion" = 183000000000, "$1.25B" = 1250000000
       - Get the MOST RECENT valuation if multiple mentioned
    
    8. last_round_name: Name of most recent funding round (STRING)
       - Look for: "Series A", "Series B", "Series C", "Series D", "Series E", "Series F", 
         "Series G", "Seed", "Seed Round", "A round", "B round", "Series A funding"
       - Check: recent blog posts, news announcements, press releases
       - Extract exactly as written: "Series F" not "series f"
       - Get the LATEST round if multiple mentioned
    
    9. last_round_date: Date of most recent funding round (DATE, YYYY-MM-DD format)
       - Look for: dates near funding announcements, "on [date]", "announced [date]", "[date] - we raised"
       - Formats: "September 2, 2025" → 2025-09-02, "Sep 2, 2025" → 2025-09-02, "2025-09-02" → 2025-09-02
       - If only year: "in 2024" → 2024-01-01, "2024" → 2024-01-01
       - If date range: use the start date or announcement date
    
    AGGRESSIVE EXTRACTION STRATEGY:
    - Read through ALL text sections carefully
    - Look for information in multiple places (About, Blog, News often have different details)
    - Extract from context clues and descriptions
    - For categories: infer from product descriptions and company focus
    - For funding: check ALL sections, funding info is often in blog/news
    - For location: check About, Careers, Contact sections
    - For founding year: check company history, About page, founder stories
    
    NEVER leave fields as None unless you have thoroughly searched ALL text sections and found NOTHING.
    
    Text to analyze (search through ALL of this):
    {combined_text}
    
    Now extract ALL available information. Be thorough and comprehensive!
    """
    
    try:
        company = client.chat.completions.create(
            model="gpt-4o-mini",  # Using better model for better extraction
            response_model=Company,
            messages=[
                {"role": "system", "content": "You are an expert at extracting structured company information from web pages. Your goal is MAXIMUM EXTRACTION - find every piece of information possible. Search through ALL text sections thoroughly. Extract information from context clues, descriptions, and explicit statements. For categories, infer from product descriptions. For funding, search all sections. For location, check multiple sections. Be aggressive - only leave fields as None if you have searched EVERYWHERE and found NOTHING. Be precise with numbers, dates, and locations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0  # Lower temperature for more consistent extraction
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
    """Extract leadership information using LLM - MAXIMUM EXTRACTION"""
    
    # Use FULL text from multiple sources
    about_text = texts.get('about', '')
    homepage_text = texts.get('homepage', '')
    careers_text = texts.get('careers', '')
    
    combined = f"""
    === ABOUT PAGE (Leadership Info) ===
    {about_text}
    
    === HOMEPAGE (Team Info) ===
    {homepage_text}
    
    === CAREERS (Company Info) ===
    {careers_text}
    """
    
    prompt = f"""Extract leadership team information from the following text.

    SEARCH THOROUGHLY for leadership team members:

    1. Look for sections mentioning:
       - Board of Directors, Leadership Team, Executive Team, Management Team
       - Founders, Co-founders, CEO, CTO, CFO, COO, President, VP, Head of
       - "Our Team", "Leadership", "About Us", "Meet the Team"
    
    2. Extract patterns like:
       - "Founded by [Name1], [Name2], [Name3]" → extract all as Founders
       - "CEO: [Name]", "CTO: [Name]", "CFO: [Name]"
       - "[Name], CEO", "[Name], CTO", "[Name], Founder"
       - "Board of Directors: [Name1], [Name2], [Name3]"
       - "[Name] is the CEO", "[Name] serves as CTO"
       - "[Name] - CEO", "[Name] - Founder and CEO"
    
    3. Common roles to extract:
       - CEO, CTO, CFO, COO, President, Founder, Co-founder
       - Board Member, Director, Executive Director
       - VP (Vice President), Head of, Chief of
       - Chief Technology Officer, Chief Executive Officer, etc.
    
    4. IMPORTANT:
       - Extract ACTUAL PERSON NAMES (first and last name)
       - DO NOT extract product names, technology names, or company names as people
       - Look for full names (e.g., "John Smith", "Jane Doe")
       - If you see "John", "Jane", etc. alone, check if it's clearly a person name in context
       - Extract even if role is not explicitly stated but name is clearly a person
    
    5. For each person, extract:
       - name: Full name (first and last)
       - role: Their role/title (CEO, CTO, Founder, etc.)
       - If multiple roles mentioned, use the primary role
    
    Text to analyze:
    {combined}
    
    Extract ALL leadership team members with their names and roles. Be thorough!
    """
    
    try:
        result = client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=LeadershipList,
            messages=[
                {"role": "system", "content": "Extract actual person names and their roles. Look for sections like 'Board of Directors:', 'Founded by', 'CEO:', 'Leadership Team', etc. Extract ONLY real people's names, not product names, company names, or technologies. If a name seems like a product or technology, skip it."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        
        leaders = result.leadership
        
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
    - Product names (specific branded products, not generic terms)
    - Services or platforms mentioned (with specific names)
    - APIs or developer tools (with specific names)
    - Specific features or offerings (with descriptive names)
    - DO NOT extract generic terms like "AI platform", "software", "service" - only extract named products
    
    {combined}
    
    Return specific product names and descriptions found in the text.
    """
    
    try:
        result = client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=ProductsList,
            messages=[
                {"role": "system", "content": "Extract specific product names and their descriptions. Look for named products, platforms, services, or tools. Extract products that have specific names (not generic terms like 'AI platform' or 'software'). Each product should have a distinct name."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        
        products = result.products
        
        # Set company_id and product_id
        for i, product in enumerate(products):
            product.company_id = company_id
            product.product_id = f"{company_id}_product_{i+1}"
        
        return products
    except Exception as e:
        print(f"Error extracting products: {e}")
        return []

def extract_events(company_id: str, texts: Dict[str, str]) -> List[Event]:
    """Extract events (funding rounds, key announcements) from blog/news - MAXIMUM EXTRACTION"""
    
    # Use FULL text - no truncation for maximum extraction
    about_text = texts.get('about', '')
    blog_text = texts.get('blog', '')
    news_text = texts.get('news', '')
    homepage_text = texts.get('homepage', '')
    combined = f"{about_text} {blog_text} {news_text} {homepage_text}"
    
    if not combined.strip():
        return []
    
    prompt = f"""Extract funding events and key announcements from the following text for company "{company_id}".

    CRITICAL: Look carefully for ALL funding information in the text. Funding info may be in About pages, blog posts, or news sections.

    Look for funding patterns like:
    - "raised $X", "raises $X", "funding of $X", "raised nearly $X billion"
    - "Series A", "Series B", "Series C", "Series D", "Series E", "Series F", "Seed round"
    - "valuation", "valued at", "post-money valuation"
    - Dates: "in 2021", "2021-2024", "between 2021 and 2024", specific dates
    - Investor names or "led by", "investors include"

    Extract EACH distinct funding round as a separate Event.
    
    For each event, you MUST include:
    - company_id: "{company_id}"
    - event_id: A unique identifier (e.g., "1", "2", "3")
    - event_type: "funding" for funding rounds
    - title: Brief descriptive title (e.g., "Series A funding round")
    - occurred_on: Date (YYYY-MM-DD). If only year given, use YYYY-01-01. If range given, use start date.
    
    For funding events, also extract:
    - round_name: Exact round name (e.g., "Series A", "Series B", "Series C", "Series D")
    - amount_usd: Amount in USD (convert: "$1 billion" = 1000000000, "$450 million" = 450000000, "$124M" = 124000000)
    - valuation_usd: Post-money valuation if mentioned
    - investors: List of investor names if mentioned

    Example 1: "Between 2021 and 2024, we secured four major funding rounds (Series A through D), raising nearly $1 billion"
    Should extract 4 separate events:
    - Event 1: Series A, occurred_on: 2021-01-01, amount_usd: 250000000 (estimated 1/4 of total)
    - Event 2: Series B, occurred_on: 2022-01-01, amount_usd: 250000000
    - Event 3: Series C, occurred_on: 2023-01-01, amount_usd: 250000000
    - Event 4: Series D, occurred_on: 2024-01-01, amount_usd: 250000000

    Example 2: "Company raises $13B Series F at $183B post-money valuation Sep 02, 2025"
    Should extract:
    - company_id: "{company_id}"
    - event_id: "1"
    - event_type: "funding"
    - title: "Series F funding round"
    - round_name: "Series F"
    - amount_usd: 13000000000
    - valuation_usd: 183000000000
    - occurred_on: 2025-09-02

    Text to analyze (search through ALL of this):
    {combined}
    
    CRITICAL: Extract ALL funding rounds mentioned. Search through EVERY section carefully.
    - If you see "Series A through D" or "four funding rounds", extract each one separately
    - If you see "raised $1B across 4 rounds", extract each round if details are available
    - Look for funding info in About page, blog posts, news articles, homepage announcements
    - Extract even if only partially mentioned (e.g., "Series F" with date but no amount)
    - Be thorough - funding information might be scattered across multiple sections
    
    Return ALL events with actual information found. Be comprehensive!
    """
    
    try:
        result = client.chat.completions.create(
            model="gpt-4o-mini",  # Using better model for better extraction
            response_model=EventsList,
            messages=[
                {"role": "system", "content": "You are an expert at extracting funding events and company announcements. Extract ALL funding rounds mentioned in the text, even if only briefly mentioned. Look carefully for funding patterns, dates, amounts, and round names. Convert all amounts to USD. Extract multiple events if multiple rounds are mentioned."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0  # Lower temperature for more consistent extraction
        )
        
        events = result.events
        
        # Ensure company_id and event_id are set for each event
        for i, event in enumerate(events):
            if not event.company_id:
                event.company_id = company_id
            if not event.event_id:
                event.event_id = f"{company_id}_event_{i+1}"
        
        return events
    except Exception as e:
        print(f"Error extracting events: {e}")
        return []

def extract_snapshot(company_id: str, texts: Dict[str, str]) -> Snapshot:
    """Extract current snapshot information - MAXIMUM EXTRACTION with LinkedIn-aware extraction"""
    
    # Use FULL text from multiple sources
    careers_text = texts.get('careers', '')
    about_text = texts.get('about', '')
    homepage_text = texts.get('homepage', '')
    blog_text = texts.get('blog', '')
    news_text = texts.get('news', '')
    linkedin_text = texts.get('linkedin', '')  # LinkedIn data if available
    
    combined = f"""
    === LINKEDIN DATA (Most Reliable for Growth Metrics) ===
    {linkedin_text}
    
    === CAREERS PAGE (Primary Source for Job Listings) ===
    {careers_text}
    
    === ABOUT PAGE (Company Info & Team Size) ===
    {about_text}
    
    === HOMEPAGE (Company Info) ===
    {homepage_text}
    
    === BLOG (Growth Announcements) ===
    {blog_text}
    
    === NEWS (Company Updates) ===
    {news_text}
    """
    
    prompt = f"""Extract current company metrics and Growth Momentum information from the following text for {company_id}.

    CRITICAL: This is for Growth Momentum analysis. Extract ALL available metrics!

    SEARCH THOROUGHLY for Growth Momentum fields:
    
    1. headcount_total: Number of employees or team size (CRITICAL FIELD)
       - PRIORITY: Check LinkedIn data section first - it often has accurate company size
       - Look for: "201-500 employees", "50-100 employees", "1000+ employees" (convert to midpoint or max)
       - Look for EXACT patterns: "X employees", "team of X", "X people", "X team members", "X+ employees", "X-person team"
       - Also check: "we're a team of X", "over X employees", "X colleagues", "X staff", "X workers"
       - Look for: "company of X", "X-person company", "team size of X", "currently X employees"
       - Check LinkedIn-style mentions: "X employees on LinkedIn", "X followers" (if mentioned with context)
       - Look in: LinkedIn data (if available), About page, Careers page, company announcements, blog posts
       - Extract the NUMBER (integer) - be precise!
       - Examples: 
         * "201-500 employees" → use midpoint (350) or max (500)
         * "50 employees" → 50
         * "team of 100+" → 100
         * "over 200 employees" → 200
    
    2. headcount_growth_pct: Growth percentage if mentioned
       - Look for: "grew X%", "X% growth", "growing X%", "X% increase", "grown X%", "X% YoY growth"
       - Also check: "doubled in size", "tripled", "10x growth" (convert to percentages)
       - Look for: "from X to Y employees" (calculate growth %)
       - Examples: "grew 50%" → 50.0, "doubled" → 100.0, "from 50 to 150" → 200.0
    
    3. job_openings_count: Number of open positions (CRITICAL FIELD - COUNT EVERY JOB!)
       - COUNT EVERY job listing you see! Look for job titles followed by location and "Apply"
       - Pattern: "Job Title" followed by "Location" followed by "Apply" = 1 job
       - Look for: "X open positions", "X roles", "X jobs", "we're hiring X", "X openings" (but prefer counting actual listings)
       - CRITICAL: Go through the careers page section by section and COUNT:
         * Each unique job title (e.g., "Account Executive", "Software Engineer", "AI Strategist")
         * Jobs are usually listed as: "Job Title" on one line, "Location" on next, "Apply" on next
         * Count ALL job titles you see, even if they're in different departments
       - Look for department sections (GTM, AI Strategy, Engineering, Sales, Marketing, Design, etc.) and count jobs in each
       - Extract the NUMBER (integer) - count ALL unique positions individually!
       - Examples: 
         * If you see "Account Executive" → count 1
         * If you see "Software Engineer" and "Frontend Engineer" → count 2
         * If you see 20 different job titles → count 20
         * If text says "56 open positions" but you count 60 jobs, use 60 (the actual count)
    
    4. engineering_openings: Number of engineering/technical roles
       - Look for: "Software Engineer", "Engineering", "Developer", "Tech", "Engineering Manager", "Data Engineer", etc.
       - Count all engineering-related positions
       - Extract the NUMBER (integer)
    
    5. sales_openings: Number of sales roles
       - Look for: "Sales", "Account Executive", "Business Development", "Sales Manager", "Account Manager"
       - Count all sales-related positions
       - Extract the NUMBER (integer)
    
    6. hiring_focus: List of departments/teams actively hiring (CRITICAL FIELD)
       - Look for: "Engineering", "Sales", "Marketing", "Product", "Design", "Operations", "GTM", "AI Strategy"
       - Extract from: "hiring in Engineering", "open roles in Sales and Marketing", department sections
       - Look at job listings and group by department
       - Extract: ["Engineering", "Sales", "Marketing", etc.] - list ALL departments hiring
       - Examples: If you see Engineering jobs and Sales jobs → ["Engineering", "Sales"]
    
    7. departments_hiring: (This is the same as hiring_focus - use hiring_focus)
       - Same as hiring_focus above
    
    8. geo_presence: Geographic locations/offices
       - Look for: office locations, "offices in", "located in", city names, "New York", "San Francisco", "London"
       - Extract from: job listings (location field), About page, Careers page
       - Extract: ["San Francisco", "New York", "Toronto", "London", etc.] - list ALL locations
       - Examples: "New York City" → ["New York"], "London, UK; New York City" → ["London", "New York"]
    
    9. active_products: List of products/services
       - Look for: product names, service offerings, platform names
       - Extract from: About page, homepage, product page
    
    10. pricing_tiers: Pricing information if mentioned
        - Look for: pricing plans, tiers, "Free", "Pro", "Enterprise", etc.
        - Extract: ["Free", "Pro", "Enterprise"] or similar
    
    AGGRESSIVE EXTRACTION STRATEGY:
    - For headcount: Search ALL sections, especially About and Careers pages
    - For job_openings_count: COUNT every unique job listing you see - be thorough!
    - For hiring_focus: Look at job categories and department names
    - For growth_pct: Look in blog posts and news for growth announcements
    - If you see "See open roles" or similar, look for actual job listings below
    - Count job titles explicitly mentioned in the careers page
    
    LINKEDIN DATA INTEGRATION NOTE:
    - If you see LinkedIn mentions (e.g., "X employees on LinkedIn", "LinkedIn shows X employees"), extract those numbers
    - Look for company size mentions that might be from LinkedIn
    
    Text to analyze (search through ALL of this carefully):
    {combined}
    
    Extract ALL metrics and information you find. Be extremely thorough, especially for headcount and job openings!
    Count every job listing you see. Extract all departments hiring. Be comprehensive!
    """
    
    try:
        snapshot = client.chat.completions.create(
            model="gpt-4o-mini",
            response_model=Snapshot,
            messages=[
                {"role": "system", "content": "You are an expert at extracting Growth Momentum metrics from company pages. Your goal is MAXIMUM EXTRACTION - especially for headcount, job openings, and hiring focus. COUNT every job listing you see. Extract all departments hiring. Look for employee counts in all sections. Search for growth percentages. Be extremely thorough - extract everything related to company size, hiring, and growth. Only leave fields as None if you have searched EVERYWHERE and found NOTHING."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        
        snapshot.company_id = company_id
        snapshot.as_of = date.today()
        
        # Use helper function to validate/improve job counts if available
        if HAS_JOB_HELPER and careers_text:
            job_counts = count_jobs_from_careers_text(careers_text)
            # If helper found more jobs than LLM, use helper's count
            if job_counts['total'] > 0:
                if not snapshot.job_openings_count or job_counts['total'] > snapshot.job_openings_count:
                    snapshot.job_openings_count = job_counts['total']
                if not snapshot.engineering_openings or job_counts['engineering'] > snapshot.engineering_openings:
                    snapshot.engineering_openings = job_counts['engineering']
                if not snapshot.sales_openings or job_counts['sales'] > snapshot.sales_openings:
                    snapshot.sales_openings = job_counts['sales']
                # Update hiring_focus with departments found
                if job_counts['departments'] and not snapshot.hiring_focus:
                    snapshot.hiring_focus = job_counts['departments']
        
        # Fix provenance URLs to be full URLs
        for prov in snapshot.provenance:
            if prov.source_url and not prov.source_url.startswith(('http://', 'https://')):
                prov.source_url = f"https://{prov.source_url}"
        
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
    
    print("  Extracting events (funding rounds, announcements)...")
    events = extract_events(company_id, texts)
    
    print("  Extracting leadership...")
    leadership = extract_leadership(company_id, texts)
    
    print("  Extracting products...")
    products = extract_products(company_id, texts)
    
    print("  Extracting snapshot...")
    snapshot = extract_snapshot(company_id, texts)
    
    # Update company-level fields from events if missing or improve them
    if events:
        # Sort events by date (most recent first)
        sorted_events = sorted([e for e in events if e.occurred_on], 
                              key=lambda x: x.occurred_on, reverse=True)
        
        # Get most recent funding event
        funding_events = [e for e in sorted_events if e.event_type == 'funding' and e.round_name]
        if funding_events:
            latest = funding_events[0]
            # Always update with most recent if we have events
            if latest.round_name:
                company.last_round_name = latest.round_name
            if latest.occurred_on:
                company.last_round_date = latest.occurred_on
            if latest.valuation_usd:
                company.last_disclosed_valuation_usd = latest.valuation_usd
        
        # Calculate total raised from all funding events (use sum if we have multiple events)
        total_from_events = sum([e.amount_usd for e in events if e.amount_usd and e.amount_usd > 0])
        if total_from_events > 0:
            # Use events total if it's larger or if company doesn't have one
            if not company.total_raised_usd or total_from_events > company.total_raised_usd:
                company.total_raised_usd = total_from_events
    
    # Create payload
    payload = Payload(
        company_record=company,
        events=events,
        snapshots=[snapshot] if snapshot else [],
        products=products,
        leadership=leadership,
        visibility=[],  # Would need external data
        notes=f"Extracted from scraped data on {date.today()}. Events: {len(events)} funding/announcement events found.",
        provenance_policy="Use only the sources you scraped. If a field is missing, write 'Not disclosed.' Do not infer valuation."
    )
    
    # Convert to dict for JSON serialization
    result = payload.model_dump(mode='json')
    
    # Save to file
    # Get project root for output
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "data" / "structured"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"{company_id}.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"  [OK] Saved to {output_path}")
    print(f"     - Company: {company.legal_name}")
    print(f"     - Founded: {company.founded_year or 'Not found'}")
    print(f"     - Total Raised: ${company.total_raised_usd/1e9:.2f}B" if company.total_raised_usd else "     - Total Raised: Not found")
    print(f"     - Events: {len(events)}")
    print(f"     - Leaders: {len(leadership)}")
    print(f"     - Products: {len(products)}")
    
    return result

def main():
    """Process all companies with structured data for Lab 5"""
    
    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw"
    
    # Get all companies with raw data
    if raw_dir.exists():
        companies = [d.name for d in raw_dir.iterdir() if d.is_dir() and (d / "initial").exists()]
        companies = sorted(companies)
    else:
        companies = ['anthropic', 'databricks', 'glean', 'cohere', 'openevidence']
    
    print("=" * 60)
    print("LAB 5: STRUCTURED EXTRACTION")
    print("=" * 60)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n[ERROR] OPENAI_API_KEY environment variable not set!")
        print("Please set it: export OPENAI_API_KEY='your-key-here'")
        return
    
    print(f"\nProcessing {len(companies)} companies...\n")
    
    results = []
    for company_id in companies:
        result = process_company(company_id)
        if result:
            results.append(result)
    
    output_dir = project_root / "data" / "structured"
    print("\n" + "=" * 60)
    print(f"[OK] LAB 5 COMPLETE!")
    print(f"   Processed {len(results)}/{len(companies)} companies")
    print(f"   Output saved to {output_dir}/")
    print("=" * 60)

if __name__ == "__main__":
    main()