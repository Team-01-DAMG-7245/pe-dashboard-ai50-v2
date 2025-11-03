"""
FastAPI RAG endpoints for Lab 4
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import os

from vector_db import VectorDB
from chunker import chunk_company_data

app = FastAPI(title="Lab 4 RAG API", version="1.0.0")

# Initialize vector database
vector_db = None

class SearchRequest(BaseModel):
    query: str
    company_id: Optional[str] = None
    n_results: int = 5

class SearchResponse(BaseModel):
    query: str
    results: List[Dict]

@app.on_event("startup")
async def startup_event():
    """Initialize vector DB and index test companies on startup"""
    global vector_db
    vector_db = VectorDB()
    
    # Index 5 test companies
    test_companies = ['anthropic', 'databricks', 'glean', 'cohere', 'openevidence']
    print("Indexing companies...")
    for company in test_companies:
        chunks = chunk_company_data(company)
        if chunks:
            vector_db.add_chunks(chunks, company)
    print("Ready to serve requests!")

@app.get("/")
async def root():
    return {"message": "Lab 4 RAG API - Use /rag/search endpoint"}

@app.post("/rag/search")
async def search_rag(request: SearchRequest):
    """Search endpoint for RAG - Lab 4 checkpoint"""
    try:
        results = vector_db.search(
            query=request.query,
            company_id=request.company_id,
            n_results=request.n_results
        )
        return SearchResponse(query=request.query, results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)