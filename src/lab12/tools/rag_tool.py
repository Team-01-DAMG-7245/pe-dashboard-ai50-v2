from typing import List, Dict

# Try to import VectorDB, but handle import errors gracefully
vector_db = None
try:
    from src.lab4.vector_db import VectorDB
    vector_db = VectorDB()
except Exception as e:
    # If VectorDB can't be imported (e.g., onnxruntime DLL issue), 
    # we'll provide a fallback implementation
    import warnings
    warnings.warn(f"VectorDB not available: {str(e)[:100]}. RAG tool will return empty results.")
    vector_db = None

async def rag_search_company(company_id: str, query: str) -> List[Dict]:
    """
    Tool: rag_search_company
    Perform retrieval-augmented search for the specified company and query.
    """
    # If vector_db is not available, return a helpful message
    if vector_db is None:
        return [
            {
                "text": f"Vector DB not available (onnxruntime dependency issue). Cannot search for '{query}' for {company_id}.",
                "source_url": "",
                "score": 0.0
            }
        ]
    
    try:
        if not hasattr(vector_db, 'search'):
            return [
                {
                    "text": f"Vector DB not properly initialized. Cannot search for '{query}' for {company_id}.",
                    "source_url": "",
                    "score": 0.0
                }
            ]
        
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
                "text": f"Search error for {company_id}: {str(e)[:100]}",
                "source_url": "",
                "score": 0.0
            }
        ]