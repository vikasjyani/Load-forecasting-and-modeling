# utils/cache_manager.py
"""
Advanced caching system with Redis fallback and intelligent cache management
"""
import redis
import json
import hashlib
import pickle
import time
import logging
from functools import wraps
from typing import Any, Optional, Callable, Dict, Union
from collections import OrderedDict
import threading
import psutil

logger = logging.getLogger(__name__)

class TTLCache:
    """Thread-safe TTL cache implementation"""
    
    def __init__(self, maxsize: int = 1000, default_ttl: int = 300):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                # Move to end (LRU)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            elif key in self.cache:
                # Expired, remove
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self.lock:
            if len(self.cache) >= self.maxsize:
                # Remove oldest
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

class CacheManager:
    """
    Multi-tier caching system with Redis primary and memory fallback
    """
    
    def __init__(self, redis_url: str = None, memory_cache_size: int = 1000):
        self.redis_client = None
        self.memory_cache = TTLCache(maxsize=memory_cache_size)
        self.hit_stats = {'redis': 0, 'memory': 0, 'miss': 0}
        self.lock = threading.RLock()
        
        # Try to connect to Redis
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, falling back to memory cache: {e}")
                self.redis_client = None
        
        # Monitor memory usage
        self.memory_threshold = 0.8  # 80% of available memory
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate deterministic cache key"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage"""
        try:
            # Try JSON first (faster)
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            # Fall back to pickle
            return pickle.dumps(value).hex()
    
    def _deserialize_value(self, serialized: str) -> Any:
        """Deserialize value from storage"""
        try:
            # Try JSON first
            return json.loads(serialized)
        except (json.JSONDecodeError, ValueError):
            # Fall back to pickle
            try:
                return pickle.loads(bytes.fromhex(serialized))
            except Exception:
                return None
    
    def _check_memory_pressure(self) -> bool:
        """Check if system is under memory pressure"""
        try:
            memory = psutil.virtual_memory()
            return memory.percent > (self.memory_threshold * 100)
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis first, then memory)"""
        with self.lock:
            # Try Redis first
            if self.redis_client:
                try:
                    value = self.redis_client.get(key)
                    if value is not None:
                        self.hit_stats['redis'] += 1
                        return self._deserialize_value(value)
                except Exception as e:
                    logger.warning(f"Redis get failed: {e}")
            
            # Try memory cache
            value = self.memory_cache.get(key)
            if value is not None:
                self.hit_stats['memory'] += 1
                return value
            
            self.hit_stats['miss'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache"""
        with self.lock:
            serialized = self._serialize_value(value)
            
            # Try Redis first
            if self.redis_client:
                try:
                    self.redis_client.setex(key, ttl, serialized)
                    return True
                except Exception as e:
                    logger.warning(f"Redis set failed: {e}")
            
            # Fall back to memory cache if not under pressure
            if not self._check_memory_pressure():
                self.memory_cache.set(key, value, ttl)
                return True
            
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            success = False
            
            # Delete from Redis
            if self.redis_client:
                try:
                    self.redis_client.delete(key)
                    success = True
                except Exception as e:
                    logger.warning(f"Redis delete failed: {e}")
            
            # Delete from memory cache
            if key in self.memory_cache.cache:
                del self.memory_cache.cache[key]
                if key in self.memory_cache.timestamps:
                    del self.memory_cache.timestamps[key]
                success = True
            
            return success
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            # Clear Redis
            if self.redis_client:
                try:
                    self.redis_client.flushdb()
                except Exception as e:
                    logger.warning(f"Redis clear failed: {e}")
            
            # Clear memory cache
            self.memory_cache.clear()
            
            # Reset stats
            self.hit_stats = {'redis': 0, 'memory': 0, 'miss': 0}
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        count = 0
        
        # Clear from Redis
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    count += self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis pattern clear failed: {e}")
        
        # Clear from memory cache
        with self.lock:
            keys_to_delete = []
            for key in self.memory_cache.cache.keys():
                if pattern.replace('*', '') in key:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self.memory_cache.cache[key]
                if key in self.memory_cache.timestamps:
                    del self.memory_cache.timestamps[key]
                count += 1
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_hits = sum(self.hit_stats.values()) - self.hit_stats['miss']
        total_requests = sum(self.hit_stats.values())
        
        stats = {
            'hit_stats': self.hit_stats.copy(),
            'hit_rate': total_hits / total_requests if total_requests > 0 else 0,
            'memory_cache_size': len(self.memory_cache.cache),
            'memory_cache_maxsize': self.memory_cache.maxsize,
            'redis_connected': self.redis_client is not None
        }
        
        # Add Redis stats if available
        if self.redis_client:
            try:
                info = self.redis_client.info('memory')
                stats['redis_memory_usage'] = info.get('used_memory_human', 'Unknown')
                stats['redis_keys'] = self.redis_client.dbsize()
            except Exception:
                pass
        
        return stats

def cached(prefix: str = "default", ttl: int = 300, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        key_func: Custom function to generate cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_manager._generate_key(f"{prefix}:{func.__name__}", *args, **kwargs)
            
            # Try to get from cache
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        # Add cache control methods to function
        wrapper.cache_clear = lambda: cache_manager.clear_pattern(f"{prefix}:{func.__name__}*")
        wrapper.cache_info = lambda: cache_manager.get_stats()
        
        return wrapper
    return decorator

# Global cache manager instance
cache_manager = CacheManager()