"""
NyayamGPT - Indian Kanoon API Client
====================================
Client for querying the Indian Kanoon API to get official legal document URLs.
"""

import re
from typing import Any, Optional
from urllib.parse import quote

import httpx
from opentelemetry import trace

from app.core.config import settings
from app.core.logging import logger

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Indian Kanoon API endpoints
KANOON_SEARCH_URL = "https://api.indiankanoon.org/search/"
KANOON_DOC_URL = "https://api.indiankanoon.org/doc/"
KANOON_BASE_URL = "https://indiankanoon.org"


class IndianKanoonClient:
    """
    Client for the Indian Kanoon API.
    
    Uses shared token authentication to search for legal documents
    and retrieve official URLs for citations.
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Indian Kanoon client.
        
        Args:
            token: API token (defaults to settings.indian_kanoon_token)
        """
        self.token = token or settings.indian_kanoon_token
        self.client = httpx.AsyncClient(timeout=15.0)
        
        if not self.token:
            logger.warning("Indian Kanoon API token not configured")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _get_headers(self) -> dict[str, str]:
        """Get headers with authentication token."""
        headers = {
            "Accept": "application/json",
            "User-Agent": "NyayamGPT/1.0"
        }
        if self.token:
            headers["Authorization"] = f"Token {self.token}"
        return headers
    
    @tracer.start_as_current_span("kanoon_search")
    async def search(
        self,
        query: str,
        page_num: int = 0
    ) -> dict[str, Any]:
        """
        Search Indian Kanoon for legal documents.
        
        Args:
            query: Search query (e.g., "IPC Section 420")
            page_num: Page number for pagination
            
        Returns:
            dict: Search results with documents
        """
        span = trace.get_current_span()
        span.set_attribute("query", query)
        
        if not self.token:
            logger.warning("No Indian Kanoon token, using fallback URL")
            return self._create_fallback_result(query)
        
        try:
            params = {
                "formInput": query,
                "pagenum": page_num
            }
            
            # Indian Kanoon API expects POST for search
            response = await self.client.post(
                KANOON_SEARCH_URL,
                headers=self._get_headers(),
                data=params
            )
            
            if response.status_code == 200:
                data = response.json()
                span.set_attribute("results_count", len(data.get("docs", [])))
                logger.debug(
                    "Indian Kanoon search completed",
                    query=query,
                    results=len(data.get("docs", []))
                )
                return data
            else:
                logger.warning(
                    "Indian Kanoon API returned error",
                    status_code=response.status_code,
                    query=query
                )
                return self._create_fallback_result(query)
                
        except httpx.TimeoutException:
            logger.warning("Indian Kanoon API timeout", query=query)
            return self._create_fallback_result(query)
        except Exception as e:
            logger.error("Indian Kanoon API error", error=str(e), query=query)
            return self._create_fallback_result(query)
    
    @tracer.start_as_current_span("kanoon_get_document")
    async def get_document(self, doc_id: str) -> Optional[dict[str, Any]]:
        """
        Get a specific document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            dict or None: Document details
        """
        if not self.token:
            return None
            
        try:
            response = await self.client.get(
                f"{KANOON_DOC_URL}{doc_id}/",
                headers=self._get_headers()
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error("Failed to get document", doc_id=doc_id, error=str(e))
            return None
    
    @tracer.start_as_current_span("kanoon_search_section")
    async def search_section(
        self,
        act: str,
        section: str
    ) -> Optional[dict[str, Any]]:
        """
        Search for a specific section of an act.
        
        Args:
            act: Act name (e.g., "IPC", "CrPC")
            section: Section number
            
        Returns:
            dict or None: Best matching document with URL
        """
        span = trace.get_current_span()
        span.set_attribute("act", act)
        span.set_attribute("section", section)
        
        # Build search query
        act_full_name = self._get_full_act_name(act)
        query = f"{act_full_name} Section {section}"
        
        result = await self.search(query)
        
        if not result.get("docs"):
            # Try alternative query format
            query = f"Section {section} {act_full_name}"
            result = await self.search(query)
        
        if result.get("docs"):
            # Get the best matching document
            best_doc = self._find_best_match(result["docs"], act, section)
            if best_doc:
                return {
                    "doc_id": best_doc.get("tid"),
                    "title": best_doc.get("title", ""),
                    "url": f"{KANOON_BASE_URL}/doc/{best_doc.get('tid')}/",
                    "headline": best_doc.get("headline", ""),
                    "source": "indiankanoon"
                }
        
        # Return fallback if no results
        return {
            "doc_id": None,
            "title": f"{act} Section {section}",
            "url": f"{KANOON_BASE_URL}/search/?formInput={quote(query)}",
            "headline": "",
            "source": "indiankanoon_search"
        }
    
    def _get_full_act_name(self, act: str) -> str:
        """Convert act abbreviation to full name."""
        act_names = {
            "IPC": "Indian Penal Code",
            "CRPC": "Code of Criminal Procedure",
            "CPC": "Code of Civil Procedure",
            "IEA": "Indian Evidence Act",
            "HMA": "Hindu Marriage Act",
            "IDA": "Industrial Disputes Act",
            "MVA": "Motor Vehicles Act",
            "NIA": "Negotiable Instruments Act",
            "IT ACT": "Information Technology Act",
            "POCSO": "Protection of Children from Sexual Offences Act",
            "CONSTITUTION": "Constitution of India",
        }
        return act_names.get(act.upper().replace(" ", ""), act)
    
    def _find_best_match(
        self,
        docs: list[dict],
        act: str,
        section: str
    ) -> Optional[dict]:
        """
        Find the best matching document from search results.
        
        Prioritizes:
        1. Exact section match in title
        2. Act bare act documents
        3. First relevant result
        """
        act_lower = act.lower()
        section_patterns = [
            f"section {section}",
            f"sec. {section}",
            f"s. {section}",
            f"§ {section}"
        ]
        
        # First pass: Look for exact section match in bare act
        for doc in docs:
            title = doc.get("title", "").lower()
            headline = doc.get("headline", "").lower()
            
            # Check if it's a bare act section
            if any(p in title or p in headline for p in section_patterns):
                if act_lower in title or "bare act" in title.lower():
                    return doc
        
        # Second pass: Any document with section match
        for doc in docs:
            title = doc.get("title", "").lower()
            headline = doc.get("headline", "").lower()
            
            if any(p in title or p in headline for p in section_patterns):
                return doc
        
        # Third pass: Any document mentioning the act
        for doc in docs:
            title = doc.get("title", "").lower()
            if act_lower in title:
                return doc
        
        # Return first result as fallback
        return docs[0] if docs else None
    
    def _create_fallback_result(self, query: str) -> dict[str, Any]:
        """Create a fallback result with search URL."""
        return {
            "docs": [],
            "fallback_url": f"{KANOON_BASE_URL}/search/?formInput={quote(query)}",
            "error": "API unavailable"
        }


# Singleton instance
_client: Optional[IndianKanoonClient] = None


def get_kanoon_client() -> IndianKanoonClient:
    """
    Get the Indian Kanoon client singleton.
    
    Returns:
        IndianKanoonClient: Client instance
    """
    global _client
    if _client is None:
        _client = IndianKanoonClient()
    return _client


async def kanoon_search(query: str) -> dict[str, Any]:
    """
    Convenience function to search Indian Kanoon.
    
    Args:
        query: Search query
        
    Returns:
        dict: Search results
    """
    client = get_kanoon_client()
    return await client.search(query)


async def get_section_url(act: str, section: str) -> dict[str, Any]:
    """
    Get the URL for a specific section.
    
    Args:
        act: Act name
        section: Section number
        
    Returns:
        dict: Document info with URL
    """
    client = get_kanoon_client()
    return await client.search_section(act, section)
