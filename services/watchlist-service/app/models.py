"""Pydantic models for request/response validation."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WatchlistItem(BaseModel):
    """Watchlist item response model."""

    id: str
    user_id: str
    symbol: str = Field(..., max_length=10, description="Stock ticker symbol")
    alert_enabled: bool = False
    alert_price_above: Optional[float] = None
    alert_price_below: Optional[float] = None
    notes: Optional[str] = Field(None, max_length=500)
    added_at: datetime

    class Config:
        from_attributes = True


class WatchlistCreate(BaseModel):
    """Request model for adding stock to watchlist."""

    symbol: str = Field(..., max_length=10, min_length=1, description="Stock ticker symbol")
    notes: Optional[str] = Field(None, max_length=500, description="Optional notes")
    alert_enabled: bool = Field(default=False, description="Enable price alerts")
    alert_price_above: Optional[float] = Field(None, ge=0, description="Alert when price goes above")
    alert_price_below: Optional[float] = Field(None, ge=0, description="Alert when price goes below")


class WatchlistUpdate(BaseModel):
    """Request model for updating watchlist item."""

    notes: Optional[str] = Field(None, max_length=500)
    alert_enabled: Optional[bool] = None
    alert_price_above: Optional[float] = Field(None, ge=0)
    alert_price_below: Optional[float] = Field(None, ge=0)


class WatchlistResponse(BaseModel):
    """Response model for watchlist list."""

    watchlist: list[WatchlistItem]
    total: int
    tier: str
    limit: int


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str
    error_code: Optional[str] = None
