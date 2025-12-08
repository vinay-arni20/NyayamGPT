"""
NyayamGPT - Citation Resolver Agent
===================================
Resolves legal citations to official Indian Kanoon URLs.
"""

import re
import urllib.parse
from typing import Any, Optional

import httpx
from opentelemetry import trace

from app.core.config import settings
from app.core.logging import logger
from app.services.kanoon_client import IndianKanoonClient, get_kanoon_client

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Official Indian Law Sources (priority order)
OFFICIAL_SOURCES = [
    "indiacode.nic.in",
    "legislative.gov.in",
    "egazette.nic.in",
    "ncrb.gov.in",
    "prsindia.org",
]

# Fallback source
FALLBACK_SOURCE = "indiankanoon.org"

# Known base URLs for direct linking
KNOWN_URLS = {
    "IPC": "https://www.indiacode.nic.in/handle/123456789/2263",
    "CRPC": "https://www.indiacode.nic.in/handle/123456789/1611",
    "CPC": "https://www.indiacode.nic.in/handle/123456789/2191",
    "CONSTITUTION": "https://www.indiacode.nic.in/handle/123456789/1362",
    "IT_ACT": "https://www.indiacode.nic.in/handle/123456789/1999",
    "EVIDENCE_ACT": "https://www.indiacode.nic.in/handle/123456789/1364",
    "IEA": "https://www.indiacode.nic.in/handle/123456789/1364",
    "CONTRACT_ACT": "https://www.indiacode.nic.in/handle/123456789/2187",
    "MOTOR_VEHICLES_ACT": "https://www.indiacode.nic.in/handle/123456789/1798",
    "MVA": "https://www.indiacode.nic.in/handle/123456789/1798",
    "POCSO": "https://www.indiacode.nic.in/handle/123456789/2079",
    "HMA": "https://www.indiacode.nic.in/handle/123456789/1560",
    "HINDU_MARRIAGE_ACT": "https://www.indiacode.nic.in/handle/123456789/1560",
    "IDA": "https://www.indiacode.nic.in/handle/123456789/1459",
    "INDUSTRIAL_DISPUTES_ACT": "https://www.indiacode.nic.in/handle/123456789/1459",
    "NIA": "https://www.indiacode.nic.in/handle/123456789/2037",
    "NIA_ACT": "https://www.indiacode.nic.in/handle/123456789/2037",
}

# Act name mappings for search
ACT_NAMES = {
    "IPC": "Indian Penal Code",
    "CRPC": "Code of Criminal Procedure",
    "CPC": "Code of Civil Procedure",
    "IT_ACT": "Information Technology Act",
    "EVIDENCE_ACT": "Indian Evidence Act",
    "IEA": "Indian Evidence Act",
    "CONTRACT_ACT": "Indian Contract Act",
    "MOTOR_VEHICLES_ACT": "Motor Vehicles Act",
    "MVA": "Motor Vehicles Act",
    "POCSO": "Protection of Children from Sexual Offences Act",
    "CONSTITUTION": "Constitution of India",
    "HMA": "Hindu Marriage Act",
    "HINDU_MARRIAGE_ACT": "Hindu Marriage Act",
    "IDA": "Industrial Disputes Act",
    "INDUSTRIAL_DISPUTES_ACT": "Industrial Disputes Act",
    "NIA": "National Investigation Agency Act",
    "NIA_ACT": "National Investigation Agency Act",
}


