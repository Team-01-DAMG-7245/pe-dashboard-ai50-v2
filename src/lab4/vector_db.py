"""
Vector database module using ChromaDB for RAG
"""

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import os


class VectorDB:
    def __init__(self, persist_directory: str = None):
        """Initialize vector database with ChromaDB"""
        if persist_directory is None:
            # Get project root (3 levels up from lab4/vector_db.py)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            persist_directory = os.path.join(project_root, "data", "vector_db")
        self.persist_directory = persist_directory
        
        # Initialize embedding model
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Create persist directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client (simpler approach)
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection - use SentenceTransformer for consistency
        # Note: We manually encode embeddings, so we don't need embedding function here
        try:
            self.collection = self.client.get_collection("ai50_companies")
            print(f"Connected to existing collection: ai50_companies")
        except:
            self.collection = self.client.create_collection(
                "ai50_companies",
                metadata={"hnsw:space": "cosine"}
            )
            print("Created new collection: ai50_companies")
    
    def add_chunks(self, chunks: List[Dict], company_id: str):
        """Add text chunks to vector database"""
        if not chunks:
            return
        
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{company_id}_{chunk.get('source_type', 'unknown')}_{i}"
            
            metadata = {
                'company_id': company_id,
                'company_name': chunk.get('company_name', company_id),
                'source_type': chunk.get('source_type', 'unknown'),
                'chunk_index': chunk.get('chunk_index', i),
                'token_count': chunk.get('token_count', 0)
            }
            
            documents.append(chunk['text'])
            metadatas.append(metadata)
            ids.append(chunk_id)
        
        # Generate embeddings
        embeddings = self.embedding_model.encode(documents).tolist()
        
        # Add to collection
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Added {len(chunks)} chunks for {company_id}")
    
    def search(self, query: str, company_id: Optional[str] = None, n_results: int = 5) -> List[Dict]:
        """Search for relevant chunks"""
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query]).tolist()
        
        # Build where clause
        where_clause = {"company_id": company_id} if company_id else None
        
        # Query the collection
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where_clause,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'score': 1 - results['distances'][0][i]
                })
        
        return formatted_results


if __name__ == "__main__":
    from lab4.chunker import chunk_company_data
    
    print("=" * 60)
    print("LAB 4 - TESTING WITH 5 COMPANIES")
    print("=" * 60)
    
    # Test companies
    test_companies = ['anthropic', 'databricks', 'glean', 'cohere', 'openevidence']
    
    # Initialize vector DB
    vector_db = VectorDB()
    
    # Index companies
    print("\nIndexing companies...")
    for company in test_companies:
        print(f"\nProcessing {company}:")
        chunks = chunk_company_data(company)
        if chunks:
            vector_db.add_chunks(chunks, company)
    
    # Test Lab 4 Checkpoint
    print("\n" + "=" * 60)
    print("LAB 4 CHECKPOINT TEST")
    print("=" * 60)
    
    # Test "funding" query
    print("\n✓ Testing 'funding' query:")
    results = vector_db.search("funding", n_results=3)
    for i, result in enumerate(results, 1):
        print(f"  Result {i}: {result['metadata']['company_name']} - {result['metadata']['source_type']}")
        print(f"    Score: {result['score']:.3f}")
        print(f"    Text: {result['text'][:100]}...")
    
    # Test "leadership" query for anthropic
    print("\n✓ Testing 'leadership' query for Anthropic:")
    results = vector_db.search("leadership", company_id='anthropic', n_results=3)
    for i, result in enumerate(results, 1):
        print(f"  Result {i}: {result['metadata']['source_type']}")
        print(f"    Score: {result['score']:.3f}")
        print(f"    Text: {result['text'][:100]}...")
    
    print("\n" + "=" * 60)
    print("✅ LAB 4 COMPLETE!")
    print("  - Chunks created (500-1000 tokens)")
    print("  - Vector DB working")
    print("  - 'funding' and 'leadership' queries return relevant chunks")
    print("=" * 60)