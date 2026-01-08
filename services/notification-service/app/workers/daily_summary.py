"""
Daily summary worker for sending morning stock news emails.

Sends daily email summaries to users with their watchlist stocks,
current prices, and latest news headlines.
"""

import asyncio
import aiohttp
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.config import settings
from app.database import db
from app.channels.email import ResendEmailChannel
from app.models import (
    NotificationType,
    StockQuote,
    StockNews,
    StockSummaryData,
    DailySummaryData,
)
from app.metrics import (
    record_email_sent,
    record_failure,
)

logger = structlog.get_logger()


class NewsCache:
    """Simple in-memory cache for news data with TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if datetime.utcnow() > entry["expires_at"]:
            del self._cache[key]
            return None

        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """Set cached value with TTL."""
        self._cache[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(seconds=self._ttl),
        }

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()


class DailySummaryWorker:
    """Background worker to send daily stock summary emails."""

    def __init__(self):
        self.email_channel = ResendEmailChannel()
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.news_cache = NewsCache(ttl_seconds=settings.NEWS_CACHE_TTL_SECONDS)

    async def start(self) -> None:
        """Start the daily summary worker."""
        if self.running:
            logger.warning("Daily summary worker already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info(
            "Daily summary worker started",
            send_hour=settings.DAILY_SUMMARY_SEND_HOUR,
        )

    async def stop(self) -> None:
        """Stop the daily summary worker."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Daily summary worker stopped")

    async def _run_scheduler(self) -> None:
        """Run scheduled daily summary sends."""
        while self.running:
            try:
                now = datetime.utcnow()
                target_hour = settings.DAILY_SUMMARY_SEND_HOUR

                if now.hour == target_hour and now.minute < 5:
                    logger.info(
                        "Running daily summary job",
                        hour=target_hour,
                        timestamp=now.isoformat(),
                    )
                    await self._send_daily_summaries()
                    await asyncio.sleep(300)
                else:
                    next_run = self._calculate_next_run(now, target_hour)
                    sleep_seconds = (next_run - now).total_seconds()
                    logger.info(
                        "Waiting for next daily summary run",
                        next_run=next_run.isoformat(),
                        sleep_seconds=sleep_seconds,
                    )
                    await asyncio.sleep(min(sleep_seconds, 3600))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in daily summary scheduler", error=str(e))
                await asyncio.sleep(60)

    def _calculate_next_run(self, now: datetime, target_hour: int) -> datetime:
        """Calculate next run time."""
        next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)

        if next_run <= now:
            next_run += timedelta(days=1)

        return next_run

    async def _send_daily_summaries(self) -> None:
        """Send daily summaries to all eligible users."""
        try:
            users = await self._get_eligible_users()
            logger.info("Sending daily summaries", user_count=len(users))

            sent_count = 0
            error_count = 0

            for user_data in users:
                try:
                    await self._process_user_summary(user_data)
                    sent_count += 1
                    await asyncio.sleep(settings.API_REQUEST_DELAY_MS / 1000)
                except Exception as e:
                    error_count += 1
                    logger.error(
                        "Failed to send daily summary",
                        user_id=str(user_data["user_id"]),
                        error=str(e),
                    )
                    record_failure(NotificationType.DAILY_SUMMARY, "send_failed")

            self.news_cache.clear()

            logger.info(
                "Daily summaries completed",
                sent=sent_count,
                errors=error_count,
            )

        except Exception as e:
            logger.error("Failed to send daily summaries", error=str(e))
            record_failure(NotificationType.DAILY_SUMMARY, "job_failed")

    async def _get_eligible_users(self) -> List[Dict[str, Any]]:
        """Get users who have stock_news notifications enabled."""
        query = """
            SELECT DISTINCT
                u.id as user_id,
                u.email,
                up.full_name,
                up.notification_preferences
            FROM auth.users u
            JOIN public.watchlists w ON w.user_id = u.id
            LEFT JOIN public.user_profiles up ON up.id = u.id
            WHERE u.email IS NOT NULL
        """

        rows = await db.fetch(query)

        results = []
        for row in rows:
            prefs = row["notification_preferences"] or {}
            if isinstance(prefs, str):
                import json
                prefs = json.loads(prefs)

            if not prefs.get("email_notifications", True):
                continue

            if not prefs.get("stock_news", True):
                continue

            results.append({
                "user_id": row["user_id"],
                "email": row["email"],
                "full_name": row["full_name"],
            })

        return results

    async def _process_user_summary(self, user_data: Dict[str, Any]) -> None:
        """Process and send daily summary for a single user."""
        user_id = user_data["user_id"]
        email = user_data["email"]
        full_name = user_data.get("full_name")

        watchlist_symbols = await self._get_user_watchlist(user_id)

        if not watchlist_symbols:
            logger.debug(
                "User has no watchlist items",
                user_id=str(user_id),
            )
            return

        stocks_data: List[StockSummaryData] = []

        for symbol in watchlist_symbols:
            try:
                quote = await self._fetch_stock_quote(symbol)
                news = await self._fetch_stock_news(symbol)

                stocks_data.append(StockSummaryData(
                    symbol=symbol,
                    quote=quote,
                    news=news,
                ))

                await asyncio.sleep(settings.API_REQUEST_DELAY_MS / 1000)

            except Exception as e:
                logger.warning(
                    "Failed to fetch data for symbol",
                    symbol=symbol,
                    error=str(e),
                )
                stocks_data.append(StockSummaryData(symbol=symbol))

        summary_data = DailySummaryData(
            user_email=email,
            user_name=full_name,
            stocks=stocks_data,
            summary_date=datetime.utcnow().strftime("%B %d, %Y"),
        )

        await self._send_summary_email(user_id, summary_data)

    async def _get_user_watchlist(self, user_id: UUID) -> List[str]:
        """Get watchlist symbols for a user."""
        query = """
            SELECT symbol
            FROM public.watchlists
            WHERE user_id = $1
            ORDER BY added_at DESC
            LIMIT 20
        """

        rows = await db.fetch(query, user_id)
        return [row["symbol"] for row in rows]

    async def _fetch_stock_quote(self, symbol: str) -> Optional[StockQuote]:
        """Fetch current stock quote from search service."""
        try:
            async with aiohttp.ClientSession() as session:
                # Use the search endpoint which returns stock data
                url = f"{settings.SEARCH_SERVICE_URL}/api/v1/search"
                params = {"query": symbol}
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(
                            "Failed to fetch quote",
                            symbol=symbol,
                            status=response.status,
                        )
                        return None

                    data = await response.json()
                    
                    # Extract price data from the search response
                    stock_data = data.get("data", {})
                    price_data = stock_data.get("price", {})
                    
                    if not price_data:
                        logger.warning("No price data in response", symbol=symbol)
                        return None

                    return StockQuote(
                        symbol=symbol,
                        current_price=price_data.get("current", 0),
                        change=price_data.get("change_absolute", 0),
                        change_percent=price_data.get("change_percent", 0),
                        volume=price_data.get("volume"),
                    )

        except asyncio.TimeoutError:
            logger.warning("Quote fetch timeout", symbol=symbol)
            return None
        except Exception as e:
            logger.warning("Quote fetch error", symbol=symbol, error=str(e))
            return None

    async def _fetch_stock_news(self, symbol: str) -> List[StockNews]:
        """Fetch stock news from search service with caching."""
        cache_key = f"news:{symbol}"
        cached = self.news_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{settings.SEARCH_SERVICE_URL}/api/v1/stocks/{symbol}/news"
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(
                            "Failed to fetch news",
                            symbol=symbol,
                            status=response.status,
                        )
                        return []

                    data = await response.json()
                    news_items = data.get("news", data) if isinstance(data, dict) else data

                    if not isinstance(news_items, list):
                        news_items = []

                    result = []
                    for item in news_items[:3]:
                        result.append(StockNews(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            summary=item.get("summary"),
                            source=item.get("source"),
                            published_at=item.get("published_at"),
                        ))

                    self.news_cache.set(cache_key, result)
                    return result

        except asyncio.TimeoutError:
            logger.warning("News fetch timeout", symbol=symbol)
            return []
        except Exception as e:
            logger.warning("News fetch error", symbol=symbol, error=str(e))
            return []

    async def _send_summary_email(
        self,
        user_id: UUID,
        summary_data: DailySummaryData,
    ) -> None:
        """Send the daily summary email."""
        template_data = {
            "user_name": summary_data.user_name,
            "summary_date": summary_data.summary_date,
            "stocks": [
                {
                    "symbol": s.symbol,
                    "quote": {
                        "current_price": s.quote.current_price,
                        "change": s.quote.change,
                        "change_percent": s.quote.change_percent,
                    } if s.quote else None,
                    "news": [
                        {
                            "title": n.title,
                            "url": n.url,
                            "source": n.source,
                            "published_at": n.published_at,
                        }
                        for n in s.news
                    ],
                }
                for s in summary_data.stocks
            ],
        }

        success = await self.email_channel.send_daily_summary(
            recipient=summary_data.user_email,
            template_data=template_data,
        )

        if success:
            record_email_sent(NotificationType.DAILY_SUMMARY)
            await self._log_notification(user_id, summary_data)
            logger.info(
                "Daily summary sent",
                user_id=str(user_id),
                email=summary_data.user_email,
                stock_count=len(summary_data.stocks),
            )
        else:
            record_failure(NotificationType.DAILY_SUMMARY, "email_send_failed")
            logger.error(
                "Failed to send daily summary email",
                user_id=str(user_id),
                email=summary_data.user_email,
            )

    async def _log_notification(
        self,
        user_id: UUID,
        summary_data: DailySummaryData,
    ) -> None:
        """Log notification to history table."""
        query = """
            INSERT INTO public.notification_history (
                user_id,
                notification_type,
                delivery_status,
                metadata
            ) VALUES ($1, $2, $3, $4)
        """

        metadata = {
            "stocks": [s.symbol for s in summary_data.stocks],
            "email": summary_data.user_email,
            "summary_date": summary_data.summary_date,
        }

        try:
            import json
            await db.execute(
                query,
                user_id,
                NotificationType.DAILY_SUMMARY.value,
                "sent",
                json.dumps(metadata),
            )
        except Exception as e:
            logger.warning(
                "Failed to log notification",
                user_id=str(user_id),
                error=str(e),
            )


daily_summary_worker = DailySummaryWorker()