class CitationResolver:
    """
    Resolves legal citations to Indian Kanoon URLs.
    
    Uses Indian Kanoon API as primary source for Indian legal
    sections and acts with fallback to generated URLs.
    """
    
    def __init__(self):
        """Initialize the citation resolver."""
        self.client = httpx.AsyncClient(timeout=10.0)
        self.cache: dict[str, str] = {}
        self.kanoon_client = get_kanoon_client()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _clean_text(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        return re.sub(r'<[^>]+>', '', text)
    
    @tracer.start_as_current_span("resolve_citation")
    async def resolve_citation(
        self,
        act: str,
        section: str,
        title: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Resolve a single citation to an Indian Kanoon URL.
        
        Args:
            act: Act name (e.g., "IPC", "CrPC")
            section: Section number (e.g., "420", "302")
            title: Optional section title
            
        Returns:
            dict: Citation with URL
        """
        span = trace.get_current_span()
        span.set_attribute("act", act)
        span.set_attribute("section", section)
        
        cache_key = f"{act.upper()}:{section}"
        
        # Check cache first
        if cache_key in self.cache:
            logger.debug("Citation found in cache", act=act, section=section)
            return {
                "act": act,
                "section": section,
                "title": title or "",
                "url": self.cache[cache_key],
                "verified": True
            }
        
        # Get full act name for search
        act_upper = act.upper().replace(" ", "_")
        act_full_name = ACT_NAMES.get(act_upper, act)
        
        # Try Indian Kanoon API first
        try:
            # Use search_section which handles both exact matches and fallbacks
            kanoon_result = await self.kanoon_client.search_section(
                act_full_name, section
            )
            
            if kanoon_result and kanoon_result.get("url"):
                url = kanoon_result["url"]
                self.cache[cache_key] = url
                span.set_attribute("url_found", True)
                span.set_attribute("source", kanoon_result.get("source", "indian_kanoon"))
                
                logger.info(
                    "Citation resolved via Indian Kanoon",
                    act=act,
                    section=section,
                    url=url
                )
                
                return {
                    "act": act,
                    "section": section,
                    "title": self._clean_text(title or kanoon_result.get("title", "")),
                    "url": url,
                    "verified": True,
                    "source": "Indian Kanoon"
                }
        except Exception as e:
            logger.warning(
                "Indian Kanoon API failed, using fallback generation",
                error=str(e),
                act=act,
                section=section
            )
        
        # Use Indian Kanoon fallback URL directly if API fails
        fallback_url = self._get_fallback_url(act, section)
        self.cache[cache_key] = fallback_url
        span.set_attribute("url_found", True)
        span.set_attribute("source", "fallback")
        
        return {
            "act": act,
            "section": section,
            "title": self._clean_text(title or ""),
            "url": fallback_url,
            "verified": False,
            "source": "Indian Kanoon (generated)"
        }
    
    @tracer.start_as_current_span("resolve_all_citations")
    async def resolve_all_citations(
        self,
        citations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Resolve multiple citations to URLs.        
        Args:
            citations: List of citation dicts with act, section, title
            
        Returns:
            list: Citations with URLs added
        """
        resolved = []
        
        for citation in citations:
            act = citation.get("act", citation.get("law", ""))
            section = citation.get("section", "")
            title = citation.get("title", "")
            
            if act and section:
                resolved_citation = await self.resolve_citation(act, section, title)
                # Preserve any extra fields from original citation
                resolved_citation.update({
                    k: v for k, v in citation.items() 
                    if k not in ["act", "section", "title", "url", "verified"]
                })
                resolved.append(resolved_citation)
            else:
                # Keep original if missing required fields
                resolved.append(citation)
        
        return resolved
    
    def _get_fallback_url(self, act: str, section: str) -> str:
        """
        Generate a fallback URL using Indian Kanoon.
        
        Args:
            act: Act name
            section: Section number
            
        Returns:
            str: Fallback search URL
        """
        act_name = ACT_NAMES.get(act.upper().replace(" ", "_"), act)
        query = urllib.parse.quote(f"{act_name} Section {section}")
        return f"https://indiankanoon.org/search/?formInput={query}"


# Singleton instance
_resolver: Optional[CitationResolver] = None


def get_citation_resolver() -> CitationResolver:
    """
    Get the citation resolver singleton.
    
    Returns:
        CitationResolver: Resolver instance
    """
    global _resolver
    if _resolver is None:
        _resolver = CitationResolver()
    return _resolver


@tracer.start_as_current_span("resolve_citations")
async def resolve_citations(
    citations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Convenience function to resolve citations.
    
    Args:
        citations: List of citations to resolve
        
    Returns:
        list: Resolved citations with URLs
    """
    resolver = get_citation_resolver()
    return await resolver.resolve_all_citations(citations)
