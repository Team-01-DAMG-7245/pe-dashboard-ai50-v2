from typing import List, Dict
import os
from pathlib import Path

def retrieve_context(company_id: str, top_k: int = 10) -> List[Dict]:
    """
    Retrieve context from vector database for a company.
    Returns list of chunks with text and metadata.
    """
    try:
        # Try to import and use vector DB
        # Support both local and Docker paths
        try:
            from src.lab4.vector_db import VectorDB
        except ImportError:
            from lab4.vector_db import VectorDB
        
        vector_db = VectorDB()
        results = vector_db.search(
            query=f"{company_id} company overview business model products funding",
            company_id=company_id,
            n_results=top_k
        )
        
        # Format results
        chunks = []
        for result in results:
            chunks.append({
                "text": result.get("text", ""),
                "source_url": result.get("metadata", {}).get("source_url", ""),
                "score": result.get("score", 0.0)
            })
        
        return chunks if chunks else []
        
    except ImportError as e:
        # Vector DB not available (e.g., chromadb not installed)
        import traceback
        print(f"Warning: Vector DB not available: {e}")
        traceback.print_exc()
        return []
    except Exception as e:
        # Any other error - return empty
        import traceback
        print(f"Warning: Error retrieving context: {e}")
        traceback.print_exc()
        return []
