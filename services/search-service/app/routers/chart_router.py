"""
Chart data router using Massive API.

Provides historical OHLC aggregate data for charting:
- Intraday bars (1min, 5min, 15min, 30min, 1hour)
- Daily, weekly, monthly bars
- Custom date ranges
- Pre-defined ranges (1D, 5D, 1M, 3M, 6M, YTD, 1Y, 5Y)
"""

import structlog
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, HTTPException, Query, Path, status
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

from ..infrastructure.massive_client import get_massive_client, MassiveTimespan

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/charts", tags=["charts"])


class ChartRange(str, Enum):
    """Pre-defined chart time ranges."""
    INTRADAY = "1D"
    FIVE_DAYS = "5D"
    ONE_MONTH = "1M"
    THREE_MONTHS = "3M"
    SIX_MONTHS = "6M"
    YEAR_TO_DATE = "YTD"
    ONE_YEAR = "1Y"
    FIVE_YEARS = "5Y"
    MAX = "MAX"


class ChartInterval(str, Enum):
    """Chart bar intervals."""
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1mo"


class OHLCBar(BaseModel):
    """OHLC bar data point."""
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Closing price")
    volume: int = Field(..., description="Trading volume")
    vwap: Optional[float] = Field(None, description="Volume weighted average price")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": 1704067200000,
                "open": 185.25,
                "high": 186.50,
                "low": 184.80,
                "close": 186.10,
                "volume": 12500000,
                "vwap": 185.75
            }
        }


class ChartMetadata(BaseModel):
    """Chart metadata."""
    ticker: str = Field(..., description="Stock ticker")
    interval: str = Field(..., description="Bar interval")
    range: str = Field(..., description="Time range")
    from_date: str = Field(..., description="Start date")
    to_date: str = Field(..., description="End date")
    bar_count: int = Field(..., description="Number of bars")
    adjusted: bool = Field(default=True, description="Adjusted for splits")


class ChartResponse(BaseModel):
    """Chart data response."""
    success: bool = True
    data: List[OHLCBar]
    metadata: ChartMetadata
    message: str = "Chart data retrieved successfully"


class ErrorResponse(BaseModel):
    """Error response model."""
    success: bool = False
    error: str
    message: str


def _get_range_params(range_type: ChartRange) -> tuple[str, str, MassiveTimespan, int]:
    """
    Get date range and interval parameters for a chart range.
    
    Returns: (from_date, to_date, timespan, multiplier)
    """
    now = datetime.now()
    to_date = now.strftime("%Y-%m-%d")
    
    if range_type == ChartRange.INTRADAY:
        # 1-minute bars for today
        from_date = to_date
        return (from_date, to_date, MassiveTimespan.MINUTE, 5)
    
    elif range_type == ChartRange.FIVE_DAYS:
        # 5-minute bars for 5 days
        from_dt = now - timedelta(days=5)
        return (from_dt.strftime("%Y-%m-%d"), to_date, MassiveTimespan.MINUTE, 15)
    
    elif range_type == ChartRange.ONE_MONTH:
        # 30-minute bars for 1 month
        from_dt = now - timedelta(days=30)
        return (from_dt.strftime("%Y-%m-%d"), to_date, MassiveTimespan.HOUR, 1)
    
    elif range_type == ChartRange.THREE_MONTHS:
        # Daily bars for 3 months
        from_dt = now - timedelta(days=90)
        return (from_dt.strftime("%Y-%m-%d"), to_date, MassiveTimespan.DAY, 1)
    
    elif range_type == ChartRange.SIX_MONTHS:
        # Daily bars for 6 months
        from_dt = now - timedelta(days=180)
        return (from_dt.strftime("%Y-%m-%d"), to_date, MassiveTimespan.DAY, 1)
    
    elif range_type == ChartRange.YEAR_TO_DATE:
        # Daily bars from Jan 1
        from_date = f"{now.year}-01-01"
        return (from_date, to_date, MassiveTimespan.DAY, 1)
    
    elif range_type == ChartRange.ONE_YEAR:
        # Daily bars for 1 year
        from_dt = now - timedelta(days=365)
        return (from_dt.strftime("%Y-%m-%d"), to_date, MassiveTimespan.DAY, 1)
    
    elif range_type == ChartRange.FIVE_YEARS:
        # Weekly bars for 5 years
        from_dt = now - timedelta(days=365 * 5)
        return (from_dt.strftime("%Y-%m-%d"), to_date, MassiveTimespan.WEEK, 1)
    
    elif range_type == ChartRange.MAX:
        # Monthly bars for all history
        from_date = "2003-01-01"  # Massive data starts 2003
        return (from_date, to_date, MassiveTimespan.MONTH, 1)
    
    # Default: 1 month daily
    from_dt = now - timedelta(days=30)
    return (from_dt.strftime("%Y-%m-%d"), to_date, MassiveTimespan.DAY, 1)


