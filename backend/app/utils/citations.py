"""
NyayamGPT - Citation Utilities
==============================
Utilities for extracting, formatting, and validating legal citations.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from app.core.logging import logger


@dataclass
class LegalCitation:
    """Structured legal citation."""
    
    law: str
    section: str
    title: Optional[str] = None
    subsection: Optional[str] = None
    clause: Optional[str] = None
    source_url: Optional[str] = None
    verified: bool = False
    context: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "law": self.law,
            "section": self.section,
            "title": self.title,
            "subsection": self.subsection,
            "clause": self.clause,
            "source_url": self.source_url,
            "verified": self.verified,
            "context": self.context
        }
    
    def format_short(self) -> str:
        """Format as short citation."""
        parts = [self.law, f"Section {self.section}"]
        if self.subsection:
            parts.append(f"({self.subsection})")
        return " ".join(parts)
    
    def format_full(self) -> str:
        """Format as full citation with title."""
        result = self.format_short()
        if self.title:
            result += f": {self.title}"
        return result


# Citation patterns for Indian laws
CITATION_PATTERNS = [
    # IPC Sections
    (
        r"(?:Section|Sec\.?|S\.?)\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?(?:IPC|Indian\s*Penal\s*Code)",
        "IPC"
    ),
    # CrPC Sections
    (
        r"(?:Section|Sec\.?|S\.?)\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?(?:CrPC|Cr\.?P\.?C\.?|Code\s*of\s*Criminal\s*Procedure)",
        "CrPC"
    ),
    # CPC Sections
    (
        r"(?:Section|Sec\.?|S\.?)\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?(?:CPC|C\.?P\.?C\.?|Code\s*of\s*Civil\s*Procedure)",
        "CPC"
    ),
    # Constitution Articles
    (
        r"Article\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?Constitution",
        "Constitution"
    ),
    # Evidence Act
    (
        r"(?:Section|Sec\.?|S\.?)\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?(?:Indian\s*)?Evidence\s*Act",
        "Evidence Act"
    ),
    # IT Act
    (
        r"(?:Section|Sec\.?|S\.?)\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?(?:IT|Information\s*Technology)\s*Act",
        "IT Act"
    ),
    # Motor Vehicles Act
    (
        r"(?:Section|Sec\.?|S\.?)\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?Motor\s*Vehicles\s*Act",
        "Motor Vehicles Act"
    ),
    # NDPS Act
    (
        r"(?:Section|Sec\.?|S\.?)\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?(?:NDPS|Narcotic\s*Drugs)",
        "NDPS Act"
    ),
    # Consumer Protection Act
    (
        r"(?:Section|Sec\.?|S\.?)\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?Consumer\s*Protection\s*Act",
        "Consumer Protection Act"
    ),
    # Domestic Violence Act
    (
        r"(?:Section|Sec\.?|S\.?)\s*(\d+[A-Z]?)\s*(?:of\s*)?(?:the\s*)?(?:Protection\s*of\s*Women\s*from\s*)?Domestic\s*Violence\s*Act",
        "DV Act"
    ),
    # Generic IPC pattern (just number after IPC mention)
    (
        r"IPC\s*(?:Section|Sec\.?)?\s*(\d+[A-Z]?)",
        "IPC"
    ),
    # Generic Section pattern
    (
        r"(?:Section|Sec\.?)\s*(\d+[A-Z]?)\s*(?:IPC|CrPC|CPC)",
        None  # Will be determined from match
    ),
]


def extract_citations(text: str) -> list[LegalCitation]:
    """
    Extract legal citations from text.
    
    Args:
        text: Text containing legal citations
        
    Returns:
        list[LegalCitation]: Extracted citations
    """
    citations = []
    seen = set()  # Avoid duplicates
    
    for pattern, law in CITATION_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            section = match.group(1)
            
            # Determine law from match if not specified
            actual_law = law
            if actual_law is None:
                full_match = match.group(0).upper()
                if "IPC" in full_match:
                    actual_law = "IPC"
                elif "CRPC" in full_match:
                    actual_law = "CrPC"
                elif "CPC" in full_match:
                    actual_law = "CPC"
                else:
                    continue
            
            # Create unique key
            key = f"{actual_law}:{section}"
            if key in seen:
                continue
            seen.add(key)
            
            # Get context (surrounding text)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()
            
            citations.append(LegalCitation(
                law=actual_law,
                section=section,
                context=context
            ))
    
    logger.debug(f"Extracted {len(citations)} citations from text")
    return citations


def format_citations_markdown(citations: list[LegalCitation]) -> str:
    """
    Format citations as markdown list.
    
    Args:
        citations: List of citations
        
    Returns:
        str: Markdown formatted citations
    """
    if not citations:
        return ""
    
    lines = ["### Legal References\n"]
    
    for citation in citations:
        line = f"- **{citation.format_short()}**"
        if citation.title:
            line += f": {citation.title}"
        if citation.source_url:
            line += f" [Source]({citation.source_url})"
        lines.append(line)
    
    return "\n".join(lines)


def format_citations_html(citations: list[LegalCitation]) -> str:
    """
    Format citations as HTML.
    
    Args:
        citations: List of citations
        
    Returns:
        str: HTML formatted citations
    """
    if not citations:
        return ""
    
    html = ["<div class='legal-citations'>", "<h4>Legal References</h4>", "<ul>"]
    
    for citation in citations:
        html.append("<li>")
        html.append(f"<strong>{citation.format_short()}</strong>")
        if citation.title:
            html.append(f": {citation.title}")
        if citation.source_url:
            html.append(f" <a href='{citation.source_url}' target='_blank'>Source</a>")
        html.append("</li>")
    
    html.extend(["</ul>", "</div>"])
    return "\n".join(html)


def get_source_url(law: str, section: str) -> Optional[str]:
    """
    Get official source URL for a citation.
    
    Args:
        law: Law name
        section: Section number
        
    Returns:
        Optional[str]: Source URL if available
    """
    # India Kanoon URLs
    base_urls = {
        "IPC": "https://indiankanoon.org/search/?formInput=section%20{}%20IPC",
        "CrPC": "https://indiankanoon.org/search/?formInput=section%20{}%20CrPC",
        "CPC": "https://indiankanoon.org/search/?formInput=section%20{}%20CPC",
        "Constitution": "https://indiankanoon.org/search/?formInput=article%20{}%20constitution",
    }
    
    if law in base_urls:
        return base_urls[law].format(section)
    
    return None


def validate_citation(citation: LegalCitation, valid_sections: dict) -> bool:
    """
    Validate a citation against known valid sections.
    
    Args:
        citation: Citation to validate
        valid_sections: Dictionary of valid sections per law
        
    Returns:
        bool: Whether citation is valid
    """
    law_sections = valid_sections.get(citation.law, set())
    return citation.section in law_sections


# Known valid IPC sections (subset for validation)
KNOWN_IPC_SECTIONS = {
    "302", "304", "307", "354", "376", "379", "380", "384", "392",
    "394", "395", "397", "406", "420", "467", "468", "471", "498A",
    "499", "500", "506", "509"
}

KNOWN_CRPC_SECTIONS = {
    "41", "154", "156", "161", "164", "167", "173", "190", "200",
    "204", "227", "228", "239", "240", "241", "313", "354", "374",
    "378", "437", "438", "439", "482"
}
