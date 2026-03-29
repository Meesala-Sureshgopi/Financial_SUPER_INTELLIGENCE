import chromadb
from sentence_transformers import SentenceTransformer
import os
import hashlib
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma"
MODEL_NAME = "all-MiniLM-L6-v2"

# Lazy load models and DB to prevent startup delays
_embedder = None
_chroma_client = None
_collection = None

def _get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(MODEL_NAME)
    return _embedder

def _get_collection():
    global _chroma_client, _collection
    if _chroma_client is None:
        if not CHROMA_DIR.exists():
            CHROMA_DIR.mkdir(parents=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _chroma_client.get_or_create_collection("filings")
    return _collection

def chunk_text(text: str, size=600, overlap=100) -> List[str]:
    """Split text into overlapping chunks for embedding."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), size - overlap):
        chunk = " ".join(words[i:i + size])
        chunks.append(chunk)
        if i + size >= len(words):
            break
    return chunks

async def ingest_filing(ticker: str, filing_text: str, source_url: str):
    """Chunk, embed, and store a filing in ChromaDB."""
    try:
        embedder = _get_embedder()
        collection = _get_collection()
        
        chunks = chunk_text(filing_text)
        embeddings = embedder.encode(chunks).tolist()
        
        ids = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            # Create a unique hash for each chunk to avoid duplicates
            h = hashlib.md5(chunk.encode()).hexdigest()[:8]
            ids.append(f"{ticker}_{i}_{h}")
            metadatas.append({"ticker": ticker, "source": source_url})
            
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        logger.info(f"Ingested {len(chunks)} chunks for {ticker} from {source_url}")
    except Exception as e:
        logger.error(f"Failed to ingest filing for {ticker}: {e}")

async def retrieve_context(query: str, ticker: str, k: int = 5) -> List[str]:
    """Retrieve relevant filing chunks from ChromaDB for a ticker."""
    try:
        embedder = _get_embedder()
        collection = _get_collection()
        
        query_embedding = embedder.encode([query]).tolist()
        
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=k,
            where={"ticker": ticker}
        )
        
        if not results or not results["documents"]:
            return []
            
        return results["documents"][0]
    except Exception as e:
        logger.error(f"Failed to retrieve context for {ticker}: {e}")
        return []
