"""
Stock snapshot router using Massive API.

Provides real-time stock price data including:
- Current price and day's OHLC
- Previous close
- Today's change (absolute and percentage)
- Volume data
"""

import structlog
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional

from ..infrastructure.massive_client import get_massive_client

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])


class DayBar(BaseModel):
    """Daily OHLC data."""
    open: Optional[float] = Field(None, description="Opening price")
    high: Optional[float] = Field(None, description="Day's high")
    low: Optional[float] = Field(None, description="Day's low")
    close: Optional[float] = Field(None, description="Current/closing price")
    volume: Optional[int] = Field(None, description="Trading volume")
    vwap: Optional[float] = Field(None, description="Volume weighted average price")


class MinuteBar(BaseModel):
    """Latest minute bar data."""
    open: Optional[float] = Field(None, description="Minute open")
    high: Optional[float] = Field(None, description="Minute high")
    low: Optional[float] = Field(None, description="Minute low")
    close: Optional[float] = Field(None, description="Minute close")
    volume: Optional[int] = Field(None, description="Minute volume")


class LastTrade(BaseModel):
    """Last trade information."""
    price: Optional[float] = Field(None, description="Trade price")
    size: Optional[int] = Field(None, description="Trade size (shares)")
    timestamp: Optional[int] = Field(None, description="Trade timestamp (Unix ms)")


class StockSnapshotData(BaseModel):
    """Complete stock snapshot data."""
    ticker: str = Field(..., description="Stock ticker symbol")
    name: Optional[str] = Field(None, description="Company name")
    
    # Current price
    price: Optional[float] = Field(None, description="Current/last price")
    
    # Change from previous close
    change: Optional[float] = Field(None, description="Price change")
    change_percent: Optional[float] = Field(None, description="Percent change")
    
    # Previous day
    prev_close: Optional[float] = Field(None, description="Previous close price")
    
    # Day's data
    day: Optional[DayBar] = Field(None, description="Today's OHLC data")
    
    # Latest minute
    minute: Optional[MinuteBar] = Field(None, description="Latest minute bar")
    
    # Last trade
    last_trade: Optional[LastTrade] = Field(None, description="Last trade info")
    
    # Metadata
    updated: Optional[int] = Field(None, description="Last update timestamp")
    market_status: str = Field(default="unknown", description="Market status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "price": 185.92,
                "change": 2.15,
                "change_percent": 1.17,
                "prev_close": 183.77,
                "day": {
                    "open": 184.25,
                    "high": 186.50,
                    "low": 183.80,
                    "close": 185.92,
                    "volume": 45000000,
                    "vwap": 185.35
                },
                "market_status": "open"
            }
        }


class StockSnapshotResponse(BaseModel):
    """Stock snapshot response."""
    success: bool = True
    data: StockSnapshotData
    message: str = "Snapshot retrieved successfully"


class BatchSnapshotResponse(BaseModel):
    """Batch snapshot response for multiple tickers."""
    success: bool = True
    data: List[StockSnapshotData]
    total_count: int
    message: str = "Snapshots retrieved successfully"


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    message: str


def _decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    """Convert Decimal to float safely."""
    if value is None:
        return None
    return float(value)


@router.get(
    "/{ticker}/snapshot",
    response_model=StockSnapshotResponse,
    responses={
        200: {"description": "Snapshot retrieved successfully"},
        404: {"description": "Stock not found", "model": ErrorResponse},
        503: {"description": "Market data unavailable", "model": ErrorResponse},
    },
    summary="Get stock snapshot",
    description="""
    Get current market snapshot for a stock.
    
    Includes:
    - Current price (from latest trade or day close)
    - Today's change and percent change
    - Day's OHLC and volume
    - Previous close
    - Latest minute bar
    
    Data availability:
    - Real-time: Stocks Advanced/Business plans
    - 15-min delayed: Stocks Starter/Developer plans
    - End-of-day: Stocks Basic plan
    """,
)
async def get_stock_snapshot(
    ticker: str,
) -> StockSnapshotResponse:
    """
    Get current market snapshot for a stock.
    
    Returns comprehensive price data including day's range,
    previous close, and change calculations.
    """
    client = get_massive_client()
    
    if not client.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": "service_not_configured",
                "message": "Market data service not configured",
            },
        )
    
    try:
        snapshot = await client.get_snapshot(ticker.upper())
        
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": "stock_not_found",
                    "message": f"No market data found for '{ticker.upper()}'",
                },
            )
        
        # Determine current price (prefer last trade, fall back to day close, minute close, prev close)
        current_price = _decimal_to_float(snapshot.last_trade_price)
        if current_price is None:
            current_price = _decimal_to_float(snapshot.day_close)
        if current_price is None:
            current_price = _decimal_to_float(snapshot.minute_close)
        if current_price is None:
            current_price = _decimal_to_float(snapshot.prev_close)
        
        # Build response
        data = StockSnapshotData(
            ticker=snapshot.ticker,
            name=snapshot.name,
            price=current_price,
            change=_decimal_to_float(snapshot.todays_change),
            change_percent=_decimal_to_float(snapshot.todays_change_percent),
            prev_close=_decimal_to_float(snapshot.prev_close),
            day=DayBar(
                open=_decimal_to_float(snapshot.day_open),
                high=_decimal_to_float(snapshot.day_high),
                low=_decimal_to_float(snapshot.day_low),
                close=_decimal_to_float(snapshot.day_close),
                volume=snapshot.day_volume,
                vwap=_decimal_to_float(snapshot.day_vwap),
            ) if any([snapshot.day_open, snapshot.day_high, snapshot.day_low]) else None,
            minute=MinuteBar(
                open=_decimal_to_float(snapshot.minute_open),
                high=_decimal_to_float(snapshot.minute_high),
                low=_decimal_to_float(snapshot.minute_low),
                close=_decimal_to_float(snapshot.minute_close),
                volume=snapshot.minute_volume,
            ) if snapshot.minute_close else None,
            last_trade=LastTrade(
                price=_decimal_to_float(snapshot.last_trade_price),
                size=snapshot.last_trade_size,
                timestamp=snapshot.last_trade_timestamp,
            ) if snapshot.last_trade_price else None,
            updated=snapshot.updated,
            market_status="open",  # TODO: Determine from market hours
        )
        
        logger.info(
            "Stock snapshot retrieved",
            ticker=ticker.upper(),
            price=current_price,
        )
        
        return StockSnapshotResponse(
            success=True,
            data=data,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Stock snapshot failed", error=str(e), ticker=ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "snapshot_failed",
                "message": f"Failed to get stock snapshot: {str(e)}",
            },
        )


