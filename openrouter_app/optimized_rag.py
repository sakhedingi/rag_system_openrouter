"""
Optimized RAG with CAG and Memory Integration
Combines pre-vectorization, cache-augmented generation, and memory layer
Now uses OpenRouter API instead of AWS Bedrock
"""
from typing import Dict, List, Optional
from .vector_store_manager import VectorStoreManager
from .prompt_cache import PromptCache
from .context_memory import ContextMemoryStore
from .system_prompt import load_system_prompt
from .chat import invoke_model_stream, chat_with_openrouter

class OptimizedRAG:
    """Integrated RAG system with vectorization, caching, and memory"""

    def __init__(self):
        self.vector_store_manager = VectorStoreManager()
        self.prompt_cache = PromptCache()
        self.memory_store = ContextMemoryStore()

    def initialize_knowledge_base(self, folder_path: str, embed_model_id: str) -> Dict:
        """Initialize pre-vectorized knowledge base"""
        print("[*] Initializing optimized knowledge base...")
        store = self.vector_store_manager.build_from_folder(folder_path, embed_model_id)
        stats = self.vector_store_manager.get_cache_stats()
        print(f"[OK] Knowledge base ready: {stats['num_vectors']} documents cached")
        return stats

    def answer_with_optimization(self, model_id: str, user_question: str,
                                 embed_model_id: str, message_history: List[Dict] = None,
                                 temperature: float = 0.7, top_p: float = 0.9,
                                 use_cache: bool = True, store_memory: bool = True,
                                 retrieve_past_contexts: bool = True) -> Dict:
        """Answer question with full optimization (RAG + CAG + Memory)"""
        stats = {
            "cache_hit": False,
            "memory_reused": False,
            "contexts_retrieved": 0,
            "tokens_saved": 0,
            "optimization_source": []
        }

        if use_cache:
            cached_response = self.prompt_cache.get_cached_response(user_question)
            if cached_response:
                print(f"[CACHE] Cache hit! (saved {cached_response['tokens_saved']} tokens)")
                stats["cache_hit"] = True
                stats["tokens_saved"] = cached_response['tokens_saved']
                stats["optimization_source"].append("prompt_cache")
                return {
                    "response": cached_response['response'],
                    "stats": stats,
                    "from_cache": True
                }

        past_contexts = []
        if retrieve_past_contexts:
            past_contexts = self.memory_store.retrieve_similar_contexts(user_question, limit=3)
            if past_contexts:
                print(f"[MEM] Found {len(past_contexts)} similar contexts from memory")
                stats["memory_reused"] = True
                stats["optimization_source"].append("context_memory")
                
                # Check for exact match and return it directly
                for past_ctx in past_contexts:
                    if past_ctx.query.strip().lower() == user_question.strip().lower():
                        print(f"[MEM] Exact match found! Returning cached response")
                        return {
                            "response": past_ctx.response,
                            "stats": stats,
                            "from_memory": True
                        }

        retrieved_results = self.vector_store_manager.semantic_search(
            user_question, embed_model_id, top_k=3
        )
        stats["contexts_retrieved"] = len(retrieved_results)
        print(f"[SEARCH] Retrieved {len(retrieved_results)} relevant documents")

        context_parts = []

        for past_ctx in past_contexts:
            context_parts.append(f"[Memory - Confidence: {past_ctx.confidence_score:.2%}]")
            context_parts.append(past_ctx.response)
            context_parts.append("")

        for filename, score, content in retrieved_results:
            context_parts.append(f"[Document: {filename}]")
            # retrieved entries are now document chunks; include full chunk
            context_parts.append(content)
            context_parts.append("")

        combined_context = "\n".join(context_parts)

        for filename, score, content in retrieved_results:
            self.prompt_cache.cache_context_chunk(
                content,
                {"source": filename, "score": score}
            )

        response = self._invoke_model_with_context(
            model_id, user_question, combined_context, message_history,
            temperature, top_p
        )

        if response is None:
            return {
                "response": "Error generating response",
                "stats": stats,
                "error": True
            }

        if use_cache:
            estimated_tokens_saved = len(combined_context.split()) // 4
            self.prompt_cache.cache_response(
                user_question, combined_context, response, model_id,
                tokens_saved=estimated_tokens_saved
            )
            stats["tokens_saved"] = estimated_tokens_saved
            stats["optimization_source"].append("newly_cached")

        if store_memory:
            confidence_score = 0.85 if len(retrieved_results) > 0 else 0.5
            tags = self._extract_tags(user_question)

            context_id = self.memory_store.store_context(
                query=user_question,
                context=combined_context,
                response=response,
                metadata={
                    "source": "optimized_rag",
                    "retrieved_docs": len(retrieved_results),
                    "past_contexts_used": len(past_contexts)
                },
                tags=tags,
                confidence_score=confidence_score,
                model_id=model_id
            )
            print(f"[SAVED] Stored in memory (ID: {context_id})")
            stats["optimization_source"].append("memory_stored")

        return {
            "response": response,
            "stats": stats,
            "from_cache": False
        }

    def _invoke_model_with_context(self, model_id: str, user_question: str,
                                   context: str, message_history: List[Dict] = None,
                                   temperature: float = 0.7, top_p: float = 0.9) -> Optional[str]:
        """Invoke OpenRouter model with context"""

        if message_history is None:
            message_history = []

        try:
            system_prompt = load_system_prompt()

            # Build OpenAI-format messages for OpenRouter
            messages = []

            # Add system prompt as first message with system role
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            # Add message history if present
            if message_history:
                messages.extend(message_history)

            # Add user question with context
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion:\n{user_question}"
            })


            response = chat_with_openrouter(
                model_id,
                "",  # Message is already in messages list
                message_history=messages[:-1],  # Pass all but last as history
                temperature=temperature,
                top_p=top_p
            )

            if response and response.startswith("Error"):
                print(f"Error from model: {response}")
                return None

            # Add assistant response to history
            if message_history:
                message_history.append({"role": "assistant", "content": response})

            return response

        except Exception as e:
            print(f"Error invoking model: {e}")
            return None

    def _extract_tags(self, question: str) -> List[str]:
        """Extract tags from question for categorization"""
        tags = []
        keywords = {
            "implementation": ["how", "build", "create", "develop"],
            "explanation": ["what", "explain", "describe", "why"],
            "troubleshooting": ["error", "bug", "fix", "issue", "problem"],
            "design": ["architecture", "design", "pattern", "structure"]
        }

        question_lower = question.lower()
        for category, words in keywords.items():
            if any(word in question_lower for word in words):
                tags.append(category)

        return tags[:3]  # Limit to 3 tags

    def get_optimization_stats(self) -> Dict:
        """Get statistics about all optimization systems"""
        return {
            "vector_store": self.vector_store_manager.get_cache_stats(),
            "prompt_cache": self.prompt_cache.get_cache_stats(),
            "memory_store": self.memory_store.get_memory_stats()
        }

    def clear_all_caches(self):
        """Clear all caches and memory"""
        self.vector_store_manager.clear_cache()
        self.prompt_cache.clear_cache()
        self.memory_store.cleanup_old_contexts(days=0)
        print("[OK] All caches cleared")

    def answer_with_optimization_stream(self, model_id: str, user_question: str,
                                        embed_model_id: str, message_history: List[Dict] = None,
                                        temperature: float = 0.7, top_p: float = 0.9,
                                        use_cache: bool = True, store_memory: bool = True,
                                        retrieve_past_contexts: bool = True):
        """Answer question with full optimization and stream tokens in real-time.

        Yields tuples of (token, stats_dict) where token is a text chunk
        and stats_dict contains optimization metadata.
        """
        stats = {
            "cache_hit": False,
            "memory_reused": False,
            "contexts_retrieved": 0,
            "tokens_saved": 0,
            "optimization_source": [],
            "streaming": True
        }

        # Check cache first
        if use_cache:
            cached_response = self.prompt_cache.get_cached_response(user_question)
            if cached_response:
                print(f"[CACHE] Cache hit! (saved {cached_response['tokens_saved']} tokens)")
                stats["cache_hit"] = True
                stats["tokens_saved"] = cached_response['tokens_saved']
                stats["optimization_source"].append("prompt_cache")
                # Yield cached response character by character to preserve formatting
                for char in cached_response['response']:
                    yield char, stats.copy()
                return

        # Retrieve past contexts
        past_contexts = []
        if retrieve_past_contexts:
            past_contexts = self.memory_store.retrieve_similar_contexts(user_question, limit=3)
            if past_contexts:
                print(f"[MEM] Found {len(past_contexts)} similar contexts from memory")
                stats["memory_reused"] = True
                stats["optimization_source"].append("context_memory")
                
                # If we have an exact match from memory, return it directly with formatting preserved
                for past_ctx in past_contexts:
                    if past_ctx.query.strip().lower() == user_question.strip().lower():
                        print(f"[MEM] Exact match found! Returning cached response with formatting")
                        # Yield the cached response character by character to preserve formatting
                        for char in past_ctx.response:
                            yield char, stats.copy()
                        return

        # Retrieve from vector store
        retrieved_results = self.vector_store_manager.semantic_search(
            user_question, embed_model_id, top_k=3
        )
        stats["contexts_retrieved"] = len(retrieved_results)
        print(f"[SEARCH] Retrieved {len(retrieved_results)} relevant documents")

        # Build combined context
        context_parts = []
        for past_ctx in past_contexts:
            context_parts.append(f"[Memory - Confidence: {past_ctx.confidence_score:.2%}]")
            context_parts.append(past_ctx.response)
            context_parts.append("")

        for filename, score, content in retrieved_results:
            context_parts.append(f"[Document: {filename}]")
            context_parts.append(content)
            context_parts.append("")

        combined_context = "\n".join(context_parts)

        # Cache context chunks
        for filename, score, content in retrieved_results:
            self.prompt_cache.cache_context_chunk(
                content,
                {"source": filename, "score": score}
            )

        # Stream response from model
        full_response = ""
        for token in self._invoke_model_with_context_stream(
            model_id, user_question, combined_context, message_history,
            temperature, top_p
        ):
            full_response += token
            yield token, stats.copy()

        # Cache the response for future use
        if use_cache:
            estimated_tokens_saved = len(combined_context.split()) // 4
            self.prompt_cache.cache_response(
                user_question, combined_context, full_response, model_id,
                tokens_saved=estimated_tokens_saved
            )
            stats["tokens_saved"] = estimated_tokens_saved
            stats["optimization_source"].append("newly_cached")

        # Store in memory
        if store_memory:
            confidence_score = 0.85 if len(retrieved_results) > 0 else 0.5
            tags = self._extract_tags(user_question)

            context_id = self.memory_store.store_context(
                query=user_question,
                context=combined_context,
                response=full_response,
                metadata={
                    "source": "optimized_rag_stream",
                    "retrieved_docs": len(retrieved_results),
                    "past_contexts_used": len(past_contexts)
                },
                tags=tags,
                confidence_score=confidence_score,
                model_id=model_id
            )
            print(f"[SAVED] Stored in memory (ID: {context_id})")
            stats["optimization_source"].append("memory_stored")

    def _invoke_model_with_context_stream(self, model_id: str, user_question: str,
                                         context: str, message_history: List[Dict] = None,
                                         temperature: float = 0.7, top_p: float = 0.9):
        """Stream response tokens from OpenRouter model with context.

        Yields:
            Text tokens from the model response
        """
        system_prompt = load_system_prompt()

        if message_history is None:
            message_history = []

        try:
            # Build OpenAI-format messages with system prompt
            messages = []

            # Add system prompt as first message with system role
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            # Add message history if present
            if message_history:
                messages.extend(message_history)

            # Add user question with context
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion:\n{user_question}"
            })

            # Use streaming invoke
            for token in invoke_model_stream(model_id, messages, temperature, top_p, character_stream=True):
                yield token

        except Exception as e:
            print(f"Error streaming from model: {e}")
            yield f"Error: {str(e)}"

