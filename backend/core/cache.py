"""
Redis caching utilities for face embeddings and frequently accessed data.
"""

import json
import pickle
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import numpy as np
import redis.asyncio as redis

from .encryption import get_face_embedding_storage

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis caching operations."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.face_storage = get_face_embedding_storage()
        
        # Cache key prefixes
        self.EMBEDDING_PREFIX = "embedding:"
        self.STUDENT_PREFIX = "student:"
        self.SESSION_PREFIX = "session:"
        self.DETECTION_PREFIX = "detection:"
        self.EMOTION_PREFIX = "emotion:"
        
        # Default TTL values (in seconds)
        self.DEFAULT_TTL = 3600  # 1 hour
        self.EMBEDDING_TTL = 7200  # 2 hours
        self.SESSION_TTL = 86400  # 24 hours
    
    async def set_data(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Set data in cache with optional TTL."""
        try:
            if ttl is None:
                ttl = self.DEFAULT_TTL
            
            # Serialize data based on type
            if isinstance(data, (dict, list)):
                serialized_data = json.dumps(data, default=str)
            elif isinstance(data, np.ndarray):
                serialized_data = pickle.dumps(data)
            else:
                serialized_data = str(data)
            
            await self.redis_client.setex(key, ttl, serialized_data)
            logger.debug(f"Data cached: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache data for key {key}: {e}")
            return False
    
    async def get_data(self, key: str, data_type: str = "json") -> Optional[Any]:
        """Get data from cache."""
        try:
            cached_data = await self.redis_client.get(key)
            if cached_data is None:
                return None
            
            # Deserialize based on type
            if data_type == "json":
                return json.loads(cached_data)
            elif data_type == "pickle":
                return pickle.loads(cached_data)
            elif data_type == "numpy":
                return pickle.loads(cached_data)
            else:
                return cached_data.decode('utf-8') if isinstance(cached_data, bytes) else cached_data
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached data for key {key}: {e}")
            return None
    
    async def delete_data(self, key: str) -> bool:
        """Delete data from cache."""
        try:
            result = await self.redis_client.delete(key)
            logger.debug(f"Cache key deleted: {key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check cache key existence {key}: {e}")
            return False
    
    async def set_ttl(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key."""
        try:
            result = await self.redis_client.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"Failed to set TTL for key {key}: {e}")
            return False
    
    # Face embedding specific methods
    async def cache_student_embedding(self, student_id: str, embedding: np.ndarray) -> bool:
        """Cache student face embedding."""
        key = f"{self.EMBEDDING_PREFIX}{student_id}"
        return await self.set_data(key, embedding, self.EMBEDDING_TTL)
    
    async def get_student_embedding(self, student_id: str) -> Optional[np.ndarray]:
        """Get cached student face embedding."""
        key = f"{self.EMBEDDING_PREFIX}{student_id}"
        return await self.get_data(key, "numpy")
    
    async def cache_student_data(self, student_id: str, student_data: Dict[str, Any]) -> bool:
        """Cache student information."""
        key = f"{self.STUDENT_PREFIX}{student_id}"
        return await self.set_data(key, student_data, self.SESSION_TTL)
    
    async def get_student_data(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Get cached student information."""
        key = f"{self.STUDENT_PREFIX}{student_id}"
        return await self.get_data(key, "json")
    
    # Session specific methods
    async def cache_session_data(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Cache attendance session data."""
        key = f"{self.SESSION_PREFIX}{session_id}"
        return await self.set_data(key, session_data, self.SESSION_TTL)
    
    async def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached session data."""
        key = f"{self.SESSION_PREFIX}{session_id}"
        return await self.get_data(key, "json")
    
    async def cache_active_sessions(self, sessions: List[Dict[str, Any]]) -> bool:
        """Cache list of active sessions."""
        key = "active_sessions"
        return await self.set_data(key, sessions, 300)  # 5 minutes TTL
    
    async def get_active_sessions(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached active sessions."""
        key = "active_sessions"
        return await self.get_data(key, "json")
    
    # Detection and emotion caching
    async def cache_recent_detections(self, camera_location: str, detections: List[Dict[str, Any]]) -> bool:
        """Cache recent face detections for a camera."""
        key = f"{self.DETECTION_PREFIX}{camera_location}"
        return await self.set_data(key, detections, 600)  # 10 minutes TTL
    
    async def get_recent_detections(self, camera_location: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached recent detections."""
        key = f"{self.DETECTION_PREFIX}{camera_location}"
        return await self.get_data(key, "json")
    
    async def cache_emotion_stats(self, session_id: str, emotion_stats: Dict[str, Any]) -> bool:
        """Cache emotion statistics for a session."""
        key = f"{self.EMOTION_PREFIX}{session_id}"
        return await self.set_data(key, emotion_stats, 1800)  # 30 minutes TTL
    
    async def get_emotion_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached emotion statistics."""
        key = f"{self.EMOTION_PREFIX}{session_id}"
        return await self.get_data(key, "json")
    
    # Bulk operations
    async def cache_multiple_embeddings(self, embeddings_data: Dict[str, np.ndarray]) -> int:
        """Cache multiple student embeddings."""
        success_count = 0
        for student_id, embedding in embeddings_data.items():
            if await self.cache_student_embedding(student_id, embedding):
                success_count += 1
        
        logger.info(f"Cached {success_count}/{len(embeddings_data)} embeddings")
        return success_count
    
    async def get_multiple_embeddings(self, student_ids: List[str]) -> Dict[str, Optional[np.ndarray]]:
        """Get multiple student embeddings."""
        embeddings = {}
        for student_id in student_ids:
            embeddings[student_id] = await self.get_student_embedding(student_id)
        
        return embeddings
    
    async def invalidate_student_cache(self, student_id: str) -> bool:
        """Invalidate all cached data for a student."""
        keys_to_delete = [
            f"{self.EMBEDDING_PREFIX}{student_id}",
            f"{self.STUDENT_PREFIX}{student_id}"
        ]
        
        success_count = 0
        for key in keys_to_delete:
            if await self.delete_data(key):
                success_count += 1
        
        logger.info(f"Invalidated {success_count}/{len(keys_to_delete)} cache keys for student {student_id}")
        return success_count == len(keys_to_delete)
    
    async def invalidate_session_cache(self, session_id: str) -> bool:
        """Invalidate all cached data for a session."""
        keys_to_delete = [
            f"{self.SESSION_PREFIX}{session_id}",
            f"{self.EMOTION_PREFIX}{session_id}"
        ]
        
        success_count = 0
        for key in keys_to_delete:
            if await self.delete_data(key):
                success_count += 1
        
        logger.info(f"Invalidated {success_count}/{len(keys_to_delete)} cache keys for session {session_id}")
        return success_count == len(keys_to_delete)
    
    # Health and monitoring
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        try:
            info = await self.redis_client.info()
            stats = {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'uptime_in_seconds': info.get('uptime_in_seconds', 0)
            }
            
            # Calculate hit rate
            hits = stats['keyspace_hits']
            misses = stats['keyspace_misses']
            total_requests = hits + misses
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
            stats['hit_rate_percentage'] = round(hit_rate, 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    async def clear_all_cache(self) -> bool:
        """Clear all cached data (use with caution!)."""
        try:
            await self.redis_client.flushdb()
            logger.warning("All cache data cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False


class EmbeddingMatcher:
    """Handles face embedding matching with caching."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.face_storage = get_face_embedding_storage()
        self.similarity_threshold = 0.8  # Configurable threshold
    
    async def find_best_match(self, query_embedding: np.ndarray, student_ids: List[str]) -> Optional[Dict[str, Any]]:
        """Find best matching student for a query embedding."""
        try:
            best_match = None
            best_similarity = 0.0
            
            # Get cached embeddings for all students
            cached_embeddings = await self.cache_manager.get_multiple_embeddings(student_ids)
            
            for student_id, cached_embedding in cached_embeddings.items():
                if cached_embedding is None:
                    continue
                
                # Calculate similarity
                similarity = self.face_storage.compare_embeddings(query_embedding, cached_embedding)
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = {
                        'student_id': student_id,
                        'similarity': similarity,
                        'confidence': similarity
                    }
            
            if best_match:
                logger.debug(f"Best match found: {best_match['student_id']} (similarity: {best_similarity:.4f})")
            else:
                logger.debug("No match found above threshold")
            
            return best_match
            
        except Exception as e:
            logger.error(f"Face matching failed: {e}")
            return None
    
    async def batch_match_embeddings(self, query_embeddings: List[np.ndarray], student_ids: List[str]) -> List[Optional[Dict[str, Any]]]:
        """Match multiple embeddings in batch."""
        matches = []
        for embedding in query_embeddings:
            match = await self.find_best_match(embedding, student_ids)
            matches.append(match)
        
        return matches
    
    def set_similarity_threshold(self, threshold: float):
        """Set similarity threshold for matching."""
        if 0.0 <= threshold <= 1.0:
            self.similarity_threshold = threshold
            logger.info(f"Similarity threshold set to: {threshold}")
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")


# Global cache manager instance
_cache_manager = None
_embedding_matcher = None
_redis_client = None


async def get_redis_client() -> redis.Redis:
    """Get global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        import os
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        
        _redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False
        )
        logger.info(f"Redis client connected to {redis_host}:{redis_port}")
    
    return _redis_client


async def get_cache_manager(redis_client: redis.Redis = None) -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        if redis_client is None:
            redis_client = await get_redis_client()
        _cache_manager = CacheManager(redis_client)
    return _cache_manager


async def get_embedding_matcher(redis_client: redis.Redis = None) -> EmbeddingMatcher:
    """Get global embedding matcher instance."""
    global _embedding_matcher
    if _embedding_matcher is None:
        if redis_client is None:
            redis_client = await get_redis_client()
        cache_manager = await get_cache_manager(redis_client)
        _embedding_matcher = EmbeddingMatcher(cache_manager)
    return _embedding_matcher