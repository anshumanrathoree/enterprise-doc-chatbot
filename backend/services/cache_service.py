import hashlib
import json
import time
from typing import Any, Optional, Dict, List
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    ttl: float
    hit_count: int = 0

class HighPerformanceCache:
    def __init__(self, max_size: int = 10000, default_ttl: float = 3600):
        """
        High-performance in-memory cache with LRU eviction and TTL

        Args:
            max_size: Maximum number of entries to store
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # LRU tracking
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'sets': 0
        }

    def _generate_key(self, query: str, context_hash: str = "") -> str:
        """Generate a consistent cache key from query and context"""
        combined = f"{query.lower().strip()}:{context_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry has expired"""
        return time.time() - entry.timestamp > entry.ttl

    def _evict_lru(self):
        """Evict least recently used entry"""
        if self.access_order:
            lru_key = self.access_order.pop(0)
            if lru_key in self.cache:
                del self.cache[lru_key]
                self.stats['evictions'] += 1

    def _update_access_order(self, key: str):
        """Update LRU access order"""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    def get(self, query: str, context_chunks: List[Any] = None) -> Optional[Any]:
        """
        Retrieve cached response for query + context combination

        Args:
            query: The user query
            context_chunks: List of document chunks (for context hashing)

        Returns:
            Cached response or None if not found/expired
        """
        try:
            # Generate context hash for cache key
            context_hash = ""
            if context_chunks:
                chunk_ids = sorted([
                    f"{chunk.metadata.get('document_id', '')}:{chunk.metadata.get('chunk_index', 0)}"
                    for chunk in context_chunks
                ])
                context_hash = hashlib.sha256(''.join(chunk_ids).encode()).hexdigest()[:8]

            cache_key = self._generate_key(query, context_hash)

            if cache_key not in self.cache:
                self.stats['misses'] += 1
                return None

            entry = self.cache[cache_key]

            # Check expiration
            if self._is_expired(entry):
                del self.cache[cache_key]
                if cache_key in self.access_order:
                    self.access_order.remove(cache_key)
                self.stats['misses'] += 1
                return None

            # Update stats and access order
            entry.hit_count += 1
            self.stats['hits'] += 1
            self._update_access_order(cache_key)

            logger.debug(f"Cache HIT for query: {query[:50]}...")
            return entry.value

        except Exception as e:
            logger.error(f"Cache retrieval error: {str(e)}")
            self.stats['misses'] += 1
            return None

    def set(self, query: str, response: Any, context_chunks: List[Any] = None, ttl: Optional[float] = None) -> bool:
        """
        Cache a response for query + context combination

        Args:
            query: The user query
            response: The response to cache
            context_chunks: List of document chunks (for context hashing)
            ttl: Time-to-live override

        Returns:
            True if successfully cached
        """
        try:
            # Generate context hash for cache key
            context_hash = ""
            if context_chunks:
                chunk_ids = sorted([
                    f"{chunk.metadata.get('document_id', '')}:{chunk.metadata.get('chunk_index', 0)}"
                    for chunk in context_chunks
                ])
                context_hash = hashlib.sha256(''.join(chunk_ids).encode()).hexdigest()[:8]

            cache_key = self._generate_key(query, context_hash)

            # Evict if at capacity
            if len(self.cache) >= self.max_size and cache_key not in self.cache:
                self._evict_lru()

            # Create cache entry
            entry = CacheEntry(
                value=response,
                timestamp=time.time(),
                ttl=ttl or self.default_ttl
            )

            self.cache[cache_key] = entry
            self._update_access_order(cache_key)
            self.stats['sets'] += 1

            logger.debug(f"Cache SET for query: {query[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Cache storage error: {str(e)}")
            return False

    def invalidate_document(self, document_id: str):
        """Invalidate all cache entries that might contain content from a document"""
        try:
            keys_to_remove = []
            for key, entry in self.cache.items():
                # Check if cached response contains references to this document
                if hasattr(entry.value, 'sources') and entry.value.sources:
                    for source in entry.value.sources:
                        if source.metadata.get('document_id') == document_id:
                            keys_to_remove.append(key)
                            break

            for key in keys_to_remove:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)

            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for document {document_id}")

        except Exception as e:
            logger.error(f"Cache invalidation error: {str(e)}")

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.access_order.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_rate_percent': round(hit_rate, 2),
            'total_hits': self.stats['hits'],
            'total_misses': self.stats['misses'],
            'total_sets': self.stats['sets'],
            'total_evictions': self.stats['evictions'],
            'memory_efficiency': f"{len(self.cache)}/{self.max_size} ({len(self.cache)/self.max_size*100:.1f}%)"
        }

# Global cache instance
cache_service = HighPerformanceCache(max_size=5000, default_ttl=1800)  # 30 minutes TTL