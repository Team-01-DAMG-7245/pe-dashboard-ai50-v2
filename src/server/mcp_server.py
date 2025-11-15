"""
MCP Server for PE Dashboard - Lab 14
Exposes dashboard generation logic as MCP Tools, Resources, and Prompts.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import json
from pathlib import Path
import os
import sys

# Add parent directory to path to import from src
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import your existing dashboard functions
from src.rag_dashboard import generate_rag_dashboard as rag_dashboard_func
from src.rag_dashboard import DashboardRequest as RAGDashboardRequest

app = FastAPI(
    title="PE Dashboard MCP Server",
    description="Model Context Protocol server for PE dashboard generation",
    version="1.0.0"
)

class CompanyIdList(BaseModel):
    company_ids: List[str]

class DashboardRequest(BaseModel):
    company_id: str

class DashboardResponse(BaseModel):
    markdown: str
    company_id: str
    status: str = "success"

@app.get("/")
async def root():
    """Root endpoint showing available MCP endpoints"""
    return {
        "service": "PE Dashboard MCP Server",
        "endpoints": {
            "tools": [
                "/tool/generate_structured_dashboard",
                "/tool/generate_rag_dashboard"
            ],
            "resources": [
                "/resource/ai50/companies"
            ],
            "prompts": [
                "/prompt/pe-dashboard"
            ]
        }
    }

@app.get("/resource/ai50/companies", response_model=CompanyIdList)
def get_companies():
    """Resource: Returns list of all AI50 company IDs"""
    try:
        # Get company IDs from payload files
        payload_dir = Path("data/payloads")
        company_files = list(payload_dir.glob("*.json"))
        
        # Extract company IDs (filename without .json, excluding manifest)
        company_ids = [
            f.stem for f in company_files 
            if f.stem != "manifest"
        ]
        
        return CompanyIdList(company_ids=sorted(company_ids))
    except Exception as e:
        # Fallback to reading from seed file if available
        try:
            seed_file = Path("data/forbes_ai50_seed.json")
            if seed_file.exists():
                with open(seed_file) as f:
                    data = json.load(f)
                    company_ids = [c.get("company_id", c.get("id")) for c in data.get("companies", [])]
                    return CompanyIdList(company_ids=company_ids)
        except:
            pass
        
        # Return empty list if no data found
        return CompanyIdList(company_ids=[])

@app.get("/prompt/pe-dashboard")
def get_pe_dashboard_prompt():
    """Prompt: Returns the 8-section PE dashboard template"""
    try:
        # Load the dashboard prompt from your existing file
        prompt_file = Path("src/prompts/dashboard_system.md")
        if prompt_file.exists():
            with open(prompt_file) as f:
                prompt_content = f.read()
        else:
            # Fallback prompt if file not found
            prompt_content = """## Company Overview
## Business Model and GTM
## Funding & Investor Profile
## Growth Momentum
## Visibility & Market Sentiment
## Risks and Challenges
## Outlook
## Disclosure Gaps"""
        
        return {
            "id": "pe-dashboard",
            "name": "PE Due Diligence Dashboard",
            "description": "8-section investor-facing diligence dashboard for private AI startups",
            "template": prompt_content,
            "sections": [
                "Company Overview",
                "Business Model and GTM",
                "Funding & Investor Profile", 
                "Growth Momentum",
                "Visibility & Market Sentiment",
                "Risks and Challenges",
                "Outlook",
                "Disclosure Gaps"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool/generate_structured_dashboard", response_model=DashboardResponse)
async def generate_structured_dashboard(req: DashboardRequest):
    """Tool: Generate dashboard using structured payload data"""
    try:
        # Import OpenAI client
        from openai import OpenAI
        
        # Load the structured payload
        payload_file = Path(f"data/payloads/{req.company_id}.json")
        if not payload_file.exists():
            raise HTTPException(status_code=404, detail=f"Payload not found for {req.company_id}")
        
        with open(payload_file) as f:
            payload_data = json.load(f)
        
        # Load the dashboard prompt
        prompt_file = Path("src/prompts/dashboard_system.md")
        with open(prompt_file) as f:
            system_prompt = f.read()
        
        # Generate dashboard using OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate a PE dashboard for this company data:\n{json.dumps(payload_data, indent=2)}"}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        dashboard_markdown = response.choices[0].message.content
        
        return DashboardResponse(
            markdown=dashboard_markdown,
            company_id=req.company_id,
            status="success"
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Company {req.company_id} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tool/generate_rag_dashboard", response_model=DashboardResponse)
async def generate_rag_dashboard(req: DashboardRequest):
    """Tool: Generate dashboard using RAG/vector search"""
    try:
        # Use your existing RAG dashboard function
        rag_request = RAGDashboardRequest(company_id=req.company_id)
        result = await rag_dashboard_func(rag_request)
        
        # Extract markdown from result
        if isinstance(result, dict):
            dashboard_markdown = result.get("dashboard", str(result))
        else:
            dashboard_markdown = str(result)
        
        return DashboardResponse(
            markdown=dashboard_markdown,
            company_id=req.company_id,
            status="success"
        )
        
    except Exception as e:
        # Fallback: Try to generate a basic RAG dashboard
        try:
            from src.vector_db import VectorDB
            from openai import OpenAI
            
            # Search vector DB
            db = VectorDB()
            search_results = db.search(
                query="company overview funding products",
                company_id=req.company_id,
                n_results=10
            )
            
            # Combine search results
            context = "\n\n".join([r['text'] for r in search_results])
            
            # Generate dashboard
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            prompt_file = Path("src/prompts/dashboard_system.md")
            with open(prompt_file) as f:
                system_prompt = f.read()
            
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate a PE dashboard based on this context about {req.company_id}:\n{context}"}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return DashboardResponse(
                markdown=response.choices[0].message.content,
                company_id=req.company_id,
                status="success"
            )
        except:
            raise HTTPException(status_code=500, detail=f"Error generating RAG dashboard: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "MCP Server"}

if __name__ == "__main__":
    import uvicorn
    # Use port 9000 to avoid conflict with your existing services
    uvicorn.run(app, host="0.0.0.0", port=9000)