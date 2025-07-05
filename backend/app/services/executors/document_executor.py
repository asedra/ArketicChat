"""
Document Function Executor for knowledge base and document search
Supports semantic search, document chunking, and content retrieval
"""
import asyncio
import json
import time
import hashlib
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import numpy as np
from openai import AsyncOpenAI

from ...core.config import settings
from ...models.function import Function


@dataclass
class DocumentChunk:
    """Document chunk with metadata"""
    content: str
    chunk_id: str
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class DocumentExecutor:
    """
    Document function executor with semantic search and processing
    """
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.document_cache = {}
        self.embedding_cache = {}
        
    async def execute(self, function: Function, parameters: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a document function with search and processing
        
        Args:
            function: Function object with document configuration
            parameters: Function parameters (query, etc.)
            context: Execution context
            
        Returns:
            Dict containing search results and metadata
        """
        if not function.document_content:
            raise ValueError("Document content is required for document functions")
        
        start_time = time.time()
        
        try:
            # Get document configuration
            doc_config = self._get_document_config(function)
            
            # Process document content if not cached
            document_id = self._get_document_id(function)
            if document_id not in self.document_cache:
                chunks = await self._process_document(function.document_content, doc_config)
                self.document_cache[document_id] = chunks
            else:
                chunks = self.document_cache[document_id]
            
            # Extract search query from parameters
            query = parameters.get('query', parameters.get('search', parameters.get('q', '')))
            if not query:
                raise ValueError("Search query is required (use 'query', 'search', or 'q' parameter)")
            
            # Perform search
            search_results = await self._search_documents(query, chunks, doc_config)
            
            # Format results
            formatted_results = self._format_search_results(search_results, doc_config)
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "result": formatted_results,
                "metadata": {
                    "execution_time": execution_time,
                    "query": query,
                    "total_chunks": len(chunks),
                    "results_count": len(search_results),
                    "search_method": doc_config.get("search_config", {}).get("method", "semantic"),
                    "document_id": document_id
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "execution_time": execution_time,
                    "query": parameters.get('query', 'unknown')
                }
            }
    
    def _get_document_config(self, function: Function) -> Dict[str, Any]:
        """Extract document configuration from function"""
        
        # Default configuration
        config = {
            "processing_config": {
                "chunk_size": settings.DOCUMENT_CHUNK_SIZE,
                "overlap": settings.DOCUMENT_OVERLAP,
                "format": "markdown"
            },
            "search_config": {
                "method": "semantic",
                "embedding_model": settings.EMBEDDING_MODEL,
                "similarity_threshold": 0.8,
                "max_results": 5
            },
            "indexing": {
                "enabled": True,
                "update_frequency": "realtime"
            }
        }
        
        # Override with function-specific config from extra_data
        if function.extra_data:
            doc_config = function.extra_data.get("document_config", {})
            if doc_config:
                config.update(doc_config)
        
        return config
    
    def _get_document_id(self, function: Function) -> str:
        """Generate unique document ID for caching"""
        content_hash = hashlib.md5(function.document_content.encode()).hexdigest()
        return f"{function.id}_{content_hash[:8]}"
    
    async def _process_document(self, content: str, config: Dict[str, Any]) -> List[DocumentChunk]:
        """Process document into searchable chunks"""
        
        processing_config = config.get("processing_config", {})
        chunk_size = processing_config.get("chunk_size", 1000)
        overlap = processing_config.get("overlap", 200)
        format_type = processing_config.get("format", "markdown")
        
        # Clean and prepare content
        cleaned_content = self._clean_content(content, format_type)
        
        # Create chunks with overlap
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(cleaned_content):
            end = min(start + chunk_size, len(cleaned_content))
            
            # Adjust end to sentence boundary if possible
            if end < len(cleaned_content):
                # Look for sentence endings
                sentence_end = cleaned_content.rfind('.', start, end)
                if sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
            
            chunk_content = cleaned_content[start:end].strip()
            
            if chunk_content:
                chunk = DocumentChunk(
                    content=chunk_content,
                    chunk_id=f"chunk_{chunk_id}",
                    start_pos=start,
                    end_pos=end,
                    metadata={
                        "length": len(chunk_content),
                        "position": chunk_id,
                        "format": format_type
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
            
            # Move start position with overlap
            start = max(start + chunk_size - overlap, end)
        
        # Generate embeddings for semantic search
        search_config = config.get("search_config", {})
        if search_config.get("method") == "semantic":
            await self._generate_embeddings(chunks, search_config)
        
        return chunks
    
    def _clean_content(self, content: str, format_type: str) -> str:
        """Clean and prepare content for processing"""
        
        if format_type == "markdown":
            # Remove markdown formatting but keep structure
            # Remove headers but keep content
            content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
            # Remove emphasis markers
            content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
            content = re.sub(r'\*(.*?)\*', r'\1', content)
            # Remove links but keep text
            content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
            # Remove code blocks
            content = re.sub(r'```[^`]*```', '', content, flags=re.DOTALL)
            content = re.sub(r'`([^`]+)`', r'\1', content)
        
        # General cleaning
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove excessive newlines
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        return content.strip()
    
    async def _generate_embeddings(self, chunks: List[DocumentChunk], search_config: Dict[str, Any]):
        """Generate embeddings for document chunks"""
        
        embedding_model = search_config.get("embedding_model", "text-embedding-ada-002")
        
        try:
            # Prepare texts for embedding
            texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings in batches
            batch_size = 20
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                
                response = await self.openai_client.embeddings.create(
                    model=embedding_model,
                    input=batch_texts
                )
                
                # Store embeddings in chunks
                for j, embedding_data in enumerate(response.data):
                    chunk_index = i + j
                    if chunk_index < len(chunks):
                        chunks[chunk_index].embedding = embedding_data.embedding
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"Warning: Failed to generate embeddings: {e}")
            # Continue without embeddings (will fall back to keyword search)
    
    async def _search_documents(self, query: str, chunks: List[DocumentChunk], config: Dict[str, Any]) -> List[Tuple[DocumentChunk, float]]:
        """Search documents using configured method"""
        
        search_config = config.get("search_config", {})
        method = search_config.get("method", "semantic")
        max_results = search_config.get("max_results", 5)
        
        if method == "semantic" and any(chunk.embedding for chunk in chunks):
            results = await self._semantic_search(query, chunks, search_config)
        else:
            results = self._keyword_search(query, chunks, search_config)
        
        # Sort by relevance score and limit results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:max_results]
    
    async def _semantic_search(self, query: str, chunks: List[DocumentChunk], search_config: Dict[str, Any]) -> List[Tuple[DocumentChunk, float]]:
        """Perform semantic search using embeddings"""
        
        try:
            # Generate embedding for query
            embedding_model = search_config.get("embedding_model", "text-embedding-ada-002")
            
            response = await self.openai_client.embeddings.create(
                model=embedding_model,
                input=[query]
            )
            
            query_embedding = response.data[0].embedding
            
            # Calculate similarity scores
            results = []
            threshold = search_config.get("similarity_threshold", 0.8)
            
            for chunk in chunks:
                if chunk.embedding:
                    similarity = self._cosine_similarity(query_embedding, chunk.embedding)
                    if similarity >= threshold:
                        results.append((chunk, similarity))
            
            return results
            
        except Exception as e:
            print(f"Semantic search failed, falling back to keyword search: {e}")
            return self._keyword_search(query, chunks, search_config)
    
    def _keyword_search(self, query: str, chunks: List[DocumentChunk], search_config: Dict[str, Any]) -> List[Tuple[DocumentChunk, float]]:
        """Perform keyword-based search"""
        
        # Normalize query
        query_words = set(query.lower().split())
        
        results = []
        
        for chunk in chunks:
            # Calculate simple keyword match score
            chunk_words = set(chunk.content.lower().split())
            
            # Calculate overlap
            common_words = query_words.intersection(chunk_words)
            if common_words:
                # Simple scoring: ratio of matching words
                score = len(common_words) / len(query_words)
                
                # Boost score for exact phrase matches
                if query.lower() in chunk.content.lower():
                    score += 0.5
                
                results.append((chunk, min(score, 1.0)))
        
        return results
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            a = np.array(vec1)
            b = np.array(vec2)
            
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return dot_product / (norm_a * norm_b)
        except Exception:
            return 0.0
    
    def _format_search_results(self, results: List[Tuple[DocumentChunk, float]], config: Dict[str, Any]) -> Dict[str, Any]:
        """Format search results for response"""
        
        formatted_results = []
        
        for chunk, score in results:
            result_item = {
                "content": chunk.content,
                "relevance_score": round(score, 3),
                "chunk_id": chunk.chunk_id,
                "metadata": chunk.metadata.copy()
            }
            
            # Add position information
            result_item["metadata"]["score"] = score
            result_item["metadata"]["chunk_position"] = chunk.metadata.get("position", 0)
            
            formatted_results.append(result_item)
        
        return {
            "results": formatted_results,
            "total_found": len(formatted_results),
            "search_summary": {
                "method": config.get("search_config", {}).get("method", "semantic"),
                "threshold": config.get("search_config", {}).get("similarity_threshold", 0.8),
                "max_results": config.get("search_config", {}).get("max_results", 5)
            }
        }
    
    async def close(self):
        """Close OpenAI client and clear caches"""
        if self.openai_client:
            await self.openai_client.close()
        
        self.document_cache.clear()
        self.embedding_cache.clear()


# Example document configurations
EXAMPLE_DOCUMENT_CONFIGS = {
    "technical_docs": {
        "processing_config": {
            "chunk_size": 1500,
            "overlap": 300,
            "format": "markdown"
        },
        "search_config": {
            "method": "semantic",
            "embedding_model": "text-embedding-ada-002",
            "similarity_threshold": 0.75,
            "max_results": 8
        }
    },
    
    "knowledge_base": {
        "processing_config": {
            "chunk_size": 800,
            "overlap": 150,
            "format": "text"
        },
        "search_config": {
            "method": "hybrid",
            "embedding_model": "text-embedding-ada-002",
            "similarity_threshold": 0.8,
            "max_results": 5
        }
    },
    
    "code_documentation": {
        "processing_config": {
            "chunk_size": 2000,
            "overlap": 400,
            "format": "markdown"
        },
        "search_config": {
            "method": "semantic",
            "embedding_model": "text-embedding-ada-002",
            "similarity_threshold": 0.7,
            "max_results": 10
        }
    }
}