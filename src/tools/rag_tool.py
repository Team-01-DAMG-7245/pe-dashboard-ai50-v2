from typing import List, Dict
from src.vector_db import VectorDB

vector_db = VectorDB()

async def rag_search_company(company_id: str, query: str) -> List[Dict]:
    """
    Tool: rag_search_company
    Perform retrieval-augmented search for the specified company and query.
    """
    try:
        results = vector_db.search(
            query=query,
            company_id=company_id,
            n_results=5
        )
        
        formatted_results = []
        for result in results:
            score = abs(result.get('score', 0))
            formatted_results.append({
                "text": result.get('text', ''),
                "source_url": result.get('metadata', {}).get('source_type', ''),
                "score": score
            })
        
        return formatted_results if formatted_results else [
            {
                "text": f"No results found for {company_id}",
                "source_url": "",
                "score": 0.0
            }
        ]
        
    except Exception as e:
        print(f"RAG search error: {str(e)}")
        return [
            {
                "text": f"Search available for {company_id}",
                "source_url": "",
                "score": 0.0
            }
        ]