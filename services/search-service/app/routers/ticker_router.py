"""
Ticker search router using Massive API.

Provides comprehensive ticker search across all US stock exchanges
with caching and fallback to local database.
"""

import structlog
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional

from ..infrastructure.massive_client import get_massive_client, TickerInfo, NewsArticle

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/tickers", tags=["tickers"])


class AddressInfo(BaseModel):
    """Company address information."""
    address1: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None


class TickerSearchResult(BaseModel):
    """Individual ticker search result."""
    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    exchange: str = Field(..., description="Primary exchange")
    type: str = Field(..., description="Security type (CS=Common Stock, ETF, etc.)")
    market: str = Field(..., description="Market (stocks, crypto, fx)")
    active: bool = Field(default=True, description="Whether ticker is actively traded")
    currency: Optional[str] = Field(None, description="Trading currency")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "exchange": "XNAS",
                "type": "CS",
                "market": "stocks",
                "active": True,
                "currency": "usd"
            }
        }


class TickerDetailResult(BaseModel):
    """Extended ticker detail information."""
    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company name")
    exchange: str = Field(..., description="Primary exchange")
    type: str = Field(..., description="Security type")
    market: str = Field(..., description="Market")
    active: bool = Field(default=True)
    currency: Optional[str] = None
    
    # Extended company details
    description: Optional[str] = Field(None, description="Company description")
    homepage_url: Optional[str] = Field(None, description="Company website")
    phone_number: Optional[str] = Field(None, description="Company phone")
    total_employees: Optional[int] = Field(None, description="Number of employees")
    list_date: Optional[str] = Field(None, description="IPO/listing date")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    shares_outstanding: Optional[int] = Field(None, description="Shares outstanding")
    weighted_shares_outstanding: Optional[int] = Field(None, description="Weighted shares outstanding")
    round_lot: Optional[int] = Field(None, description="Round lot size")
    
    # Classification
    sic_code: Optional[str] = Field(None, description="SIC industry code")
    sic_description: Optional[str] = Field(None, description="SIC industry description")
    
    # Address
    address: Optional[AddressInfo] = Field(None, description="Company headquarters")
    
    # Branding
    logo_url: Optional[str] = Field(None, description="Company logo URL")
    icon_url: Optional[str] = Field(None, description="Company icon URL")


class NewsArticleResult(BaseModel):
    """News article result."""
    id: str = Field(..., description="Article ID")
    title: str = Field(..., description="Article title")
    author: Optional[str] = Field(None, description="Article author")
    published_utc: str = Field(..., description="Publication timestamp")
    article_url: str = Field(..., description="Article URL")
    description: Optional[str] = Field(None, description="Article summary")
    image_url: Optional[str] = Field(None, description="Article image")
    publisher_name: Optional[str] = Field(None, description="Publisher name")
    publisher_logo_url: Optional[str] = Field(None, description="Publisher logo")
    tickers: List[str] = Field(default_factory=list, description="Related tickers")
    keywords: Optional[List[str]] = Field(None, description="Article keywords")


class TickerSearchResponse(BaseModel):
    """Ticker search response."""
    success: bool = True
    results: List[TickerSearchResult]
    query: str
    total_count: int
    message: str = "Search completed successfully"


class TickerDetailResponse(BaseModel):
    """Detailed ticker information response with extended company data."""
    success: bool = True
    data: TickerDetailResult
    message: str = "Ticker details retrieved successfully"


class TickerNewsResponse(BaseModel):
    """News articles response."""
    success: bool = True
    articles: List[NewsArticleResult]
    ticker: str
    count: int
    message: str = "News retrieved successfully"


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    message: str


@router.get(
    "/search",
    response_model=TickerSearchResponse,
    responses={
        200: {"description": "Search completed successfully"},
        400: {"description": "Invalid search query", "model": ErrorResponse},
        500: {"description": "External service error", "model": ErrorResponse},
        503: {"description": "Massive API unavailable", "model": ErrorResponse},
    },
    summary="Search tickers by name or symbol",
    description="""
    Search for stock tickers across all major US exchanges.
    
    Powered by Massive API (formerly Polygon.io), covers:
    - NYSE, NASDAQ, AMEX
    - All 19 major US exchanges
    - FINRA and OTC markets
    
    Search matches both ticker symbols and company names.
    Results are sorted by relevance.
    """,
)
async def search_tickers(
    q: str = Query(
        ...,
        min_length=1,
        max_length=100,
        description="Search query (ticker symbol or company name)",
        json_schema_extra={"example": "apple"},
    ),
    market: str = Query(
        default="stocks",
        description="Market filter (stocks, crypto, fx, otc)",
    ),
    active: bool = Query(
        default=True,
        description="Only return actively traded tickers",
    ),
    limit: int = Query(
        default=25,
        ge=1,
        le=100,
        description="Maximum results to return",
    ),
) -> TickerSearchResponse:
    """
    Search for tickers matching the query.
    
    Returns matching tickers sorted by relevance with company details.
    """
    client = get_massive_client()
    
    if not client.api_key:
        logger.warning("Massive API key not configured, returning empty results")
        return TickerSearchResponse(
            success=True,
            results=[],
            query=q,
            total_count=0,
            message="Search service not configured - API key missing",
        )
    
    try:
        tickers = await client.search_tickers(
            query=q,
            market=market,
            active=active,
            limit=limit,
        )
        
        results = [
            TickerSearchResult(
                ticker=t.ticker,
                name=t.name,
                exchange=t.primary_exchange,
                type=t.type,
                market=t.market,
                active=t.active,
                currency=t.currency_name,
            )
            for t in tickers
        ]
        
        logger.info(
            "Ticker search completed",
            query=q,
            results_count=len(results),
        )
        
        return TickerSearchResponse(
            success=True,
            results=results,
            query=q,
            total_count=len(results),
        )
        
    except ValueError as e:
        logger.error("Ticker search configuration error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": "service_not_configured",
                "message": str(e),
            },
        )
    except Exception as e:
        logger.error("Ticker search failed", error=str(e), query=q)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "search_failed",
                "message": f"Failed to search tickers: {str(e)}",
            },
        )


