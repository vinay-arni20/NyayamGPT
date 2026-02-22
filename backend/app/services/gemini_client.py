"""
NyayamGPT - Gemini Client
=========================
Robust wrapper for Google Gemini API with rate limiting, caching, and retries.
"""

import os
import json
import time
import hashlib
import asyncio
import logging
from typing import Any, Optional, Dict, List

import google.generativeai as genai
from google.api_core import exceptions

from app.core.config import settings
from app.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class FileCache:
    """
    Simple file-based JSON cache for offline capability.
    """
    def __init__(self, cache_dir: str = "data/cache", ttl_seconds: int = 3600):
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.cache_file = os.path.join(cache_dir, "gemini_cache.json")
        
        # Ensure directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        self.cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.cache = {}
        else:
            self.cache = {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if valid."""
        if key in self.cache:
            entry = self.cache[key]
            timestamp = entry.get("timestamp", 0)
            if time.time() - timestamp < self.ttl_seconds:
                return entry.get("data")
            else:
                # Expired
                del self.cache[key]
                # Don't save immediately on read to avoid IO thrashing
        return None

    def set(self, key: str, data: Any):
        """Set item in cache."""
        self.cache[key] = {
            "timestamp": time.time(),
            "data": data
        }
        self._save_cache()


class GeminiClient:
    """
    Wrapper for Gemini API with robust error handling.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.api_keys = settings.all_gemini_keys
        self.current_key_index = 0
        
        self.models = settings.all_gemini_models
        self.current_model_index = 0
        
        # Rate limiters cache
        self.rate_limiters = {}
        self.active_rate_limiter = None
        
        # File cache
        self.cache = FileCache()
        
        # Stats
        self.stats = {
            "requests": 0, 
            "errors": 0, 
            "cache_hits": 0, 
            "retries": 0,
            "key_rotations": 0,
            "model_rotations": 0
        }
        
        self._configure_client()
        self._initialized = True

    def _configure_client(self):
        """Configure the Gemini client with the current key and model."""
        if not self.api_keys:
            raise ValueError("No Gemini API keys configured")
        
        api_key = self.api_keys[self.current_key_index]
        genai.configure(api_key=api_key)
        
        current_model = self.models[self.current_model_index]
        
        # Determine RPM based on model type (Free Tier Limits)
        # gemini-2.5-flash -> 10 RPM (latest, best quality)
        # gemini-2.5-pro -> 5 RPM (highest quality, lower quota)
        # gemini-2.0-flash -> 15 RPM (fast and reliable)
        # gemini-2.0-flash-lite -> 30 RPM (fastest, lowest quality)
        if "2.5-pro" in current_model.lower():
            rpm = 5
        elif "2.5-flash" in current_model.lower():
            rpm = 10
        elif "lite" in current_model.lower():
            rpm = 30
        else:
            rpm = 15  # Default for 2.0-flash models
        
        # Get or create rate limiter for this model
        if current_model not in self.rate_limiters:
            self.rate_limiters[current_model] = RateLimiter(rpm=rpm)
        
        self.active_rate_limiter = self.rate_limiters[current_model]
        
        # Create model instance
        self.model = genai.GenerativeModel(
            model_name=current_model,
            generation_config={
                "temperature": settings.gemini_temperature,
                "max_output_tokens": settings.gemini_max_tokens,
                "top_p": 0.95,
                "top_k": 40,
            }
        )
        logger.info(f"Gemini Client configured with key index: {self.current_key_index}, model: {current_model}, RPM: {rpm}")

    def _rotate_key(self) -> bool:
        """Rotate to the next API key."""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self._configure_client()
            self.stats["key_rotations"] += 1
            logger.warning(f"Rotated to Gemini API Key index: {self.current_key_index}")
            return True
        return False

    def _rotate_model(self) -> bool:
        """Rotate to the next model."""
        if len(self.models) > 1:
            self.current_model_index = (self.current_model_index + 1) % len(self.models)
            self._configure_client()
            self.stats["model_rotations"] += 1
            logger.warning(f"Rotated to Gemini Model: {self.models[self.current_model_index]}")
            return True
        return False

    async def generate_content(self, prompt: str, use_cache: bool = True) -> str:
        """
        Generate content with retries, rate limiting, and caching.
        """
        self.stats["requests"] += 1
        
        # 1. Check Cache
        cache_key = hashlib.sha256(prompt.encode()).hexdigest()
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                self.stats["cache_hits"] += 1
                logger.info("Gemini Cache Hit")
                return cached

        # 2. Retry Loop
        retries = 0
        max_retries = 3
        backoff_delays = [1, 2, 5] # Seconds

        while retries <= max_retries:
            try:
                # 3. Rate Limiting
                if self.active_rate_limiter:
                    await self.active_rate_limiter.wait_for_token()
                
                # 4. API Call
                logger.debug(f"Sending request to Gemini (Attempt {retries+1})")
                response = await self.model.generate_content_async(prompt)
                result = response.text
                
                # 5. Update Cache
                if use_cache and result:
                    self.cache.set(cache_key, result)
                
                return result

            except Exception as e:
                error_msg = str(e)
                is_quota = "429" in error_msg or "quota" in error_msg.lower() or "exhausted" in error_msg.lower()
                is_server_error = "503" in error_msg or "500" in error_msg or "overloaded" in error_msg.lower()
                is_not_found = "404" in error_msg or "not found" in error_msg.lower()
                
                if is_quota:
                    logger.warning(f"Quota exceeded on key {self.current_key_index}: {error_msg}")
                    
                    # Try rotating key first
                    if self._rotate_key():
                        logger.info("Key rotated, retrying immediately...")
                        continue 
                    
                    # If keys exhausted, try rotating model (different models might have different quotas)
                    if self._rotate_model():
                        logger.info("Model rotated, retrying immediately...")
                        continue

                    # If rotation failed (only 1 key/model) or exhausted, backoff
                    if retries < max_retries:
                        delay = backoff_delays[retries]
                        logger.warning(f"Rate limit hit & no keys/models left. Sleeping {delay}s...")
                        self.stats["retries"] += 1
                        await asyncio.sleep(delay)
                        retries += 1
                        continue
                
                elif is_server_error or is_not_found:
                    logger.warning(f"Model error ({error_msg}). Rotating model...")
                    if self._rotate_model():
                        continue

                # Other errors
                self.stats["errors"] += 1
                logger.error(f"Gemini API Error: {e}")
                
                if retries < max_retries:
                    # Short backoff for non-quota errors
                    await asyncio.sleep(2 * (retries + 1))
                    retries += 1
                    continue
                    
                raise e
        
        raise Exception("Max retries exceeded for Gemini API")

    def get_stats(self) -> Dict[str, int]:
        """Return usage statistics."""
        return self.stats

# Global instance
gemini_client = GeminiClient()
