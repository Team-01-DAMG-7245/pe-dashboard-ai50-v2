import os
import sys
from pathlib import Path

# Fix NumPy 2.x compatibility
import numpy as np
if not hasattr(np, 'float_'):
    np.float_ = np.float64
if not hasattr(np, 'int_'):
    np.int_ = np.int64
if not hasattr(np, 'uint'):
    np.uint = np.uint64

# Mock onnxruntime to prevent DLL errors
from types import ModuleType
import importlib.util
class MockONNXRuntime(ModuleType):
    def __init__(self):
        super().__init__('onnxruntime')
        self.__spec__ = importlib.util.spec_from_loader('onnxruntime', loader=None)
sys.modules['onnxruntime'] = MockONNXRuntime()

# Add project root and src to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from lab4.vector_db import VectorDB
from lab4.chunker import chunk_company_data

print("=" * 60)
print("INDEXING ALL COMPANIES FOR LAB 4")
print("=" * 60)

data_raw_path = os.path.join(project_root, 'data', 'raw')
companies = [d for d in os.listdir(data_raw_path) if os.path.isdir(os.path.join(data_raw_path, d))]
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
        print(f"  [OK] Added {len(chunks)} chunks")
    else:
        print(f"  [WARNING] No chunks generated")

print("\n" + "=" * 60)
print(f"[OK] INDEXING COMPLETE!")
print(f"   Companies indexed: {successful}/{len(companies)}")
print(f"   Total chunks in DB: {total_chunks}")

import chromadb
vector_db_path = os.path.join(project_root, "data", "vector_db")
client = chromadb.PersistentClient(path=vector_db_path)
collection = client.get_collection("ai50_companies")
print(f"   Verified chunks in vector DB: {collection.count()}")
print("=" * 60)
