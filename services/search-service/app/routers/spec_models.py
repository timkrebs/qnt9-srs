"""
API response models conforming to technical specification.

Defines Pydantic models for API responses that match the spec format.
"""

from typing import List

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """
    Individual search result matching technical specification.

    Attributes:
        symbol: Stock ticker symbol
        name: Company name
        exchange: Stock exchange
        type: Security type (always 'stock' for now)
        match_score: Relevance score (0-1.0 scale per spec)
    """

    symbol: str = Field(..., description="Stock ticker symbol", examples=["AAPL"])
    name: str = Field(..., description="Company name", examples=["Apple Inc."])
    exchange: str = Field(..., description="Stock exchange", examples=["NASDAQ"])
    type: str = Field(default="stock", description="Security type", examples=["stock"])
    match_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance score (1.0=exact, 0.8=prefix, 0.6=contains, 0.5=name_prefix, 0.3=name_contains)",
        examples=[1.0, 0.8, 0.5],
    )


class SearchResponse(BaseModel):
    """
    Search response conforming to technical specification.

    Response format:
    {
        "results": [...],
        "query": "aapl",
        "total_matches": 1
    }
    """

    results: List[SearchResultItem] = Field(
        ..., description="List of matching stocks ranked by relevance"
    )
    query: str = Field(..., description="Original search query")
    total_matches: int = Field(..., description="Total number of matches found")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: dict = Field(default_factory=dict, description="Additional error details")
