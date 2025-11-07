import sys
import os
sys.path.append('..')  # Add parent directory to path

from lab4.chunker import chunk_company_data
from lab4.vector_db import VectorDB

# Initialize vector DB
vector_db = VectorDB()

# Index our 5 test companies
companies = ['anthropic', 'databricks', 'glean', 'cohere', 'openevidence']

for company in companies:
    print(f"Indexing {company}...")
    # Use the correct path to data/raw
    chunks = chunk_company_data(company, '../data/raw')
    if chunks:
        vector_db.add_chunks(chunks, company)
        print(f"  Added {len(chunks)} chunks")
    else:
        print(f"  No chunks found for {company}")

print("Indexing complete!")