@router.get(
    "/{ticker}/price",
    response_model=dict,
    summary="Get stock price (simplified)",
    description="Get just the current price and change for a stock.",
)
async def get_stock_price(
    ticker: str,
) -> dict:
    """
    Get simplified price data for a stock.
    
    Returns just price, change, and change_percent for quick lookups.
    """
    client = get_massive_client()
    
    if not client.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_not_configured"},
        )
    
    try:
        snapshot = await client.get_snapshot(ticker.upper())
        
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "ticker": ticker.upper()},
            )
        
        # Log all available price fields for debugging
        logger.info(
            "Snapshot data for price lookup",
            ticker=ticker.upper(),
            last_trade_price=snapshot.last_trade_price,
            day_close=snapshot.day_close,
            day_open=snapshot.day_open,
            minute_close=snapshot.minute_close,
            prev_close=snapshot.prev_close,
            todays_change=snapshot.todays_change,
            todays_change_percent=snapshot.todays_change_percent,
        )
        
        # Determine current price with multiple fallbacks
        # Priority: last_trade_price > day_close > minute_close > prev_close
        price = _decimal_to_float(snapshot.last_trade_price)
        if price is None:
            price = _decimal_to_float(snapshot.day_close)
        if price is None:
            price = _decimal_to_float(snapshot.minute_close)
        if price is None:
            price = _decimal_to_float(snapshot.prev_close)
        
        logger.info(
            "Final price determined",
            ticker=ticker.upper(),
            price=price,
        )
        
        return {
            "ticker": snapshot.ticker,
            "price": price,
            "change": _decimal_to_float(snapshot.todays_change),
            "change_percent": _decimal_to_float(snapshot.todays_change_percent),
            "prev_close": _decimal_to_float(snapshot.prev_close),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Stock price fetch failed", error=str(e), ticker=ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "fetch_failed", "message": str(e)},
        )


@router.post(
    "/batch/prices",
    response_model=dict,
    summary="Get prices for multiple stocks",
    description="Get current prices for a batch of tickers (max 50).",
)
async def get_batch_prices(
    tickers: List[str] = Query(
        ...,
        max_length=50,
        description="List of ticker symbols",
    ),
) -> dict:
    """
    Get prices for multiple stocks in a single request.
    
    Returns a map of ticker to price data.
    Useful for watchlist price updates.
    """
    client = get_massive_client()
    
    if not client.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_not_configured"},
        )
    
    if len(tickers) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "too_many_tickers", "message": "Maximum 50 tickers per request"},
        )
    
    results = {}
    errors = []
    
    for ticker in tickers:
        try:
            snapshot = await client.get_snapshot(ticker.upper())
            
            if snapshot:
                # Determine current price with multiple fallbacks
                price = _decimal_to_float(snapshot.last_trade_price)
                if price is None:
                    price = _decimal_to_float(snapshot.day_close)
                if price is None:
                    price = _decimal_to_float(snapshot.prev_close)
                
                results[ticker.upper()] = {
                    "price": price,
                    "change": _decimal_to_float(snapshot.todays_change),
                    "change_percent": _decimal_to_float(snapshot.todays_change_percent),
                }
            else:
                errors.append(ticker.upper())
                
        except Exception as e:
            logger.warning("Batch price fetch failed for ticker", ticker=ticker, error=str(e))
            errors.append(ticker.upper())
    
    return {
        "prices": results,
        "errors": errors,
        "success_count": len(results),
        "error_count": len(errors),
    }
