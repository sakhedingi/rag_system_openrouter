"""
Cache-Augmented Generation (CAG) - Prompt Caching System
Implements context caching to reduce token consumption and improve response consistency
"""
import json
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

class PromptCache:
    """Manages cached prompts and responses for CAG"""
    
    def __init__(self, db_path: str = "./.cag_cache/prompts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for prompt caching"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cached_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT UNIQUE NOT NULL,
                query TEXT NOT NULL,
                context_hash TEXT NOT NULL,
                context TEXT NOT NULL,
                response TEXT NOT NULL,
                model_id TEXT NOT NULL,
                tokens_saved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_hash TEXT UNIQUE NOT NULL,
                chunk_content TEXT NOT NULL,
                chunk_metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reuse_count INTEGER DEFAULT 1
            )
        ''')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def _hash_text(text: str) -> str:
        """Generate hash of text for efficient comparison"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def cache_context_chunk(self, content: str, metadata: Dict = None) -> str:
        """
        Cache a context chunk for reuse
        Args:
            content: Context chunk text
            metadata: Optional metadata about the chunk
        Returns:
            Hash of the cached chunk
        """
        chunk_hash = self._hash_text(content)
        metadata_json = json.dumps(metadata) if metadata else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO context_chunks (chunk_hash, chunk_content, chunk_metadata)
                VALUES (?, ?, ?)
            ''', (chunk_hash, content, metadata_json))
            conn.commit()
        except sqlite3.IntegrityError:
            # Update reuse count if already cached
            cursor.execute('''
                UPDATE context_chunks 
                SET reuse_count = reuse_count + 1
                WHERE chunk_hash = ?
            ''', (chunk_hash,))
            conn.commit()
        
        conn.close()
        return chunk_hash
    
    def get_cached_response(self, query: str, context: str = None) -> Optional[Dict]:
        """
        Retrieve cached response if available
        Args:
            query: User query
            context: Optional context text
        Returns:
            Cached response dict or None
        """
        query_hash = self._hash_text(query)
        context_hash = self._hash_text(context) if context else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if context_hash:
            cursor.execute('''
                SELECT response, tokens_saved, access_count FROM cached_prompts
                WHERE query_hash = ? AND context_hash = ?
            ''', (query_hash, context_hash))
        else:
            cursor.execute('''
                SELECT response, tokens_saved, access_count FROM cached_prompts
                WHERE query_hash = ?
            ''', (query_hash,))
        
        result = cursor.fetchone()
        
        if result:
            # Update access stats
            cursor.execute('''
                UPDATE cached_prompts 
                SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE query_hash = ?
            ''', (query_hash,))
            conn.commit()
            conn.close()
            
            return {
                "response": result[0],
                "tokens_saved": result[1],
                "access_count": result[2],
                "cached": True
            }
        
        conn.close()
        return None
    
    def cache_response(self, query: str, context: str, response: str, 
                      model_id: str, tokens_saved: int = 0) -> bool:
        """
        Cache a response for future reuse
        Args:
            query: User query
            context: Context used
            response: Model response
            model_id: Model ID used
            tokens_saved: Estimated tokens saved by using cache
        Returns:
            Success status
        """
        query_hash = self._hash_text(query)
        context_hash = self._hash_text(context) if context else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO cached_prompts 
                (query_hash, query, context_hash, context, response, model_id, tokens_saved)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (query_hash, query, context_hash, context, response, model_id, tokens_saved))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
        except Exception as e:
            print(f"Error caching response: {e}")
            conn.close()
            return False
    
    def get_similar_context_chunks(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Get frequently reused context chunks
        Args:
            query: Search query (optional filter)
            limit: Maximum results
        Returns:
            List of frequently cached chunks
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT chunk_content, chunk_metadata, reuse_count FROM context_chunks
            ORDER BY reuse_count DESC
            LIMIT ?
        ''', (limit,))
        
        results = [
            {
                "content": row[0],
                "metadata": json.loads(row[1]) if row[1] else None,
                "reuse_count": row[2]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return results
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM cached_prompts')
        prompt_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(tokens_saved) FROM cached_prompts')
        total_tokens_saved = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(access_count) FROM cached_prompts')
        total_hits = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM context_chunks')
        chunk_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(reuse_count) FROM context_chunks')
        total_chunk_reuses = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "cached_prompts": prompt_count,
            "total_tokens_saved": total_tokens_saved,
            "total_cache_hits": total_hits,
            "context_chunks": chunk_count,
            "chunk_reuses": total_chunk_reuses,
            "efficiency": f"{(total_hits / max(prompt_count, 1)) * 100:.1f}% hit rate"
        }
    
    def clear_cache(self, older_than_days: int = None):
        """
        Clear cached responses
        Args:
            older_than_days: Only clear entries older than N days
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if older_than_days:
            date_threshold = datetime.now() - timedelta(days=older_than_days)
            cursor.execute('''
                DELETE FROM cached_prompts 
                WHERE created_at < ?
            ''', (date_threshold,))
        else:
            cursor.execute('DELETE FROM cached_prompts')
            cursor.execute('DELETE FROM context_chunks')
        
        conn.commit()
        conn.close()
        print("[OK] Cache cleared")
