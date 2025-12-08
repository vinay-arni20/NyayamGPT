"""
NyayamGPT - Web Search Node
===========================
Web search integration for fetching external legal information.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
import aiohttp

from app.core.logging import logger
from app.core.config import settings


class WebSearchResult:
    """Represents a single web search result."""
    
    def __init__(
        self,
        index: int,
        title: str,
        url: str,
        snippet: str,
        date: Optional[str] = None,
        source_type: Optional[str] = None,
    ):
        self.index = index
        self.title = title
        self.url = url
        self.snippet = snippet
        self.date = date
        self.source_type = source_type or self._classify_source(url)
    
    def _classify_source(self, url: str) -> str:
        """Classify the source type based on URL."""
        url_lower = url.lower()
        
        if ".gov.in" in url_lower or ".nic.in" in url_lower:
            return "official"
        elif "indiankanoon" in url_lower or "scconline" in url_lower:
            return "legal_database"
        elif "barandbench" in url_lower or "livelaw" in url_lower:
            return "legal_news"
        elif any(x in url_lower for x in [".edu", "law.ac", "university"]):
            return "academic"
        else:
            return "general"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "index": self.index,
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "date": self.date,
            "source_type": self.source_type,
        }


async def search_duckduckgo(query: str, max_results: int = 5) -> List[WebSearchResult]:
    """
    Search using DuckDuckGo (no API key required).
    
    Args:
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        List of WebSearchResult objects
    """
    try:
        from duckduckgo_search import DDGS
        
        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(
                f"{query} India law legal",
                max_results=max_results
            ))
            
            for i, result in enumerate(search_results):
                results.append(WebSearchResult(
                    index=i + 1,
                    title=result.get("title", ""),
                    url=result.get("href", result.get("link", "")),
                    snippet=result.get("body", result.get("snippet", "")),
                    date=None,
                ))
        
        return results
        
    except ImportError:
        logger.warning("[WEB_SEARCH] duckduckgo_search not installed, using fallback")
        return []
    except Exception as e:
        logger.error(f"[WEB_SEARCH] DuckDuckGo search failed: {e}")
        return []


async def search_serper(query: str, max_results: int = 5) -> List[WebSearchResult]:
    """
    Search using Serper API (Google Search).
    
    Args:
        query: Search query
        max_results: Maximum number of results
        
    Returns:
        List of WebSearchResult objects
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        logger.warning("[WEB_SEARCH] SERPER_API_KEY not configured")
        return []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "q": f"{query} India law legal",
                    "gl": "in",
                    "num": max_results,
                }
            ) as response:
                if response.status != 200:
                    logger.error(f"[WEB_SEARCH] Serper API error: {response.status}")
                    return []
                
                data = await response.json()
                results = []
                
                for i, item in enumerate(data.get("organic", [])[:max_results]):
                    results.append(WebSearchResult(
                        index=i + 1,
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        date=item.get("date"),
                    ))
                
                return results
                
    except Exception as e:
        logger.error(f"[WEB_SEARCH] Serper search failed: {e}")
        return []


async def web_search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform web search and add results to state.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with web search results
    """
    query = state.get("query", "")
    max_results = state.get("retrieval_config", {}).get("web_results", 5)
    
    logger.info(f"[WEB_SEARCH] Searching for: {query[:50]}...")
    start_time = datetime.now()
    
    # Try Serper first, fallback to DuckDuckGo
    results = await search_serper(query, max_results)
    
    if not results:
        results = await search_duckduckgo(query, max_results)
    
    search_time = (datetime.now() - start_time).total_seconds() * 1000
    logger.info(f"[WEB_SEARCH] Found {len(results)} sources in {search_time:.0f}ms")
    
    # Convert results to dictionaries
    web_sources = [r.to_dict() for r in results]
    
    # Format web context for LLM
    web_context = format_web_context(results)
    
    # Prioritize official sources
    prioritized_sources = prioritize_sources(results)
    
    return {
        **state,
        "web_sources": web_sources,
        "web_context": web_context,
        "prioritized_sources": [s.to_dict() for s in prioritized_sources],
        "search_performed": True,
        "search_time_ms": search_time,
    }


def format_web_context(results: List[WebSearchResult]) -> str:
    """
    Format web search results as context for LLM.
    
    Args:
        results: List of search results
        
    Returns:
        Formatted markdown string
    """
    if not results:
        return "No web search results found."
    
    formatted = ["## Web Search Results\n"]
    
    for result in results:
        source_label = {
            "official": "🏛️ Official",
            "legal_database": "⚖️ Legal Database",
            "legal_news": "📰 Legal News",
            "academic": "🎓 Academic",
            "general": "🌐 Web",
        }.get(result.source_type, "🌐 Web")
        
        formatted.append(f"### [{result.index}] {result.title}")
        formatted.append(f"**Source:** {source_label}")
        formatted.append(f"**URL:** {result.url}")
        if result.date:
            formatted.append(f"**Date:** {result.date}")
        formatted.append(f"\n{result.snippet}\n")
        formatted.append("---\n")
    
    return "\n".join(formatted)


def prioritize_sources(results: List[WebSearchResult]) -> List[WebSearchResult]:
    """
    Prioritize sources by reliability.
    
    Args:
        results: List of search results
        
    Returns:
        Sorted list with official sources first
    """
    priority = {
        "official": 0,
        "legal_database": 1,
        "legal_news": 2,
        "academic": 3,
        "general": 4,
    }
    
    return sorted(results, key=lambda r: priority.get(r.source_type, 5))
