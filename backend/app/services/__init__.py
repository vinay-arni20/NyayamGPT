"""
NyayamGPT - Services Package
============================
External service integrations.
"""

from app.services.kanoon_client import (
    IndianKanoonClient,
    get_kanoon_client,
    kanoon_search,
    get_section_url,
)

__all__ = [
    "IndianKanoonClient",
    "get_kanoon_client",
    "kanoon_search",
    "get_section_url",
]
