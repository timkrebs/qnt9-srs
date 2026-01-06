"""
Stock Data Router for real-time financial information.

Provides endpoints for:
- Real-time stock quotes
- Intraday chart data
- Company news feed
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.financial_data_service import financial_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stocks", tags=["Stock Data"])


class StockQuote(BaseModel):
    """Real-time stock quote model."""

    symbol: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Stock name")
    price: float = Field(..., description="Current price")
    change: float = Field(..., description="Price change from previous close")
    change_percent: float = Field(..., description="Percentage change")
    volume: int = Field(..., description="Trading volume")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Day's high price")
    low: float = Field(..., description="Day's low price")
    previous_close: float = Field(..., description="Previous closing price")
    market_cap: Optional[int] = Field(None, description="Market capitalization")
    timestamp: str = Field(..., description="Data timestamp")


class ChartDataPoint(BaseModel):
    """OHLCV data point for charts."""

    timestamp: str = Field(..., description="Data point timestamp")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Volume")


class NewsArticle(BaseModel):
    """News article model."""

    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    summary: str = Field(..., description="Article summary/description")
    source: str = Field(..., description="News source/publisher")
    published_at: str = Field(..., description="Publication timestamp")
    image_url: Optional[str] = Field(None, description="Article image URL")


@router.get("/{symbol}/quote", response_model=StockQuote, summary="Get real-time stock quote")
async def get_stock_quote(symbol: str) -> StockQuote:
    """
    Get real-time quote data for a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g., AAPL, MSFT, TSLA)

    Returns:
        Real-time quote including price, change, volume, and other data

    Raises:
        HTTPException: If unable to fetch quote data
    """
    try:
        logger.info(f"Fetching quote for symbol: {symbol}")
        quote_data = await financial_data_service.get_real_time_quote(symbol)

        if not quote_data:
            raise HTTPException(
                status_code=404, detail=f"No quote data available for symbol: {symbol}"
            )

        return StockQuote(**quote_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock quote")


@router.get(
    "/{symbol}/chart",
    response_model=List[ChartDataPoint],
    summary="Get intraday chart data",
)
async def get_chart_data(
    symbol: str,
    timespan: str = Query("minute", description="Time resolution: minute, hour, day"),
    multiplier: int = Query(5, description="Multiplier for timespan (e.g., 5 for 5-minute bars)", ge=1, le=60),
) -> List[ChartDataPoint]:
    """
    Get intraday price data for charting.

    Args:
        symbol: Stock ticker symbol
        timespan: Time resolution (minute, hour, day)
        multiplier: Multiplier for timespan

    Returns:
        List of OHLCV data points for the current trading day

    Raises:
        HTTPException: If unable to fetch chart data
    """
    try:
        logger.info(f"Fetching chart data for {symbol}: {multiplier}{timespan}")
        chart_data = await financial_data_service.get_intraday_data(
            symbol, timespan=timespan, multiplier=multiplier
        )

        if not chart_data:
            raise HTTPException(
                status_code=404, detail=f"No chart data available for symbol: {symbol}"
            )

        return [ChartDataPoint(**point) for point in chart_data]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chart data")


@router.get(
    "/{symbol}/news",
    response_model=List[NewsArticle],
    summary="Get company news",
)
async def get_company_news(
    symbol: str,
    limit: int = Query(10, description="Maximum number of articles", ge=1, le=50),
) -> List[NewsArticle]:
    """
    Get latest news articles for a company.

    Args:
        symbol: Stock ticker symbol
        limit: Maximum number of articles to return

    Returns:
        List of recent news articles

    Raises:
        HTTPException: If unable to fetch news
    """
    try:
        logger.info(f"Fetching news for {symbol}, limit: {limit}")
        news_data = await financial_data_service.get_company_news(symbol, limit=limit)

        if not news_data:
            return []

        return [NewsArticle(**article) for article in news_data]

    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch company news")
