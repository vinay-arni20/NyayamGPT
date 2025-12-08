"""
NyayamGPT - Web Search Service
==============================
Service for searching trusted legal websites using DuckDuckGo.
"""

import warnings
from typing import Any, List, Optional
from ddgs import DDGS
from opentelemetry import trace
from app.core.logging import logger

# Suppress the specific RuntimeWarning from duckduckgo_search
warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Whitelist of trusted Indian legal domains
TRUSTED_DOMAINS = [
    "indiankanoon.org",
    "indiacode.nic.in",
    "sci.gov.in",
    "livelaw.in",
    "barandbench.com",
    "prsindia.org",
    "legalserviceindia.com",
    "pathlegal.com"
]

class WebSearchService:
    """
    Service to search the web for legal information from trusted sources.
    """
    
    def __init__(self):
        pass

    @tracer.start_as_current_span("web_search_legal")
    def search_legal_sources(self, query: str, max_results: int = 8) -> List[dict[str, Any]]:
        """
        Search trusted legal sources for the query.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List[dict]: List of search results with title, href, body
        """
        span = trace.get_current_span()
        span.set_attribute("query", query)
        
        results = []
        try:
            # STRATEGY: Use a broad, natural query. 
            # Avoid 'site:' operators as they often return 0 results via API.
            # Append "India law" to ensure jurisdiction context.
            search_query = f"{query} India law"
            
            logger.info(f"Executing web search: {search_query}")
            
            # DDGS.text() is synchronous
            # Use context manager to ensure proper cleanup
            with DDGS() as ddgs:
                search_results = ddgs.text(search_query, max_results=max_results)
                
                if search_results:
                    for r in search_results:
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("href", ""),
                            "snippet": r.get("body", ""),
                            "source": self._extract_source(r.get("href", ""))
                        })
            
            span.set_attribute("results_count", len(results))
            logger.info("Web search completed", query=query, results=len(results))
            
        except Exception as e:
            span.set_attribute("error", True)
            import traceback
            logger.error(f"Web search failed: {str(e)}\n{traceback.format_exc()}")
            # No fallback needed as the primary query is already broad
            
        return results

    def _extract_source(self, url: str) -> str:
        """Extract the source domain name from URL."""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.replace("www.", "")
        except:
            return "External Source"
