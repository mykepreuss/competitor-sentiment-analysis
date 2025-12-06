"""
Competitor Analysis Engine package.

This package exposes a host-agnostic analysis engine intended to be called over
JSON/HTTP and integrated with Hummingbird or other orchestrators. The initial
implementation provides scaffolding; concrete logic can be filled in
incrementally.
"""

__all__ = [
    "engine",
    "models",
    "config",
    "scraper",
    "analysis",
    "summary",
    "reports",
    "jobs",
    "store",
]

__version__ = "0.0.1"