def _parse_interval(interval: ChartInterval) -> tuple[MassiveTimespan, int]:
    """Parse chart interval to Massive timespan and multiplier."""
    mapping = {
        ChartInterval.ONE_MINUTE: (MassiveTimespan.MINUTE, 1),
        ChartInterval.FIVE_MINUTES: (MassiveTimespan.MINUTE, 5),
        ChartInterval.FIFTEEN_MINUTES: (MassiveTimespan.MINUTE, 15),
        ChartInterval.THIRTY_MINUTES: (MassiveTimespan.MINUTE, 30),
        ChartInterval.ONE_HOUR: (MassiveTimespan.HOUR, 1),
        ChartInterval.FOUR_HOURS: (MassiveTimespan.HOUR, 4),
        ChartInterval.ONE_DAY: (MassiveTimespan.DAY, 1),
        ChartInterval.ONE_WEEK: (MassiveTimespan.WEEK, 1),
        ChartInterval.ONE_MONTH: (MassiveTimespan.MONTH, 1),
    }
    return mapping.get(interval, (MassiveTimespan.DAY, 1))


def _decimal_to_float(value: Optional[Decimal]) -> float:
    """Convert Decimal to float safely."""
    if value is None:
        return 0.0
    return float(value)


@router.get(
    "/{ticker}",
    response_model=ChartResponse,
    responses={
        200: {"description": "Chart data retrieved successfully"},
        404: {"description": "No data found for ticker", "model": ErrorResponse},
        503: {"description": "Chart service unavailable", "model": ErrorResponse},
    },
    summary="Get chart data for a stock",
    description="""
    Get historical OHLC data for charting.
    
    Pre-defined ranges:
    - 1D: Intraday 5-minute bars
    - 5D: 5-day 15-minute bars
    - 1M: 1-month hourly bars
    - 3M, 6M: Daily bars
    - YTD: Year-to-date daily bars
    - 1Y: 1-year daily bars
    - 5Y: 5-year weekly bars
    - MAX: All history monthly bars
    
    Or specify custom date range with interval.
    """,
)
async def get_chart_data(
    ticker: str = Path(..., description="Stock ticker symbol"),
    range: ChartRange = Query(
        default=ChartRange.ONE_MONTH,
        description="Pre-defined time range",
    ),
    adjusted: bool = Query(
        default=True,
        description="Adjust prices for splits",
    ),
) -> ChartResponse:
    """
    Get chart data for a stock with pre-defined range.
    
    Returns OHLC bars optimized for the selected time range.
    """
    client = get_massive_client()
    
    if not client.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": "service_not_configured",
                "message": "Chart service not configured",
            },
        )
    
    try:
        from_date, to_date, timespan, multiplier = _get_range_params(range)
        
        bars = await client.get_aggregates(
            ticker=ticker.upper(),
            multiplier=multiplier,
            timespan=timespan,
            from_date=from_date,
            to_date=to_date,
            adjusted=adjusted,
        )
        
        if not bars:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": "no_data",
                    "message": f"No chart data found for '{ticker.upper()}' in range {range.value}",
                },
            )
        
        # Convert to response format
        data = [
            OHLCBar(
                timestamp=bar.timestamp,
                open=_decimal_to_float(bar.open),
                high=_decimal_to_float(bar.high),
                low=_decimal_to_float(bar.low),
                close=_decimal_to_float(bar.close),
                volume=bar.volume,
                vwap=_decimal_to_float(bar.vwap) if bar.vwap else None,
            )
            for bar in bars
        ]
        
        interval_str = f"{multiplier}{timespan.value[0]}"  # e.g., "1d", "5m"
        
        logger.info(
            "Chart data retrieved",
            ticker=ticker.upper(),
            range=range.value,
            bars=len(data),
        )
        
        return ChartResponse(
            success=True,
            data=data,
            metadata=ChartMetadata(
                ticker=ticker.upper(),
                interval=interval_str,
                range=range.value,
                from_date=from_date,
                to_date=to_date,
                bar_count=len(data),
                adjusted=adjusted,
            ),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chart data fetch failed", error=str(e), ticker=ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "fetch_failed",
                "message": f"Failed to get chart data: {str(e)}",
            },
        )


