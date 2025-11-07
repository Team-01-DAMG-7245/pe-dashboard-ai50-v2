"""
Lab 7: RAG Pipeline Dashboard
Generates investor dashboards using vector DB retrieval
Strictly follows professor's dashboard_system.md requirements
"""

# Fix NumPy 2.x compatibility with ChromaDB
import numpy as np
if not hasattr(np, 'float_'):
    np.float_ = np.float64
if not hasattr(np, 'int_'):
    np.int_ = np.int64
if not hasattr(np, 'uint'):
    np.uint = np.uint64

# Patch ChromaDB's DefaultEmbeddingFunction BEFORE importing chromadb
# This prevents ONNX DLL errors on Windows
import sys
from unittest.mock import MagicMock
from types import ModuleType

# Create a proper mock module for onnxruntime with __spec__ attribute
# This prevents PyTorch's dynamo from failing when checking for onnxruntime
class MockONNXRuntime(ModuleType):
    """Mock onnxruntime module to prevent DLL errors"""
    def __init__(self):
        super().__init__('onnxruntime')
        # Add __spec__ attribute for importlib compatibility
        import importlib.util
        self.__spec__ = importlib.util.spec_from_loader('onnxruntime', loader=None)
        
# Mock ONNX to prevent import errors
sys.modules['onnxruntime'] = MockONNXRuntime()

import os
import json
from typing import Dict
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import chromadb

# Load environment variables from .env file
project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Also try loading from current directory
    load_dotenv()

app = FastAPI(title="PE Dashboard API - RAG Pipeline")

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Please set it in .env file or environment variable.")
client = OpenAI(api_key=api_key)

# Connect to EXISTING vector database
# Try to load SentenceTransformer model FIRST (this will show DLL errors early)
try:
    from sentence_transformers import SentenceTransformer
    print("Loading SentenceTransformer model...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("[OK] SentenceTransformer model loaded successfully")
except Exception as e:
    print(f"[ERROR] Error loading SentenceTransformer: {e}")
    print("This is likely a PyTorch DLL issue.")
    print("Solution: Install Visual C++ Redistributables from:")
    print("https://aka.ms/vs/17/release/vc_redist.x64.exe")
    embedding_model = None
    raise

# Now create ChromaDB embedding function (after model is loaded)
from chromadb.utils import embedding_functions
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name='all-MiniLM-L6-v2'
)

# Use relative path from project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
vector_db_path = os.path.join(project_root, "data", "vector_db")
chroma_client = chromadb.PersistentClient(path=vector_db_path)

# Now try to connect to vector DB
try:
    collection = chroma_client.get_collection(
        "ai50_companies",
        embedding_function=sentence_transformer_ef
    )
    print(f"[OK] Connected to existing collection with {collection.count()} chunks")
except Exception as e:
    print(f"[WARNING] Error connecting to collection: {e}")
    print("Creating new collection...")
    try:
        collection = chroma_client.create_collection(
            "ai50_companies",
            embedding_function=sentence_transformer_ef
        )
        print("[OK] Created new collection. Run: python src/index_for_rag_all.py to populate it.")
    except Exception as e2:
        print(f"[ERROR] Error creating collection: {e2}")
        print("Vector DB may not be accessible. Some endpoints may not work.")
        collection = None

class DashboardRequest(BaseModel):
    company_id: str
    top_k: int = 10

class DashboardResponse(BaseModel):
    company_id: str
    dashboard: str
    chunks_used: int

