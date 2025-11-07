from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import date

class Provenance(BaseModel):
    source_url: Optional[str] = None  # Changed from HttpUrl to Optional[str] for flexibility
    crawled_at: str
    snippet: Optional[str] = None

class Company(BaseModel):
    company_id: str
    legal_name: str
    brand_name: Optional[str] = None
    website: Optional[HttpUrl] = None
    hq_city: Optional[str] = None
    hq_state: Optional[str] = None
    hq_country: Optional[str] = None
    founded_year: Optional[int] = None
    categories: List[str] = []
    related_companies: List[str] = []
    total_raised_usd: Optional[float] = None
    last_disclosed_valuation_usd: Optional[float] = None
    last_round_name: Optional[str] = None
    last_round_date: Optional[date] = None
    schema_version: str = "2.0.0"
    as_of: Optional[date] = None
    provenance: List[Provenance] = []

class Event(BaseModel):
    event_id: str
    company_id: Optional[str] = None  # Will be set after extraction
    occurred_on: date
    event_type: str
    title: str
    description: Optional[str] = None
    round_name: Optional[str] = None
    investors: Optional[List[str]] = []  # Allow empty list as default
    amount_usd: Optional[float] = None
    valuation_usd: Optional[float] = None
    actors: List[str] = []
    tags: List[str] = []
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = []

class Snapshot(BaseModel):
    company_id: str
    as_of: date
    headcount_total: Optional[int] = None
    headcount_growth_pct: Optional[float] = None
    job_openings_count: Optional[int] = None
    engineering_openings: Optional[int] = None
    sales_openings: Optional[int] = None
    hiring_focus: List[str] = []
    pricing_tiers: Optional[List[str]] = []  # Allow empty list as default
    active_products: Optional[List[str]] = []  # Allow empty list as default
    geo_presence: Optional[List[str]] = []  # Allow empty list as default
    confidence: Optional[float] = None
    # Growth Momentum Metrics
    funding_cadence_months: Optional[float] = None  # Average months between funding rounds
    headcount_velocity: Optional[str] = None  # e.g., "Rapid", "Moderate", "Slow", "Stable"
    headcount_growth_rate: Optional[float] = None  # Annual growth rate percentage
    release_velocity: Optional[str] = None  # e.g., "High", "Medium", "Low"
    products_released_last_12m: Optional[int] = None  # Number of products/features released in last 12 months
    geography_expansion: List[str] = []  # New geographic locations/regions
    geography_expansion_rate: Optional[str] = None  # e.g., "Rapid", "Moderate", "Slow"
    # Durability Indicators
    notable_customers: List[str] = []  # Well-known customers/partners
    customer_quality_score: Optional[str] = None  # e.g., "Enterprise", "Mid-market", "SMB"
    churn_signals: List[str] = []  # Any churn or customer retention issues mentioned
    regulatory_exposure: List[str] = []  # Regulatory risks or compliance issues
    leadership_stability: Optional[str] = None  # e.g., "Stable", "High turnover", "Growing"
    leadership_changes_last_12m: Optional[int] = None  # Number of leadership changes
    # Risk & Challenges
    layoffs_mentioned: Optional[bool] = None  # Whether layoffs are mentioned
    layoffs_count: Optional[int] = None  # Number of layoffs if mentioned
    layoffs_date: Optional[date] = None  # Date of layoffs if mentioned
    layoffs_percentage: Optional[float] = None  # Percentage of workforce laid off
    positive_signals: List[str] = []  # Product releases, partnerships, funding, positive news
    negative_signals: List[str] = []  # Layoffs, churn, regulatory issues, negative news
    positive_events_count: Optional[int] = None  # Count of positive events/announcements
    negative_events_count: Optional[int] = None  # Count of negative events/announcements
    risk_score: Optional[float] = None  # Overall risk score (0-100, lower is better)
    risk_level: Optional[str] = None  # "Low", "Medium", "High", "Critical"
    key_challenges: List[str] = []  # Identified challenges and risks
    # Transparency & Disclosure
    transparency_score: Optional[float] = None  # Transparency score (0-100, higher is better)
    transparency_level: Optional[str] = None  # "High", "Medium", "Low", "Poor"
    marketed_info_available: List[str] = []  # What information is marketed (claims, features, benefits)
    actual_case_studies: List[str] = []  # Actual case studies, customer testimonials, proof points
    disclosure_gaps: List[str] = []  # Information that should be disclosed but isn't (e.g., pricing, customer count, metrics)
    missing_key_info: List[str] = []  # Critical information that's missing (e.g., pricing, customer count, metrics, team size)
    marketing_vs_reality_gap: Optional[str] = None  # Assessment of gap between marketing claims and proof
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = []

class Product(BaseModel):
    product_id: str
    company_id: str
    name: str
    description: Optional[str] = None
    pricing_model: Optional[str] = None
    pricing_tiers_public: List[str] = []
    ga_date: Optional[date] = None
    integration_partners: List[str] = []
    github_repo: Optional[str] = None
    license_type: Optional[str] = None
    reference_customers: List[str] = []
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = []

class Leadership(BaseModel):
    person_id: str
    company_id: str
    name: str
    role: str
    is_founder: bool = False
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    previous_affiliation: Optional[str] = None
    education: Optional[str] = None
    linkedin: Optional[HttpUrl] = None
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = []

class Visibility(BaseModel):
    company_id: str
    as_of: date
    news_mentions_30d: Optional[int] = None
    avg_sentiment: Optional[float] = None
    github_stars: Optional[int] = None
    glassdoor_rating: Optional[float] = None
    schema_version: str = "2.0.0"
    provenance: List[Provenance] = []

# Wrapper models for instructor List extraction
class EventsList(BaseModel):
    events: List[Event] = []

class LeadershipList(BaseModel):
    leadership: List[Leadership] = []

class ProductsList(BaseModel):
    products: List[Product] = []

class Payload(BaseModel):
    company_record: Company
    events: List[Event] = []
    snapshots: List[Snapshot] = []
    products: List[Product] = []
    leadership: List[Leadership] = []
    visibility: List[Visibility] = []
    notes: Optional[str] = ""
    provenance_policy: Optional[str] = "Use only the sources you scraped. If a field is missing, write 'Not disclosed.' Do not infer valuation."
