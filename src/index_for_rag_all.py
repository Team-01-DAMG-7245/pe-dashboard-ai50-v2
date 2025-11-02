import os
import sys
from pathlib import Path

sys.path.append('src')

from vector_db import VectorDB
from chunker import chunk_company_data

print("=" * 60)
print("INDEXING ALL COMPANIES FOR LAB 4")
print("=" * 60)

companies = [d for d in os.listdir('data/raw') if os.path.isdir(f'data/raw/{d}')]
companies.sort()

print(f"Found {len(companies)} companies to index")
print(f"Companies: {', '.join(companies[:5])}... and {len(companies)-5} more")

vector_db = VectorDB()

successful = 0
total_chunks = 0

for i, company in enumerate(companies, 1):
    print(f"\n[{i}/{len(companies)}] Indexing {company}...")
    chunks = chunk_company_data(company)
    if chunks:
        vector_db.add_chunks(chunks, company)
        successful += 1
        total_chunks += len(chunks)
        print(f"  ✓ Added {len(chunks)} chunks")
    else:
        print(f"  ⚠ No chunks generated")

print("\n" + "=" * 60)
print(f"✅ INDEXING COMPLETE!")
print(f"   Companies indexed: {successful}/{len(companies)}")
print(f"   Total chunks in DB: {total_chunks}")

import chromadb
client = chromadb.PersistentClient(path="data/vector_db")
collection = client.get_collection("ai50_companies")
print(f"   Verified chunks in vector DB: {collection.count()}")
print("=" * 60)
