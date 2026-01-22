"""
Memory Layer - Context Memory and Storage System
Stores and retrieves previously processed contexts for intelligent reuse
"""
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class ContextMemory:
    """Data class for context memory entry"""
    id: int
    query: str
    context: str
    response: str
    metadata: Dict
    created_at: str
    last_accessed: str
    access_count: int
    tags: List[str]
    confidence_score: float = 0.0

class ContextMemoryStore:
    """
    Memory layer that stores and retrieves processed contexts
    Enables intelligent reuse and context optimization
    """
    
    def __init__(self, db_path: str = "./.memory_store/contexts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for memory storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main context memory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT NOT NULL,
                query TEXT NOT NULL,
                context_hash TEXT NOT NULL,
                context TEXT NOT NULL,
                response TEXT NOT NULL,
                metadata TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                confidence_score REAL DEFAULT 0.0,
                model_id TEXT,
                UNIQUE(query_hash, context_hash)
            )
        ''')
        
        # Conversation thread table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_threads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT UNIQUE NOT NULL,
                title TEXT,
                context_ids TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary TEXT
            )
        ''')
        
        # Related contexts table for fast retrieval
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS context_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                related_id INTEGER NOT NULL,
                relation_type TEXT,
                similarity_score REAL,
                FOREIGN KEY(source_id) REFERENCES context_memory(id),
                FOREIGN KEY(related_id) REFERENCES context_memory(id)
            )
        ''')
        
        # Indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_query_hash ON context_memory(query_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON context_memory(tags)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON context_memory(created_at)')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def _hash_text(text: str) -> str:
        """Generate hash of text"""
        return hashlib.sha256(text.encode()).hexdigest()
    
    def store_context(self, query: str, context: str, response: str, 
                     metadata: Dict = None, tags: List[str] = None, 
                     confidence_score: float = 0.0, model_id: str = None) -> int:
        """
        Store a processed context in memory
        Args:
            query: User query
            context: Retrieved context
            response: Model response
            metadata: Additional metadata
            tags: Topic tags for categorization
            confidence_score: Confidence in response (0.0-1.0)
            model_id: Model used to generate response
        Returns:
            ID of stored context
        """
        query_hash = self._hash_text(query)
        context_hash = self._hash_text(context)
        metadata_json = json.dumps(metadata) if metadata else None
        tags_json = json.dumps(tags) if tags else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO context_memory 
                (query_hash, query, context_hash, context, response, metadata, tags, 
                 confidence_score, model_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (query_hash, query, context_hash, context, response, metadata_json, 
                  tags_json, confidence_score, model_id))
            conn.commit()
            context_id = cursor.lastrowid
            conn.close()
            return context_id
        except sqlite3.IntegrityError:
            # Update existing entry
            cursor.execute('''
                UPDATE context_memory 
                SET access_count = access_count + 1, 
                    last_accessed = CURRENT_TIMESTAMP
                WHERE query_hash = ? AND context_hash = ?
            ''', (query_hash, context_hash))
            conn.commit()
            cursor.execute('''
                SELECT id FROM context_memory 
                WHERE query_hash = ? AND context_hash = ?
            ''', (query_hash, context_hash))
            context_id = cursor.fetchone()[0]
            conn.close()
            return context_id
        except Exception as e:
            print(f"Error storing context: {e}")
            conn.close()
            return -1
    
    def retrieve_similar_contexts(self, query: str, limit: int = 5, 
                                  min_confidence: float = 0.0) -> List[ContextMemory]:
        """
        Retrieve similar contexts from memory
        Args:
            query: Query to find similar contexts for
            limit: Maximum results
            min_confidence: Minimum confidence score
        Returns:
            List of similar contexts
        """
        query_hash = self._hash_text(query)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First try exact match
        cursor.execute('''
            SELECT id, query, context, response, metadata, tags, created_at, 
                   last_accessed, access_count, confidence_score
            FROM context_memory 
            WHERE query_hash = ? AND confidence_score >= ?
            ORDER BY access_count DESC, confidence_score DESC
            LIMIT ?
        ''', (query_hash, min_confidence, limit))
        
        results = cursor.fetchall()
        
        # If no exact match, get related contexts
        if not results:
            cursor.execute('''
                SELECT id, query, context, response, metadata, tags, created_at, 
                       last_accessed, access_count, confidence_score
                FROM context_memory 
                WHERE confidence_score >= ?
                ORDER BY last_accessed DESC, access_count DESC
                LIMIT ?
            ''', (min_confidence, limit))
            results = cursor.fetchall()
        
        conn.close()
        
        memories = []
        for row in results:
            # SELECT order: id, query, context, response, metadata, tags,
            # created_at, last_accessed, access_count, confidence_score
            memory = ContextMemory(
                id=row[0],
                query=row[1],
                context=row[2],
                response=row[3],
                metadata=json.loads(row[4]) if row[4] else {},
                tags=json.loads(row[5]) if row[5] else [],
                created_at=row[6],
                last_accessed=row[7],
                access_count=row[8],
                confidence_score=row[9]
            )
            memories.append(memory)
        
        return memories
    
    def get_memory_by_tags(self, tags: List[str], limit: int = 10) -> List[ContextMemory]:
        """
        Retrieve contexts by tags
        Args:
            tags: Topic tags to search for
            limit: Maximum results
        Returns:
            List of contexts with matching tags
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        memories = []
        for tag in tags:
            cursor.execute('''
                SELECT id, query, context, response, metadata, tags, created_at, 
                       last_accessed, access_count, confidence_score
                FROM context_memory 
                WHERE tags LIKE ?
                ORDER BY access_count DESC
                LIMIT ?
            ''', (f'%{tag}%', limit))
            
            results = cursor.fetchall()
            for row in results:
                memory = ContextMemory(
                    id=row[0],
                    query=row[1],
                    context=row[2],
                    response=row[3],
                    metadata=json.loads(row[4]) if row[4] else {},
                    tags=json.loads(row[5]) if row[5] else [],
                    created_at=row[6],
                    last_accessed=row[7],
                    access_count=row[8],
                    confidence_score=row[9]
                )
                memories.append(memory)
        
        conn.close()
        return memories
    
    def create_conversation_thread(self, thread_id: str, title: str = None) -> bool:
        """
        Create a new conversation thread for grouping contexts
        Args:
            thread_id: Unique thread identifier
            title: Human-readable title
        Returns:
            Success status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO conversation_threads (thread_id, title, context_ids)
                VALUES (?, ?, '[]')
            ''', (thread_id, title))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def add_to_thread(self, thread_id: str, context_id: int) -> bool:
        """
        Add context to conversation thread
        Args:
            thread_id: Thread identifier
            context_id: Context memory ID
        Returns:
            Success status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT context_ids FROM conversation_threads WHERE thread_id = ?
            ''', (thread_id,))
            result = cursor.fetchone()
            
            if result:
                context_ids = json.loads(result[0])
                if context_id not in context_ids:
                    context_ids.append(context_id)
                    cursor.execute('''
                        UPDATE conversation_threads 
                        SET context_ids = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE thread_id = ?
                    ''', (json.dumps(context_ids), thread_id))
                    conn.commit()
            
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding to thread: {e}")
            conn.close()
            return False
    
    def get_memory_stats(self) -> Dict:
        """Get statistics about memory store"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM context_memory')
        total_contexts = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(confidence_score) FROM context_memory')
        avg_confidence = cursor.fetchone()[0] or 0.0
        
        cursor.execute('SELECT SUM(access_count) FROM context_memory')
        total_accesses = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM conversation_threads')
        total_threads = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM context_memory 
            WHERE created_at > datetime('now', '-1 day')
        ''')
        recent_contexts = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_contexts": total_contexts,
            "average_confidence": f"{avg_confidence:.2f}",
            "total_accesses": total_accesses,
            "conversation_threads": total_threads,
            "recent_contexts_24h": recent_contexts,
            "db_path": str(self.db_path)
        }
    
    def cleanup_old_contexts(self, days: int = 30) -> int:
        """
        Remove old context memories
        Args:
            days: Delete contexts older than N days
        Returns:
            Number of contexts deleted
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        date_threshold = datetime.now() - timedelta(days=days)
        cursor.execute('''
            DELETE FROM context_memory 
            WHERE created_at < ? AND access_count < 5
        ''', (date_threshold,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