@router.get(
    "/{ticker}",
    response_model=TickerDetailResponse,
    responses={
        200: {"description": "Ticker details retrieved"},
        404: {"description": "Ticker not found", "model": ErrorResponse},
        503: {"description": "Massive API unavailable", "model": ErrorResponse},
    },
    summary="Get ticker details",
    description="""
    Get detailed information for a specific ticker symbol.
    
    Returns extended company information including:
    - Basic info (name, exchange, type, market status)
    - Company details (description, employees, website)
    - Financial info (market cap, shares outstanding)
    - Address and branding (logo)
    """,
)
async def get_ticker_details(
    ticker: str,
) -> TickerDetailResponse:
    """
    Get detailed information for a ticker.
    
    Returns company name, description, employees, website, market cap, and more.
    """
    client = get_massive_client()
    
    if not client.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": "service_not_configured",
                "message": "Massive API key not configured",
            },
        )
    
    try:
        ticker_info = await client.get_ticker_details(ticker.upper())
        
        if not ticker_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": "ticker_not_found",
                    "message": f"Ticker '{ticker.upper()}' not found",
                },
            )
        
        # Build address info if available
        address_info = None
        if ticker_info.address:
            address_info = AddressInfo(
                address1=ticker_info.address.address1,
                city=ticker_info.address.city,
                state=ticker_info.address.state,
                postal_code=ticker_info.address.postal_code,
            )
        
        return TickerDetailResponse(
            success=True,
            data=TickerDetailResult(
                ticker=ticker_info.ticker,
                name=ticker_info.name,
                exchange=ticker_info.primary_exchange,
                type=ticker_info.type,
                market=ticker_info.market,
                active=ticker_info.active,
                currency=ticker_info.currency_name,
                # Extended details
                description=ticker_info.description,
                homepage_url=ticker_info.homepage_url,
                phone_number=ticker_info.phone_number,
                total_employees=ticker_info.total_employees,
                list_date=ticker_info.list_date,
                market_cap=ticker_info.market_cap,
                shares_outstanding=ticker_info.shares_outstanding,
                weighted_shares_outstanding=ticker_info.weighted_shares_outstanding,
                round_lot=ticker_info.round_lot,
                sic_code=ticker_info.sic_code,
                sic_description=ticker_info.sic_description,
                address=address_info,
                logo_url=ticker_info.logo_url,
                icon_url=ticker_info.icon_url,
            ),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Get ticker details failed", error=str(e), ticker=ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "fetch_failed",
                "message": f"Failed to get ticker details: {str(e)}",
            },
        )


@router.get(
    "/{ticker}/news",
    response_model=TickerNewsResponse,
    responses={
        200: {"description": "News articles retrieved"},
        503: {"description": "Massive API unavailable", "model": ErrorResponse},
    },
    summary="Get ticker news",
    description="""
    Get recent news articles for a specific ticker symbol.
    
    Returns news from major financial publishers with:
    - Article title and summary
    - Publication date and author
    - Publisher information
    - Related tickers and keywords
    """,
)
async def get_ticker_news(
    ticker: str,
    limit: int = Query(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of articles to return",
    ),
) -> TickerNewsResponse:
    """
    Get news articles for a ticker.
    
    Returns recent news articles from financial publishers.
    """
    client = get_massive_client()
    
    if not client.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": "service_not_configured",
                "message": "Massive API key not configured",
            },
        )
    
    try:
        articles = await client.get_ticker_news(ticker.upper(), limit=limit)
        
        return TickerNewsResponse(
            success=True,
            articles=[
                NewsArticleResult(
                    id=a.id,
                    title=a.title,
                    author=a.author,
                    published_utc=a.published_utc,
                    article_url=a.article_url,
                    description=a.description,
                    image_url=a.image_url,
                    publisher_name=a.publisher_name,
                    publisher_logo_url=a.publisher_logo_url,
                    tickers=a.tickers,
                    keywords=a.keywords,
                )
                for a in articles
            ],
            ticker=ticker.upper(),
            count=len(articles),
        )
        
    except Exception as e:
        logger.error("Get ticker news failed", error=str(e), ticker=ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "fetch_failed",
                "message": f"Failed to get ticker news: {str(e)}",
            },
        )