def load_dashboard_prompt() -> str:
    """Load the dashboard system prompt"""
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'dashboard_system.md')
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/dashboard/rag", response_model=DashboardResponse)
async def generate_rag_dashboard(request: DashboardRequest):
    """
    Generate dashboard using RAG pipeline
    Following professor's requirements exactly:
    1. Retrieve top-k context for the company
    2. Call LLM with the dashboard prompt
    3. Enforce 8-section output
    4. Use "Not disclosed." for missing data
    """
    
    if collection is None:
        raise HTTPException(status_code=503, detail="Vector database not available. Please check if vector DB is initialized.")
    
    if embedding_model is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded. DLL error - please install Visual C++ Redistributables.")
    
    try:
        # Step 1: Retrieve top-k context for the company
        # Using multiple targeted queries for comprehensive coverage
        queries = [
            f"{request.company_id} company overview business model products services",
            f"{request.company_id} funding investment valuation series raised investors", 
            f"{request.company_id} leadership team CEO founder executives management",
            f"{request.company_id} growth revenue customers metrics performance ARR",
            f"{request.company_id} market sentiment news press visibility media",
            f"{request.company_id} risks challenges competition concerns limitations",
            f"{request.company_id} future outlook strategy expansion plans",
            f"{request.company_id} financial information disclosure transparency"
        ]
        
        all_chunks = []
        for query in queries:
            # Generate embedding for each query
            query_embedding = embedding_model.encode([query]).tolist()
            
            # Search in collection with company filter
            # Try with filter first, if no results, try without filter
            where_clause = {"company_id": request.company_id}
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=5,  # Get top 5 per query (increased from 3)
                where=where_clause
            )
            
            # If no results with filter, try without filter and filter manually
            if not results['documents'] or not results['documents'][0]:
                # Try without filter and filter results manually
                results = collection.query(
                    query_embeddings=query_embedding,
                    n_results=20  # Get more results to filter
                )
                # Filter manually by company_id
                if results['documents'] and results['documents'][0]:
                    filtered_docs = []
                    filtered_metas = []
                    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                        if meta.get('company_id') == request.company_id:
                            filtered_docs.append(doc)
                            filtered_metas.append(meta)
                    results = {'documents': [filtered_docs], 'metadatas': [filtered_metas]}
            
            if results['documents'] and results['documents'][0]:
                for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
                    all_chunks.append({
                        'text': doc,
                        'metadata': meta
                    })
        
        # Deduplicate chunks
        seen = set()
        unique_chunks = []
        for chunk in all_chunks:
            if chunk['text'] not in seen:
                seen.add(chunk['text'])
                unique_chunks.append(chunk)
        
        # Limit to top_k chunks
        unique_chunks = unique_chunks[:request.top_k]
        
        if not unique_chunks:
            raise HTTPException(status_code=404, detail=f"No data found for company: {request.company_id}")
        
        # Step 2: Combine chunks into context (this is our "payload" for RAG)
        context = "\n\n---\n\n".join([chunk['text'] for chunk in unique_chunks])
        
        # Step 3: Load the exact dashboard prompt from professor
        system_prompt = load_dashboard_prompt()
        
        # Step 4: Create user prompt that emphasizes the requirements
        user_prompt = f"""Generate an investor-facing diligence dashboard for {request.company_id}.

Here is the available data (payload):

{context}

CRITICAL REQUIREMENTS:
1. Use ONLY the data provided above - do not add external information
2. When information is not available in the provided data, say exactly "Not disclosed."
3. If a claim seems like marketing, attribute it: "The company states..."
4. Never include personal emails or phone numbers
5. Must include ALL 8 sections in this EXACT order:
   - Company Overview
   - Business Model and GTM
   - Funding & Investor Profile
   - Growth Momentum
   - Visibility & Market Sentiment
   - Risks and Challenges
   - Outlook
   - Disclosure Gaps

The "Disclosure Gaps" section MUST be included as the final section and should list what important information was not available in the provided data."""
        
        # Step 5: Generate dashboard with strict adherence to format
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using gpt-4o-mini for better instruction following
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Low temperature for consistency
            max_tokens=2500   # Enough for comprehensive dashboard
        )
        
        dashboard = response.choices[0].message.content
        
        # Validate checkpoint: All 8 sections must be present
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
        
        missing_sections = [s for s in required_sections if s not in dashboard]
        if missing_sections:
            # If sections are missing, regenerate with stronger emphasis
            print(f"Warning: Missing sections: {missing_sections}, regenerating...")
            
            stronger_prompt = user_prompt + f"\n\nCRITICAL: You MUST include all 8 sections with ## headers. Missing: {', '.join(missing_sections)}\n\nYour output MUST start with ## Company Overview and end with ## Disclosure Gaps."
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": stronger_prompt}
                ],
                temperature=0.1,
                max_tokens=3000  # Increased for complete sections
            )
            dashboard = response.choices[0].message.content
        
        # Final validation - ensure all sections present
        final_missing = [s for s in required_sections if s not in dashboard]
        if final_missing:
            # Add missing sections manually if LLM still fails
            for section in final_missing:
                section_name = section.replace("## ", "")
                dashboard += f"\n\n{section}\n\nNot disclosed.\n"
        
        # Checkpoint: Verify "Not disclosed." usage (case-insensitive)
        if "not disclosed" not in dashboard.lower():
            print("Warning: Dashboard may not use 'Not disclosed.' for missing data")
        
        return DashboardResponse(
            company_id=request.company_id,
            dashboard=dashboard,
            chunks_used=len(unique_chunks)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard: {str(e)}")

# Add Lab 8 structured dashboard endpoint
class StructuredDashboardRequest(BaseModel):
    company_id: str

class StructuredDashboardResponse(BaseModel):
    company_id: str
    dashboard: str
    source: str = "structured_payload"

@app.post("/dashboard/structured", response_model=StructuredDashboardResponse)
async def generate_structured_dashboard(request: StructuredDashboardRequest):
    """
    Lab 8: Generate dashboard using structured payload pipeline
    Goal: structured payload → LLM → Markdown dashboard
    """
    try:
        # Step 1: Load structured payload
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        payload_path = os.path.join(project_root, "data", "payloads", f"{request.company_id}.json")
        
        if not os.path.exists(payload_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Structured payload not found for company: {request.company_id}"
            )
        
        with open(payload_path, "r", encoding="utf-8") as f:
            payload_data = json.load(f)
        
        # Step 2: Format as context
        context = json.dumps(payload_data, indent=2, ensure_ascii=False)
        
        # Step 3: Load dashboard prompt
        system_prompt = load_dashboard_prompt()
        
        # Step 4: Create user prompt
        user_prompt = f'''Generate an investor-facing diligence dashboard for {request.company_id}.

Here is the structured payload (JSON) with normalized, validated data:

{context}

CRITICAL REQUIREMENTS:
1. Use ONLY the structured data provided above
2. When a field is null or empty, say exactly "Not disclosed."
3. When an array is empty, say "Not disclosed."
4. Must include ALL 8 sections:
   - Company Overview
   - Business Model and GTM
   - Funding & Investor Profile
   - Growth Momentum
   - Visibility & Market Sentiment
   - Risks and Challenges
   - Outlook
   - Disclosure Gaps

5. For Disclosure Gaps section:
   - Do NOT include "Missing Key Information" as a heading, category, or bullet point
   - Do NOT use phrases like "Missing Key Information:" followed by a list
   - Focus on specific gaps: missing financial metrics, incomplete leadership data, unclear product details, etc.
   - List specific data points that are not available using bullet points (e.g., "• Revenue figures not disclosed", "• Customer retention metrics unavailable")
   - Format as specific bullet points or short statements about what data is missing
   - If no specific gaps, simply state "No significant disclosure gaps identified." or "All key information appears to be disclosed."

6. For the following three sections, include these details strictly from the structured payload (do NOT invent; use "Not disclosed."):

   A) Visibility & Market Sentiment
      - Summarize recent visibility from VisibilityMetrics using:
        • news_mentions_30d
        • avg_sentiment (−1 to 1)
        • github_stars
        • glassdoor_rating
      - Conclude with: "Attention: accelerating | stable | unclear" based on available signals.

   B) Risks and Challenges
      - List downside signals using only provided data (neutral tone):
        • layoffs
        • regulatory / security incidents
        • executive churn
        • pricing pressure / commoditization
        • GTM concentration risk

   C) Outlook
      - Give a restrained investor readout focusing on:
        • moat (data advantage, integrations, founder pedigree)
        • GTM scaling (compare sales_openings vs engineering_openings if available)
        • macro fit
      - Do not hype. Do not invent.
'''
        
        # Step 5: Generate dashboard
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=3000
        )
        
        dashboard = response.choices[0].message.content
        
        # Post-process: Remove "Missing Key Information" line from Disclosure Gaps
        import re
        # Remove lines that start with "Missing Key Information:" or contain it as a header
        dashboard = re.sub(r'^.*Missing Key Information:.*$', '', dashboard, flags=re.MULTILINE | re.IGNORECASE)
        # Clean up extra blank lines
        dashboard = re.sub(r'\n{3,}', '\n\n', dashboard)
        
        # Validate 8 sections
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
        
        missing_sections = [s for s in required_sections if s not in dashboard]
        if missing_sections:
            # Add missing sections
            for section in missing_sections:
                dashboard += f"\n\n{section}\n\nNot disclosed.\n"
        
        return StructuredDashboardResponse(
            company_id=request.company_id,
            dashboard=dashboard,
            source="structured_payload"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating structured dashboard: {str(e)}")

@app.get("/companies")
async def list_companies():
    """List available companies for dashboard generation.
    Sources:
    - data/payloads/*.json filenames (preferred)
    - Chroma collection metadatas (fallback if available)
    """
    companies = set()

    # From structured payloads
    try:
        project_root_local = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        payloads_dir = os.path.join(project_root_local, "data", "payloads")
        if os.path.isdir(payloads_dir):
            for name in os.listdir(payloads_dir):
                if name.lower().endswith(".json"):
                    companies.add(os.path.splitext(name)[0])
    except Exception:
        pass

    # From vector DB collection metadata (best-effort)
    try:
        if collection is not None:
            # Query a sample to collect company_id values
            sample = collection.get(include=["metadatas"], limit=1000)
            for meta in (sample.get("metadatas") or []):
                for m in meta or []:
                    cid = (m or {}).get("company_id")
                    if cid:
                        companies.add(cid)
    except Exception:
        pass

    return {"companies": sorted(companies)}

@app.get("/")
async def root():
    return {
        "message": "Dashboard API - Labs 7 & 8",
        "endpoints": {
            "/companies": "List available companies (from payloads and/or vector DB)",
            "/dashboard/rag": "Lab 7 - RAG pipeline (vector DB → LLM → dashboard)",
            "/dashboard/structured": "Lab 8 - Structured pipeline (JSON payload → LLM → dashboard)"
        },
        "description": "POST to either endpoint with company_id to generate investor dashboard"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        count = collection.count()
        return {
            "status": "healthy",
            "vector_db_chunks": count,
            "model": "gpt-4o-mini",
            "endpoints": ["/dashboard/rag", "/dashboard/structured"]
        }
    except:
        return {"status": "unhealthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)