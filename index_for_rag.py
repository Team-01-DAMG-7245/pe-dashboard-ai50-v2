from src.chunker import chunk_company_data
from src.vector_db import VectorDB

# Initialize vector DB
vector_db = VectorDB()

# Index our 5 test companies  
companies = ['anthropic', 'databricks', 'glean', 'cohere', 'openevidence']

for company in companies:
    print(f"Indexing {company}...")
    chunks = chunk_company_data(company)
    if chunks:
        vector_db.add_chunks(chunks, company)
        print(f"  Added {len(chunks)} chunks")

print("Indexing complete!")
