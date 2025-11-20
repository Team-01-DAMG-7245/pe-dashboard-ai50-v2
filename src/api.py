from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import os
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="PE Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Please set it in .env file or environment variable.")
client = OpenAI(api_key=api_key)

def load_dashboard_prompt() -> str:
    """Load the dashboard system prompt"""
    prompt_path = DATA_DIR.parent / "src" / "prompts" / "dashboard_system.md"
    if prompt_path.exists():
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    # Fallback prompt
    return """You are generating investor-facing due diligence dashboards for private equity firms."""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/companies")
def list_companies():
    seed_path = DATA_DIR / "forbes_ai50_seed.json"
    if seed_path.exists():
        return json.loads(seed_path.read_text())
    return []

class DashboardRequest(BaseModel):
    company_id: str

@app.post("/dashboard/structured")
async def dashboard_structured(request: DashboardRequest):
    """Generate dashboard using structured payload pipeline"""
    try:
        # Load structured payload
        payload_path = DATA_DIR / "payloads" / f"{request.company_id}.json"
        
        if not payload_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Structured payload not found for company: {request.company_id}"
            )
        
        with open(payload_path, "r", encoding="utf-8") as f:
            payload_data = json.load(f)
        
        # Format as context
        context = json.dumps(payload_data, indent=2, ensure_ascii=False)
        
        # Load dashboard prompt
        system_prompt = load_dashboard_prompt()
        
        # Create user prompt
        user_prompt = f"""Generate an investor-facing diligence dashboard for {request.company_id}.

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
   - Disclosure Gaps"""
        
        # Generate dashboard
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
        
        return {"markdown": dashboard}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating structured dashboard: {str(e)}")

@app.post("/dashboard/rag")
async def dashboard_rag(request: DashboardRequest):
    """Generate dashboard using RAG pipeline"""
    try:
        # Import RAG retrieval (with error handling)
        try:
            from .lab7.rag_pipeline import retrieve_context
            context_chunks = retrieve_context(request.company_id, top_k=10)
        except Exception as e:
            # Fallback if RAG not available
            print(f"Warning: RAG retrieval failed: {e}")
            context_chunks = []
        
        # Format context
        if context_chunks:
            context = "\n\n".join([chunk.get("text", "") for chunk in context_chunks[:10]])
        else:
            context = "No context available from vector database."
        
        # Load dashboard prompt
        system_prompt = load_dashboard_prompt()
        
        # Create user prompt
        user_prompt = f"""Generate an investor-facing diligence dashboard for {request.company_id}.

Here is retrieved context from the vector database:

{context}

CRITICAL REQUIREMENTS:
1. Use the retrieved context above
2. When information is not in the context, say exactly "Not disclosed."
3. Must include ALL 8 sections:
   - Company Overview
   - Business Model and GTM
   - Funding & Investor Profile
   - Growth Momentum
   - Visibility & Market Sentiment
   - Risks and Challenges
   - Outlook
   - Disclosure Gaps"""
        
        # Generate dashboard
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
        
        return {
            "markdown": dashboard,
            "chunks_used": len(context_chunks) if context_chunks else 0
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating RAG dashboard: {str(e)}")
