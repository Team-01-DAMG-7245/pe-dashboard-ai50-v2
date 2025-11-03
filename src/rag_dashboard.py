"""
Lab 7: RAG Pipeline Dashboard
Generates investor dashboards using vector DB retrieval
Strictly follows professor's dashboard_system.md requirements
"""

import os
from typing import Dict
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import chromadb

app = FastAPI(title="PE Dashboard API - RAG Pipeline")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Connect to EXISTING vector database
chroma_client = chromadb.PersistentClient(path="data/vector_db")
collection = chroma_client.get_collection("ai50_companies")
print(f"Connected to existing collection with {collection.count()} chunks")

# Import embedding model for searches
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

class DashboardRequest(BaseModel):
    company_id: str
    top_k: int = 10

class DashboardResponse(BaseModel):
    company_id: str
    dashboard: str
    chunks_used: int

def load_dashboard_prompt() -> str:
    """Load the dashboard system prompt"""
    with open("src/prompts/dashboard_system.md", "r") as f:
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
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=3,  # Get top 3 per query
                where={"company_id": request.company_id}
            )
            
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
        
        # Validate that all 8 sections are present
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
        
        for section in required_sections:
            if section not in dashboard:
                # If a section is missing, regenerate with stronger emphasis
                print(f"Warning: Section '{section}' missing, regenerating...")
                
                stronger_prompt = user_prompt + f"\n\nWARNING: You MUST include all 8 sections with ## headers. Currently missing: {section}"
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": stronger_prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2500
                )
                dashboard = response.choices[0].message.content
                break
        
        return DashboardResponse(
            company_id=request.company_id,
            dashboard=dashboard,
            chunks_used=len(unique_chunks)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "RAG Dashboard API - Lab 7",
        "endpoint": "/dashboard/rag",
        "description": "POST to /dashboard/rag with company_id to generate investor dashboard"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        count = collection.count()
        return {
            "status": "healthy",
            "vector_db_chunks": count,
            "model": "gpt-4o-mini"
        }
    except:
        return {"status": "unhealthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)