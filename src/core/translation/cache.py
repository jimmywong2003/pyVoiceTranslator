"""
Translation Cache Module

Provides caching for translations to improve performance and reduce API calls.
"""

import hashlib
import json
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from .base import TranslationResult

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry for a translation."""
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    timestamp: float
    hit_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "timestamp": self.timestamp,
            "hit_count": self.hit_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        """Create from dictionary."""
        return cls(**data)


class TranslationCache:
    """
    LRU cache for translations with persistence support.
    
    Features:
    - In-memory caching for fast lookups
    - Persistent disk cache
    - TTL (Time To Live) support
    - Cache statistics
    
    Usage:
        cache = TranslationCache(max_size=1000, ttl=3600)
        
        # Check cache
        result = cache.get("hello", "en", "zh")
        if result:
            print(f"Cached: {result.translated_text}")
        else:
            # Translate and cache
            result = translator.translate("hello", "en", "zh")
            cache.put(result)
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl: Optional[int] = 3600,  # 1 hour default
        cache_dir: Optional[str] = None
    ):
        """
        Initialize translation cache.
        
        Args:
            max_size: Maximum number of entries in cache
            ttl: Time to live in seconds (None for no expiry)
            cache_dir: Directory for persistent cache (None for memory-only)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache_dir = Path(cache_dir) if cache_dir else None
        
        # In-memory cache: {(source, src_lang, tgt_lang): CacheEntry}
        self._cache: Dict[Tuple[str, str, str], CacheEntry] = {}
        self._access_order: list = []  # For LRU eviction
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._puts = 0
        
        # Load persistent cache if available
        if self.cache_dir:
            self._load_cache()
        
        logger.info(f"TranslationCache initialized: max_size={max_size}, ttl={ttl}")
    
    def _generate_key(self, source_text: str, source_lang: str, target_lang: str) -> Tuple[str, str, str]:
        """Generate cache key from translation parameters."""
        # Normalize text for caching
        normalized = source_text.strip().lower()
        return (normalized, source_lang.lower(), target_lang.lower())
    
    def get(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str
    ) -> Optional[TranslationResult]:
        """
        Get cached translation if available.
        
        Args:
            source_text: Source text to translate
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            TranslationResult if found in cache, None otherwise
        """
        key = self._generate_key(source_text, source_lang, target_lang)
        
        if key not in self._cache:
            self._misses += 1
            return None
        
        entry = self._cache[key]
        
        # Check TTL
        if self.ttl is not None:
            age = time.time() - entry.timestamp
            if age > self.ttl:
                logger.debug(f"Cache entry expired: {key[0][:30]}...")
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._misses += 1
                return None
        
        # Update access order (LRU)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        # Update hit count
        entry.hit_count += 1
        self._hits += 1
        
        logger.debug(f"Cache hit: {key[0][:30]}...")
        
        return TranslationResult(
            source_text=entry.source_text,
            translated_text=entry.translated_text,
            source_language=entry.source_lang,
            target_language=entry.target_lang,
            confidence=0.95,  # Cached translations are considered reliable
            processing_time=0.0  # Instant from cache
        )
    
    def put(self, result: TranslationResult) -> None:
        """
        Store translation result in cache.
        
        Args:
            result: TranslationResult to cache
        """
        if not result or not result.translated_text:
            return
        
        key = self._generate_key(
            result.source_text,
            result.source_language,
            result.target_language
        )
        
        # Check if already exists
        if key in self._cache:
            # Update existing entry
            entry = self._cache[key]
            entry.translated_text = result.translated_text
            entry.timestamp = time.time()
        else:
            # Evict if at capacity
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            # Create new entry
            entry = CacheEntry(
                source_text=result.source_text,
                translated_text=result.translated_text,
                source_lang=result.source_language,
                target_lang=result.target_language,
                timestamp=time.time()
            )
            self._cache[key] = entry
            self._puts += 1
        
        # Update access order
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        
        logger.debug(f"Cache put: {key[0][:30]}...")
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry using LRU policy."""
        if not self._access_order:
            return
        
        oldest_key = self._access_order.pop(0)
        if oldest_key in self._cache:
            del self._cache[oldest_key]
            logger.debug(f"Evicted from cache: {oldest_key[0][:30]}...")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._access_order.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "puts": self._puts,
            "hit_rate": f"{hit_rate:.1f}%",
            "ttl": self.ttl
        }
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_dir:
            return
        
        cache_file = self.cache_dir / "translation_cache.json"
        if not cache_file.exists():
            return
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for item in data:
                entry = CacheEntry.from_dict(item)
                key = self._generate_key(
                    entry.source_text,
                    entry.source_lang,
                    entry.target_lang
                )
                self._cache[key] = entry
                self._access_order.append(key)
            
            logger.info(f"Loaded {len(self._cache)} entries from disk cache")
            
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
    
    def save(self) -> None:
        """Save cache to disk."""
        if not self.cache_dir:
            return
        
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / "translation_cache.json"
            
            data = [entry.to_dict() for entry in self._cache.values()]
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(self._cache)} entries to disk cache")
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def __del__(self):
        """Destructor - save cache on exit."""
        self.save()


class CachedTranslator:
    """
    Wrapper for translators that adds caching.
    
    Usage:
        translator = MarianTranslator(source_lang="en", target_lang="zh")
        cached = CachedTranslator(translator, max_cache_size=500)
        
        # First call - translates and caches
        result = cached.translate("Hello", "en", "zh")
        
        # Second call - returns from cache
        result = cached.translate("Hello", "en", "zh")  # Instant
    """
    
    def __init__(self, translator, cache: Optional[TranslationCache] = None):
        """
        Initialize cached translator wrapper.
        
        Args:
            translator: Base translator instance
            cache: TranslationCache instance (creates default if None)
        """
        self.translator = translator
        self.cache = cache or TranslationCache()
    
    def translate(self, text: str, source_lang: str, target_lang: str, **kwargs):
        """
        Translate with caching.
        
        Checks cache first, falls back to translator if not found.
        """
        # Check cache
        cached = self.cache.get(text, source_lang, target_lang)
        if cached:
            return cached
        
        # Translate
        result = self.translator.translate(text, source_lang, target_lang, **kwargs)
        
        # Cache result
        if result:
            self.cache.put(result)
        
        return result
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return self.cache.get_stats()