@router.get(
    "/{ticker}/custom",
    response_model=ChartResponse,
    summary="Get chart data with custom parameters",
    description="Get chart data with custom date range and interval.",
)
async def get_custom_chart_data(
    ticker: str = Path(..., description="Stock ticker symbol"),
    interval: ChartInterval = Query(
        default=ChartInterval.ONE_DAY,
        description="Bar interval",
    ),
    from_date: str = Query(
        ...,
        description="Start date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    to_date: str = Query(
        ...,
        description="End date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    adjusted: bool = Query(
        default=True,
        description="Adjust prices for splits",
    ),
    limit: int = Query(
        default=5000,
        ge=1,
        le=50000,
        description="Maximum bars to return",
    ),
) -> ChartResponse:
    """
    Get chart data with custom date range and interval.
    
    Allows full control over date range and bar interval.
    """
    client = get_massive_client()
    
    if not client.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "success": False,
                "error": "service_not_configured",
                "message": "Chart service not configured",
            },
        )
    
    try:
        timespan, multiplier = _parse_interval(interval)
        
        bars = await client.get_aggregates(
            ticker=ticker.upper(),
            multiplier=multiplier,
            timespan=timespan,
            from_date=from_date,
            to_date=to_date,
            adjusted=adjusted,
            limit=limit,
        )
        
        if not bars:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": "no_data",
                    "message": f"No chart data found for '{ticker.upper()}'",
                },
            )
        
        data = [
            OHLCBar(
                timestamp=bar.timestamp,
                open=_decimal_to_float(bar.open),
                high=_decimal_to_float(bar.high),
                low=_decimal_to_float(bar.low),
                close=_decimal_to_float(bar.close),
                volume=bar.volume,
                vwap=_decimal_to_float(bar.vwap) if bar.vwap else None,
            )
            for bar in bars
        ]
        
        logger.info(
            "Custom chart data retrieved",
            ticker=ticker.upper(),
            interval=interval.value,
            from_date=from_date,
            to_date=to_date,
            bars=len(data),
        )
        
        return ChartResponse(
            success=True,
            data=data,
            metadata=ChartMetadata(
                ticker=ticker.upper(),
                interval=interval.value,
                range="custom",
                from_date=from_date,
                to_date=to_date,
                bar_count=len(data),
                adjusted=adjusted,
            ),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Custom chart data fetch failed", error=str(e), ticker=ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "fetch_failed",
                "message": f"Failed to get chart data: {str(e)}",
            },
        )


@router.get(
    "/{ticker}/previous",
    response_model=dict,
    summary="Get previous day's bar",
    description="Get the previous trading day's OHLC data.",
)
async def get_previous_close(
    ticker: str = Path(..., description="Stock ticker symbol"),
    adjusted: bool = Query(default=True, description="Adjust for splits"),
) -> dict:
    """Get previous trading day's OHLC bar."""
    client = get_massive_client()
    
    if not client.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_not_configured"},
        )
    
    try:
        bar = await client.get_previous_close(ticker.upper(), adjusted=adjusted)
        
        if not bar:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "not_found", "ticker": ticker.upper()},
            )
        
        return {
            "ticker": ticker.upper(),
            "timestamp": bar.timestamp,
            "open": _decimal_to_float(bar.open),
            "high": _decimal_to_float(bar.high),
            "low": _decimal_to_float(bar.low),
            "close": _decimal_to_float(bar.close),
            "volume": bar.volume,
            "vwap": _decimal_to_float(bar.vwap) if bar.vwap else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Previous close fetch failed", error=str(e), ticker=ticker)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "fetch_failed", "message": str(e)},
        )
