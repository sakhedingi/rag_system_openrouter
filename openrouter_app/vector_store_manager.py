"""
Vector Store Manager for Pre-Vectorization
Handles persistent storage, caching, and efficient retrieval of embeddings
"""
import json
import os
import pickle
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import numpy as np
from .embedding import embed_with_openrouter, cosine_similarity

class VectorStoreManager:
    """Manages pre-vectorized knowledge base with persistent caching"""
    
    def __init__(self, cache_dir: str = "./.vector_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.metadata_file = self.cache_dir / "metadata.json"
        self.vectors_file = self.cache_dir / "vectors.pkl"
        self.store = []
        self.metadata = self._load_metadata()
        
    def _load_metadata(self) -> Dict:
        """Load metadata about cached vectors"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading metadata: {e}")
        return {"files": {}, "last_updated": None, "model_id": None}
    
    def _save_metadata(self):
        """Save metadata about cached vectors"""
        self.metadata["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata: {e}")
    
    def _get_file_hash(self, file_path: str) -> str:
        """Calculate hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"Error calculating file hash: {e}")
            return ""
    
    def _is_cache_valid(self, folder_path: str, embed_model_id: str) -> bool:
        """Check if cached vectors are still valid"""
        if not self.vectors_file.exists():
            return False
        
        if self.metadata.get("model_id") != embed_model_id:
            return False
        
        # Check if any files have changed
        current_files = {}
        for filename in os.listdir(folder_path):
            if filename.endswith(('.txt', '.pdf', '.docx')):
                file_path = os.path.join(folder_path, filename)
                current_files[filename] = self._get_file_hash(file_path)
        
        # Compare with cached metadata
        cached_files = self.metadata.get("files", {})
        return current_files == cached_files
    
    def build_from_folder(self, folder_path: str, embed_model_id: str, documents: List[Dict] = None) -> List[Dict]:
        """
        Build vector store from folder, using cache if valid
        Args:
            folder_path: Path to folder with documents
            embed_model_id: Embedding model ID
            documents: Optional pre-loaded documents
        Returns:
            List of document entries with embeddings
        """
        # Check if cache is valid
        if self._is_cache_valid(folder_path, embed_model_id):
            print("[OK] Loading from cache...")
            return self._load_from_cache()
        
        print("[REFRESH] Building new vector store...")
        from .semantic_search import load_documents_from_folder
        
        if documents is None:
            documents = load_documents_from_folder(folder_path)
        
        store = []
        file_hashes = {}
        
        # Chunk documents into smaller passages to improve retrieval granularity
        chunk_size = 1000  # characters per chunk (approximate)
        chunk_overlap = 200  # overlap between chunks

        for doc in documents:
            text = doc.get("content", "")
            filename = doc.get("filename", "unknown")

            # Compute and store file hash for original file
            file_path = os.path.join(folder_path, filename)
            file_hashes[filename] = self._get_file_hash(file_path)

            if not text:
                print(f"[ERROR] Empty content: {filename}")
                continue

            # Create overlapping chunks
            start = 0
            chunk_index = 0
            text_len = len(text)
            while start < text_len:
                end = min(start + chunk_size, text_len)
                chunk_text = text[start:end]
                chunk_name = f"{filename}__chunk_{chunk_index}"

                embedding = embed_with_openrouter(embed_model_id, chunk_text)
                if embedding:
                    store.append({
                        "filename": chunk_name,
                        "source": filename,
                        "content": chunk_text,
                        "embedding": embedding,
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"[OK] Embedded chunk: {chunk_name}")
                else:
                    print(f"[ERROR] Failed to embed chunk: {chunk_name}")

                chunk_index += 1
                # Advance with overlap
                start = end - chunk_overlap if end < text_len else end
        
        # Update metadata
        self.metadata["files"] = file_hashes
        self.metadata["model_id"] = embed_model_id
        self._save_metadata()
        
        # Save to cache
        self._save_to_cache(store)
        self.store = store
        
        return store
    
    def _save_to_cache(self, store: List[Dict]):
        """Persist vector store to disk"""
        try:
            with open(self.vectors_file, 'wb') as f:
                pickle.dump(store, f)
            print(f"[SAVED] Cached {len(store)} embeddings")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def _load_from_cache(self) -> List[Dict]:
        """Load vector store from disk"""
        try:
            with open(self.vectors_file, 'rb') as f:
                self.store = pickle.load(f)
            print(f"[LOADED] Loaded {len(self.store)} embeddings from cache")
            return self.store
        except Exception as e:
            print(f"Error loading cache: {e}")
            return []
    
    def semantic_search(self, query_text: str, embed_model_id: str, top_k: int = 3) -> List[Tuple]:
        """
        Perform semantic search on cached vectors
        Args:
            query_text: User query
            embed_model_id: Embedding model ID
            top_k: Number of results to return
        Returns:
            List of tuples (filename, score, content)
        """
        query_embedding = embed_with_openrouter(embed_model_id, query_text)
        if not query_embedding:
            print("Failed to generate embedding for query.")
            return []
        
        scored = []
        for entry in self.store:
            score = cosine_similarity(query_embedding, entry["embedding"])
            scored.append((entry["filename"], score, entry["content"]))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    
    def clear_cache(self):
        """Clear all cached vectors"""
        try:
            if self.vectors_file.exists():
                self.vectors_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            self.store = []
            self.metadata = {"files": {}, "last_updated": None, "model_id": None}
            print("[OK] Cache cleared")
        except Exception as e:
            print(f"Error clearing cache: {e}")
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache"""
        return {
            "num_vectors": len(self.store),
            "cache_dir": str(self.cache_dir),
            "metadata": self.metadata,
            "cache_exists": self.vectors_file.exists()
        }
