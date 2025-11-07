"""
Lab 8: Structured Pipeline Dashboard
Generate dashboard using structured payload pipeline
Goal: structured payload → LLM → Markdown dashboard
"""

import os
import json
from typing import Dict
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PE Dashboard API - Structured Pipeline")

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found. Please set it in .env file or environment variable.")
client = OpenAI(api_key=api_key)

class StructuredDashboardRequest(BaseModel):
    company_id: str

class StructuredDashboardResponse(BaseModel):
    company_id: str
    dashboard: str
    source: str = "structured_payload"

def load_dashboard_prompt() -> str:
    """Load the dashboard system prompt"""
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'dashboard_system.md')
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

@app.post("/dashboard/structured", response_model=StructuredDashboardResponse)
async def generate_structured_dashboard(request: StructuredDashboardRequest):
    """
    Lab 8: Generate dashboard using structured payload pipeline
    Goal: structured payload → LLM → Markdown dashboard
    
    This is more precise and less hallucinatory than RAG because it uses
    structured JSON data instead of retrieved text chunks.
    
    Tasks:
    1. Load data/payloads/<company_id>.json
    2. Pass as context to LLM with the same prompt
    3. Return Markdown dashboard
    """
    
    try:
        # Step 1: Load structured payload from data/payloads/<company_id>.json
        # Use relative path from project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        payload_path = os.path.join(project_root, "data", "payloads", f"{request.company_id}.json")
        
        if not os.path.exists(payload_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Structured payload not found for company: {request.company_id}. Expected file: data/payloads/{request.company_id}.json"
            )
        
        with open(payload_path, "r", encoding="utf-8") as f:
            payload_data = json.load(f)
        
        # Step 2: Format the structured payload as readable context
        # Convert JSON to a well-formatted string for the LLM
        context = json.dumps(payload_data, indent=2, ensure_ascii=False)
        
        # Step 3: Load the same dashboard prompt as RAG
        system_prompt = load_dashboard_prompt()
        
        # Step 4: Create user prompt emphasizing structured data advantages
        user_prompt = f"""Generate an investor-facing diligence dashboard for {request.company_id}.

Here is the structured payload (JSON) with normalized, validated data:

{context}

CRITICAL REQUIREMENTS:
1. Use ONLY the structured data provided above - do not add external information
2. This is STRUCTURED DATA, so it should be more precise and accurate than RAG
3. When a field is null or empty, say exactly "Not disclosed."
4. When an array is empty, say "Not disclosed."
5. If a claim seems like marketing, attribute it: "The company states..."
6. Never include personal emails or phone numbers
7. Use the structured fields directly - they are already validated
8. Must include ALL 8 sections in this EXACT order:
   - Company Overview
   - Business Model and GTM
   - Funding & Investor Profile
   - Growth Momentum
   - Visibility & Market Sentiment
   - Risks and Challenges
   - Outlook
   - Disclosure Gaps

ADVANTAGE OF STRUCTURED DATA:
- company_record: Use legal_name, founded_year, categories, total_raised_usd, etc.
- events: List funding events with dates, amounts, investors
- snapshots: Use headcount, growth metrics, job openings
- products: List product names, descriptions from products array
- leadership: Use leadership array for team information
- visibility: Use visibility array for market sentiment

The "Disclosure Gaps" section should list what important fields are null or missing in the structured payload."""
        
        # Step 5: Generate dashboard with structured data
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Low temperature for precision
            max_tokens=3000   # Enough for comprehensive dashboard
        )
        
        dashboard = response.choices[0].message.content
        
        # Step 6: Validate all 8 sections are present (same as RAG)
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
                max_tokens=3000
            )
            dashboard = response.choices[0].message.content
        
        # Final validation - ensure all sections present
        final_missing = [s for s in required_sections if s not in dashboard]
        if final_missing:
            # Add missing sections manually if LLM still fails
            for section in final_missing:
                section_name = section.replace("## ", "")
                dashboard += f"\n\n{section}\n\nNot disclosed.\n"
        
        # Checkpoint: Verify "Not disclosed." usage
        if "not disclosed" not in dashboard.lower():
            print("Warning: Dashboard may not use 'Not disclosed.' for missing data")
        
        return StructuredDashboardResponse(
            company_id=request.company_id,
            dashboard=dashboard,
            source="structured_payload"
        )
    
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, 
            detail=f"Payload file not found: data/payloads/{request.company_id}.json"
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid JSON in payload file: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating structured dashboard: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

