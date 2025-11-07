"""
Text chunking module for RAG pipeline
Works with the company/initial/*.txt structure
"""

import tiktoken
from typing import List, Dict
import re
import json
import os
from datetime import datetime


class TextChunker:
    def __init__(self, chunk_size=750, overlap=100, max_chunk_size=1000):
        """Initialize chunker with token limits"""
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_chunk_size = max_chunk_size
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))
    
    def clean_text(self, text: str) -> str:
        """Clean scraped text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        return text.strip()
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Split text into chunks with metadata"""
        if not text or not text.strip():
            return []
        
        # Clean text
        text = self.clean_text(text)
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            
            if current_tokens + sentence_tokens > self.chunk_size:
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        'text': chunk_text,
                        'chunk_index': len(chunks),
                        'token_count': self.count_tokens(chunk_text),
                        'created_at': datetime.utcnow().isoformat(),
                        **(metadata or {})
                    })
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'chunk_index': len(chunks),
                'token_count': self.count_tokens(chunk_text),
                'created_at': datetime.utcnow().isoformat(),
                **(metadata or {})
            })
        
        return chunks


def chunk_company_data(company_id: str, raw_data_path: str = None) -> List[Dict]:
    """Chunk all text data for a company from initial folder"""
    if raw_data_path is None:
        # Get project root (3 levels up from lab4/chunker.py: src/lab4/chunker.py -> src -> root)
        # Use Path for more reliable path resolution
        from pathlib import Path
        file_path = Path(__file__).resolve()
        project_root = file_path.parent.parent.parent
        raw_data_path = os.path.join(str(project_root), 'data', 'raw')
    
    chunker = TextChunker()
    all_chunks = []
    
    # Path to the initial folder
    initial_path = os.path.join(raw_data_path, company_id, 'initial')
    
    if not os.path.exists(initial_path):
        print(f"No initial folder found for {company_id}")
        return []
    
    # Process each .txt file (prioritize _clean.txt files if available)
    txt_files = ['about.txt', 'blog.txt', 'careers.txt', 'homepage.txt', 'product.txt']
    
    for txt_file in txt_files:
        # First try _clean.txt version, then fall back to regular .txt
        source_type = txt_file.replace('.txt', '')
        clean_file_path = os.path.join(initial_path, f'{source_type}_clean.txt')
        regular_file_path = os.path.join(initial_path, txt_file)
        
        # Choose which file to use
        file_path = clean_file_path if os.path.exists(clean_file_path) else regular_file_path
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Get source type from filename (remove _clean suffix if present)
                
                metadata = {
                    'company_id': company_id,
                    'company_name': company_id.replace('_', ' ').title(),
                    'source_file': file_path,
                    'source_type': source_type,
                    'source_url': ''
                }
                
                # Add metadata from JSON if exists
                metadata_file = os.path.join(initial_path, f'{source_type}_metadata.json')
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        meta_data = json.load(f)
                        metadata['source_url'] = meta_data.get('source_url', '')
                
                chunks = chunker.chunk_text(text, metadata)
                all_chunks.extend(chunks)
                print(f"  Processed {source_type}: {len(chunks)} chunks")
                
            except Exception as e:
                print(f"  Error processing {txt_file}: {e}")
    
    return all_chunks


if __name__ == "__main__":
    # Test with anthropic
    chunks = chunk_company_data('anthropic')
    print(f"\nTotal chunks created: {len(chunks)}")
    if chunks:
        print(f"First chunk: {chunks[0]['text'][:100]}...")
        print(f"Token count: {chunks[0]['token_count']}")