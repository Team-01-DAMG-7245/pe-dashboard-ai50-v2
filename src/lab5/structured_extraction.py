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
from dotenv import load_dotenv

from lab5.models import (
    Company, Event, Snapshot, Product, 
    Leadership, Visibility, Payload, Provenance,
    EventsList, LeadershipList, ProductsList
)

# Load environment variables from .env file
project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Also try loading from current directory
    load_dotenv()

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
    
    GROWTH MOMENTUM METRICS (CRITICAL - Extract these):
    
    11. headcount_velocity: How fast is the company hiring? (STRING)
       - Look for: hiring announcements, growth rates, "doubling team size", "growing rapidly"
       - Extract: "Rapid" (doubling in <12 months), "Moderate" (20-50% growth), "Slow" (<20%), "Stable" (minimal growth)
       - Consider: job openings count relative to headcount, growth announcements
    
    12. headcount_growth_rate: Annual headcount growth percentage (FLOAT)
       - Look for: "grew from X to Y in Z months", "doubled team size", "50% growth"
       - Calculate if you see: "from 100 to 200 employees in 12 months" → 100.0%
       - Extract percentage if explicitly mentioned
    
    13. release_velocity: How frequently are products/features released? (STRING)
       - Look for: product launches, feature releases, "new product every X months"
       - Extract: "High" (multiple releases/month), "Medium" (monthly), "Low" (quarterly or less)
       - Consider: number of products, frequency of announcements
    
    14. products_released_last_12m: Number of products/features released in last 12 months (INTEGER)
       - Count product launches, major features, new offerings mentioned
       - Look in: blog posts, news, product announcements
       - Extract actual count if mentioned
    
    15. geography_expansion: New geographic locations/regions (LIST of strings)
       - Look for: "opening office in X", "expanding to Y", "new location in Z"
       - Extract: ["Europe", "Asia-Pacific", "New York", "London", etc.]
       - Look for: international expansion, new office openings, global presence
    
    16. geography_expansion_rate: How fast is geographic expansion? (STRING)
       - Extract: "Rapid" (multiple new locations recently), "Moderate" (1-2 new locations), "Slow" (minimal expansion)
    
    DURABILITY INDICATORS (CRITICAL - Extract these):
    
    17. notable_customers: Well-known customers/partners (LIST of strings)
       - Look for: "customers include", "partners with", Fortune 500 mentions, big brand names
       - Extract: ["Company A", "Company B", "Fortune 500", etc.]
       - Look in: About page, homepage, case studies, press releases
    
    18. customer_quality_score: Type of customers (STRING)
       - Extract: "Enterprise" (large companies), "Mid-market" (medium businesses), "SMB" (small businesses), "Mixed"
       - Look for: enterprise sales, SMB focus, customer segments mentioned
    
    19. churn_signals: Customer retention issues (LIST of strings)
       - Look for: "churn", "customer retention", "lost customers", retention challenges
       - Extract any mentions of customer loss or retention issues
       - If none mentioned, leave empty
    
    20. regulatory_exposure: Regulatory risks or compliance issues (LIST of strings)
       - Look for: "regulation", "compliance", "regulatory", "GDPR", "CCPA", "AI regulation"
       - Extract: ["GDPR", "AI Safety", "Data Privacy", etc.]
       - Look for: regulatory mentions, compliance challenges, industry regulations
    
    21. leadership_stability: Leadership team stability (STRING)
       - Extract: "Stable" (founders still there, low turnover), "Growing" (adding leaders), "High turnover" (if mentioned)
       - Consider: founder presence, leadership changes, team growth
    
    22. leadership_changes_last_12m: Number of leadership changes in last 12 months (INTEGER)
       - Count: new executives hired, departures mentioned, leadership announcements
       - Look in: news, blog posts, press releases
    
    RISK & CHALLENGES (CRITICAL - Extract these):
    
    23. layoffs_mentioned: Whether layoffs are mentioned (BOOLEAN)
       - Look for: "layoffs", "reduction in force", "RIF", "workforce reduction", "downsizing", "restructuring"
       - Check: Layoffs.fyi mentions, news articles, blog posts
       - Extract: true if mentioned, false if not
    
    24. layoffs_count: Number of employees laid off (INTEGER)
       - Look for: "laid off X employees", "cutting X jobs", "X% of workforce"
       - Extract the NUMBER if mentioned
    
    25. layoffs_date: Date of layoffs (DATE)
       - Look for: "announced layoffs on [date]", "in [month/year]", recent layoff announcements
       - Extract date if mentioned
    
    26. layoffs_percentage: Percentage of workforce laid off (FLOAT)
       - Look for: "X% of workforce", "cutting X%", "reducing by X%"
       - Extract percentage if mentioned
    
    27. positive_signals: Positive news/events (LIST of strings)
       - Look for: product launches, partnerships, funding rounds, customer wins, awards, expansions
       - Extract: ["Product X launched", "Partnership with Company Y", "Raised $X", "Won award Z", etc.]
       - Look in: blog posts, news, press releases, announcements
    
    28. negative_signals: Negative news/events (LIST of strings)
       - Look for: layoffs, customer churn, regulatory issues, lawsuits, security breaches, negative press
       - Extract: ["Layoffs announced", "Lost major customer", "Regulatory investigation", etc.]
       - Look in: news, blog posts, press releases
    
    29. key_challenges: Identified challenges and risks (LIST of strings)
       - Look for: market challenges, competition, regulatory hurdles, technical challenges, scaling issues
       - Extract: ["Regulatory compliance", "Market competition", "Scaling challenges", etc.]
       - Consider: regulatory exposure, churn signals, leadership turnover, layoffs
    
    TRANSPARENCY & DISCLOSURE GAPS (CRITICAL - Analyze these):
    
    30. marketed_info_available: What information is publicly marketed/claimed (LIST of strings)
       - Look for: marketing claims, feature descriptions, benefits, value propositions
       - Extract: ["Enterprise AI platform", "Serves Fortune 500", "99.9% uptime", "AI-powered search", etc.]
       - Look in: homepage, product pages, marketing materials, about page
    
    31. actual_case_studies: Actual proof points, case studies, customer testimonials (LIST of strings)
       - Look for: case studies, customer testimonials, "used by", "customers include", specific examples
       - Extract: ["Case study with Company X", "Customer testimonial from Company Y", "Used by Z companies", etc.]
       - Look in: case studies page, testimonials, customer success stories, press releases
       - Focus on SPECIFIC examples, not just claims
    
    32. missing_key_info: Critical information that should be disclosed but isn't (LIST of strings)
       - Check for missing: pricing information, customer count, revenue, metrics, team size, location details
       - Extract: ["Pricing not disclosed", "Customer count not available", "Revenue not disclosed", "Team size unclear", etc.]
       - Look for: "Not disclosed", "Contact us", vague statements instead of specific numbers
    
    33. disclosure_gaps: Gaps between what's marketed and what's proven (LIST of strings)
       - Compare: marketed claims vs actual case studies
       - Identify: ["Claims enterprise customers but no case studies", "Marketing claims not backed by proof", etc.]
       - Look for: bold claims without evidence, missing customer names, vague metrics
    
    Text to analyze (search through ALL of this carefully):
    {combined}
    
    Extract ALL metrics and information you find. Be extremely thorough, especially for Growth Momentum, Durability indicators, and Risk & Challenges!
    Count every job listing you see. Extract all departments hiring. Identify positive and negative signals. Be comprehensive!
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
    # Calculate Growth Momentum metrics from events and other data
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
        
        # Calculate funding cadence (average months between funding rounds)
        if len(funding_events) >= 2:
            funding_dates = sorted([e.occurred_on for e in funding_events])
            date_diffs = []
            for i in range(1, len(funding_dates)):
                delta = funding_dates[i] - funding_dates[i-1]
                months_diff = delta.days / 30.44  # Average days per month
                date_diffs.append(months_diff)
            if date_diffs:
                snapshot.funding_cadence_months = sum(date_diffs) / len(date_diffs)
    
    # Calculate headcount velocity from snapshot data
    if snapshot.headcount_total and snapshot.job_openings_count:
        # If job openings are high relative to headcount, likely rapid hiring
        job_ratio = snapshot.job_openings_count / snapshot.headcount_total if snapshot.headcount_total > 0 else 0
        if not snapshot.headcount_velocity:
            if job_ratio > 0.15:  # >15% of headcount are open positions
                snapshot.headcount_velocity = "Rapid"
            elif job_ratio > 0.08:  # 8-15%
                snapshot.headcount_velocity = "Moderate"
            elif job_ratio > 0.03:  # 3-8%
                snapshot.headcount_velocity = "Slow"
            else:
                snapshot.headcount_velocity = "Stable"
    
    # Calculate release velocity from products
    if products:
        # Count products with GA dates in last 12 months
        today = date.today()
        one_year_ago = date(today.year - 1, today.month, today.day)
        recent_products = [p for p in products if p.ga_date and p.ga_date >= one_year_ago]
        
        if not snapshot.products_released_last_12m:
            snapshot.products_released_last_12m = len(recent_products)
        
        # Determine release velocity
        if not snapshot.release_velocity:
            if len(recent_products) >= 5:
                snapshot.release_velocity = "High"
            elif len(recent_products) >= 2:
                snapshot.release_velocity = "Medium"
            else:
                snapshot.release_velocity = "Low"
    
    # Extract notable customers from products
    if products and not snapshot.notable_customers:
        all_customers = []
        for product in products:
            if product.reference_customers:
                all_customers.extend(product.reference_customers)
        if all_customers:
            snapshot.notable_customers = list(set(all_customers))[:10]  # Top 10 unique customers
    
    # Calculate leadership stability
    if leadership:
        # Count leadership changes (those with end_date or recent start_date)
        if not snapshot.leadership_changes_last_12m:
            today = date.today()
            one_year_ago = date(today.year - 1, today.month, today.day)
            recent_changes = [
                l for l in leadership 
                if (l.start_date and l.start_date >= one_year_ago) or 
                   (l.end_date and l.end_date >= one_year_ago)
            ]
            snapshot.leadership_changes_last_12m = len(recent_changes)
        
        # Determine stability
        if not snapshot.leadership_stability:
            if snapshot.leadership_changes_last_12m and snapshot.leadership_changes_last_12m > 3:
                snapshot.leadership_stability = "High turnover"
            elif snapshot.leadership_changes_last_12m and snapshot.leadership_changes_last_12m > 0:
                snapshot.leadership_stability = "Growing"
            else:
                snapshot.leadership_stability = "Stable"
    
    # Calculate positive vs negative events from events list
    if events:
        positive_events = []
        negative_events = []
        
        for event in events:
            event_lower = event.title.lower() + " " + (event.description or "").lower()
            
            # Positive signals
            if any(keyword in event_lower for keyword in [
                'funding', 'raised', 'partnership', 'launch', 'award', 'expansion',
                'growth', 'milestone', 'customer', 'contract', 'acquisition'
            ]) and not any(neg in event_lower for neg in ['layoff', 'churn', 'loss', 'failure']):
                positive_events.append(event.title)
            
            # Negative signals
            if any(keyword in event_lower for keyword in [
                'layoff', 'reduction', 'downsizing', 'rif', 'restructuring',
                'lawsuit', 'breach', 'churn', 'loss', 'failure', 'investigation'
            ]):
                negative_events.append(event.title)
        
        snapshot.positive_events_count = len(positive_events)
        snapshot.negative_events_count = len(negative_events)
        
        # Add to signals if not already extracted
        if not snapshot.positive_signals:
            snapshot.positive_signals = positive_events[:10]  # Top 10
        if not snapshot.negative_signals:
            snapshot.negative_signals = negative_events[:10]  # Top 10
    
    # Calculate Risk Score (0-100, lower is better)
    risk_score = 50.0  # Start at neutral
    
    # Layoffs significantly increase risk
    if snapshot.layoffs_mentioned:
        risk_score += 30
        if snapshot.layoffs_percentage:
            risk_score += min(snapshot.layoffs_percentage * 0.5, 20)  # Up to +20 for large layoffs
        elif snapshot.layoffs_count and snapshot.headcount_total:
            layoff_pct = (snapshot.layoffs_count / snapshot.headcount_total) * 100
            risk_score += min(layoff_pct * 0.5, 20)
    
    # Negative signals increase risk
    if snapshot.negative_events_count:
        risk_score += snapshot.negative_events_count * 3  # +3 per negative event
    
    # Churn signals increase risk
    if snapshot.churn_signals:
        risk_score += len(snapshot.churn_signals) * 5
    
    # Regulatory exposure increases risk
    if snapshot.regulatory_exposure:
        risk_score += len(snapshot.regulatory_exposure) * 4
    
    # Leadership instability increases risk
    if snapshot.leadership_stability == "High turnover":
        risk_score += 15
    elif snapshot.leadership_stability and "turnover" in snapshot.leadership_stability.lower():
        risk_score += 10
    
    # High leadership changes increase risk
    if snapshot.leadership_changes_last_12m and snapshot.leadership_changes_last_12m > 3:
        risk_score += 10
    
    # Positive signals reduce risk
    if snapshot.positive_events_count:
        risk_score -= min(snapshot.positive_events_count * 2, 20)  # Up to -20 for positive events
    
    # Strong customers reduce risk
    if snapshot.notable_customers and len(snapshot.notable_customers) >= 3:
        risk_score -= 5
    if snapshot.customer_quality_score == "Enterprise":
        risk_score -= 5
    
    # Growth indicators reduce risk
    if snapshot.headcount_velocity == "Rapid":
        risk_score -= 5
    if snapshot.funding_cadence_months and snapshot.funding_cadence_months < 12:
        risk_score -= 5  # Frequent funding is positive
    
    # Clamp risk score between 0 and 100
    risk_score = max(0, min(100, risk_score))
    snapshot.risk_score = round(risk_score, 1)
    
    # Determine risk level
    if risk_score >= 70:
        snapshot.risk_level = "Critical"
    elif risk_score >= 50:
        snapshot.risk_level = "High"
    elif risk_score >= 30:
        snapshot.risk_level = "Medium"
    else:
        snapshot.risk_level = "Low"
    
    # Build key challenges list
    challenges = []
    if snapshot.layoffs_mentioned:
        challenges.append("Workforce reduction/Layoffs")
    if snapshot.churn_signals:
        challenges.append("Customer retention issues")
    if snapshot.regulatory_exposure:
        challenges.append(f"Regulatory exposure: {', '.join(snapshot.regulatory_exposure[:3])}")
    if snapshot.leadership_stability == "High turnover":
        challenges.append("Leadership instability")
    if snapshot.negative_events_count and snapshot.negative_events_count > snapshot.positive_events_count:
        challenges.append("Negative news outweighs positive")
    if not snapshot.notable_customers or len(snapshot.notable_customers) < 2:
        challenges.append("Limited enterprise customer base")
    
    if not snapshot.key_challenges:
        snapshot.key_challenges = challenges
    
    # Calculate Transparency Score (0-100, higher is better)
    transparency_score = 50.0  # Start at neutral
    
    # Positive transparency indicators
    if snapshot.headcount_total:  # Disclosing team size
        transparency_score += 10
    if company.total_raised_usd:  # Disclosing funding
        transparency_score += 10
    if snapshot.notable_customers and len(snapshot.notable_customers) >= 3:  # Naming customers
        transparency_score += 15
    if snapshot.actual_case_studies and len(snapshot.actual_case_studies) >= 2:  # Case studies
        transparency_score += 15
    if snapshot.pricing_tiers and len(snapshot.pricing_tiers) > 0:  # Pricing transparency
        transparency_score += 10
    if snapshot.geo_presence and len(snapshot.geo_presence) > 0:  # Location transparency
        transparency_score += 5
    if company.founded_year:  # Founding date disclosed
        transparency_score += 5
    
    # Negative transparency indicators (disclosure gaps)
    missing_info_penalty = len(snapshot.missing_key_info) * 5  # -5 per missing key info
    transparency_score -= missing_info_penalty
    
    if snapshot.disclosure_gaps and len(snapshot.disclosure_gaps) > 0:
        transparency_score -= len(snapshot.disclosure_gaps) * 8  # -8 per disclosure gap
    
    # Marketing vs reality gap penalty
    if snapshot.marketing_vs_reality_gap:
        if "large" in snapshot.marketing_vs_reality_gap.lower() or "significant" in snapshot.marketing_vs_reality_gap.lower():
            transparency_score -= 15
        elif "gap" in snapshot.marketing_vs_reality_gap.lower() or "mismatch" in snapshot.marketing_vs_reality_gap.lower():
            transparency_score -= 10
    
    # Lack of case studies when marketing claims exist
    if snapshot.marketed_info_available and len(snapshot.marketed_info_available) > 0:
        if not snapshot.actual_case_studies or len(snapshot.actual_case_studies) == 0:
            transparency_score -= 10  # Marketing without proof
    
    # Clamp transparency score between 0 and 100
    transparency_score = max(0, min(100, transparency_score))
    snapshot.transparency_score = round(transparency_score, 1)
    
    # Determine transparency level
    if transparency_score >= 80:
        snapshot.transparency_level = "High"
    elif transparency_score >= 60:
        snapshot.transparency_level = "Medium"
    elif transparency_score >= 40:
        snapshot.transparency_level = "Low"
    else:
        snapshot.transparency_level = "Poor"
    
    # Assess marketing vs reality gap if not already extracted
    if not snapshot.marketing_vs_reality_gap:
        if snapshot.marketed_info_available and snapshot.actual_case_studies:
            if len(snapshot.actual_case_studies) >= len(snapshot.marketed_info_available) * 0.5:
                snapshot.marketing_vs_reality_gap = "Well-supported (claims backed by proof)"
            elif len(snapshot.actual_case_studies) >= len(snapshot.marketed_info_available) * 0.25:
                snapshot.marketing_vs_reality_gap = "Moderate gap (some claims supported)"
            else:
                snapshot.marketing_vs_reality_gap = "Significant gap (claims lack proof)"
        elif snapshot.marketed_info_available and not snapshot.actual_case_studies:
            snapshot.marketing_vs_reality_gap = "Large gap (marketing claims without case studies)"
        else:
            snapshot.marketing_vs_reality_gap = "Limited information available"
    
    # Enhance disclosure_gaps if not already extracted
    if not snapshot.disclosure_gaps:
        gaps = []
        if not snapshot.headcount_total:
            gaps.append("Team size not disclosed")
        if not snapshot.pricing_tiers or len(snapshot.pricing_tiers) == 0:
            gaps.append("Pricing information not disclosed")
        if not snapshot.notable_customers or len(snapshot.notable_customers) == 0:
            gaps.append("Customer names/references not disclosed")
        if snapshot.marketed_info_available and not snapshot.actual_case_studies:
            gaps.append("Marketing claims lack supporting case studies")
        if not company.total_raised_usd:
            gaps.append("Funding information not disclosed")
        snapshot.disclosure_gaps = gaps
    
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