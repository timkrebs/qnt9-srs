import asyncio
import aiohttp
import structlog
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.config import settings
from app.database import db
from app.channels.email import ResendEmailChannel
from app.models import NotificationType, AlertDirection
from app.metrics import (
    record_email_sent,
    record_price_alert,
    record_failure,
    active_price_alerts,
    watchlist_items_checked_total,
    MetricsTracker,
)

logger = structlog.get_logger()


class PriceMonitorWorker:
    """Background worker to monitor watchlist price alerts."""

    def __init__(self):
        self.email_channel = ResendEmailChannel()
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the price monitoring worker."""
        if self.running:
            logger.warning("Price monitor already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Price monitor worker started")

    async def stop(self):
        """Stop the price monitoring worker."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Price monitor worker stopped")

    async def _run_scheduler(self):
        """Run scheduled price checks."""
        while self.running:
            try:
                now = datetime.now()
                target_hour = settings.PRICE_ALERT_SEND_HOUR

                if now.hour == target_hour and now.minute < 5:
                    logger.info("Running daily price alert check", hour=target_hour)
                    await self._check_price_alerts()

                    await asyncio.sleep(300)
                else:
                    next_run = self._calculate_next_run(now, target_hour)
                    sleep_seconds = (next_run - now).total_seconds()
                    logger.info(
                        "Waiting for next price check",
                        next_run=next_run.isoformat(),
                        sleep_seconds=sleep_seconds,
                    )
                    await asyncio.sleep(min(sleep_seconds, 3600))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in price monitor scheduler", error=str(e))
                await asyncio.sleep(60)

    def _calculate_next_run(self, now: datetime, target_hour: int) -> datetime:
        """Calculate next run time."""
        next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)

        if next_run <= now:
            next_run += timedelta(days=1)

        return next_run

    async def _check_price_alerts(self):
        """Check all active price alerts and send notifications."""
        try:
            watchlist_items = await self._get_active_alerts()
            active_price_alerts.set(len(watchlist_items))

            logger.info("Checking price alerts", count=len(watchlist_items))

            for item in watchlist_items:
                watchlist_items_checked_total.inc()
                try:
                    await self._process_alert(item)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(
                        "Failed to process alert",
                        symbol=item["symbol"],
                        user_id=str(item["user_id"]),
                        error=str(e),
                    )
                    record_failure(NotificationType.PRICE_ALERT, "processing_error")

            logger.info("Price alert check completed", processed=len(watchlist_items))

        except Exception as e:
            logger.error("Failed to check price alerts", error=str(e))
            record_failure(NotificationType.PRICE_ALERT, "check_failed")

    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all watchlist items with active alerts."""
        query = """
            SELECT 
                w.id,
                w.user_id,
                w.symbol,
                w.alert_price_above,
                w.alert_price_below,
                u.email,
                up.notification_preferences
            FROM public.watchlists w
            JOIN auth.users u ON w.user_id = u.id
            LEFT JOIN public.user_profiles up ON w.user_id = up.id
            WHERE w.alert_enabled = true
            AND u.email IS NOT NULL
        """

        rows = await db.fetch(query)

        results = []
        for row in rows:
            prefs = row["notification_preferences"] or {}
            if isinstance(prefs, str):
                import json

                prefs = json.loads(prefs)

            if prefs.get("usage_alerts", True):
                results.append(
                    {
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "symbol": row["symbol"],
                        "alert_price_above": row["alert_price_above"],
                        "alert_price_below": row["alert_price_below"],
                        "email": row["email"],
                    }
                )

        return results

    async def _process_alert(self, item: Dict[str, Any]):
        """Process a single watchlist alert."""
        symbol = item["symbol"]
        user_id = item["user_id"]
        email = item["email"]

        if await self._is_in_cooldown(user_id, symbol):
            logger.debug("Alert in cooldown period", symbol=symbol, user_id=str(user_id))
            return

        current_price = await self._fetch_current_price(symbol)
        if current_price is None:
            logger.warning("Failed to fetch price", symbol=symbol)
            record_failure(NotificationType.PRICE_ALERT, "price_fetch_failed")
            return

        triggered = False
        direction = None

        if item["alert_price_above"] and current_price > float(item["alert_price_above"]):
            triggered = True
            direction = AlertDirection.ABOVE
            threshold = float(item["alert_price_above"])

        elif item["alert_price_below"] and current_price < float(item["alert_price_below"]):
            triggered = True
            direction = AlertDirection.BELOW
            threshold = float(item["alert_price_below"])

        if triggered:
            await self._send_price_alert(
                symbol=symbol,
                current_price=current_price,
                threshold_price=threshold,
                direction=direction,
                user_id=user_id,
                email=email,
            )

    async def _is_in_cooldown(self, user_id: UUID, symbol: str) -> bool:
        """Check if alert is in cooldown period."""
        cooldown_hours = settings.ALERT_COOLDOWN_HOURS
        cutoff_time = datetime.now() - timedelta(hours=cooldown_hours)

        query = """
            SELECT COUNT(*) as count
            FROM public.notification_history
            WHERE user_id = $1
            AND notification_type = $2
            AND metadata->>'symbol' = $3
            AND sent_at > $4
        """

        count = await db.fetchval(
            query, user_id, NotificationType.PRICE_ALERT.value, symbol, cutoff_time
        )

        return count > 0

    async def _fetch_current_price(self, symbol: str) -> Optional[float]:
        """Fetch current stock price from search service."""
        try:
            url = f"{settings.SEARCH_SERVICE_URL}/api/v1/search/{symbol}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get("current_price")
                        if price:
                            return float(price)

            logger.warning("No price data available", symbol=symbol)
            return None

        except Exception as e:
            logger.error("Failed to fetch price", symbol=symbol, error=str(e))
            return None

    async def _send_price_alert(
        self,
        symbol: str,
        current_price: float,
        threshold_price: float,
        direction: AlertDirection,
        user_id: UUID,
        email: str,
    ):
        """Send price alert notification."""
        try:
            user_query = """
                SELECT raw_user_meta_data->>'full_name' as full_name
                FROM auth.users
                WHERE id = $1
            """
            user_data = await db.fetchrow(user_query, user_id)
            user_name = user_data["full_name"] if user_data else None

            email_data = {
                "symbol": symbol,
                "current_price": current_price,
                "threshold_price": threshold_price,
                "direction": direction.value,
                "user_name": user_name,
            }

            with MetricsTracker(NotificationType.PRICE_ALERT):
                status, resend_id = await self.email_channel.send(
                    recipient=email, notification_type=NotificationType.PRICE_ALERT, data=email_data
                )

            success = status.value in ["sent", "delivered"]
            record_email_sent(NotificationType.PRICE_ALERT, success)
            record_price_alert(symbol, direction.value)

            import json

            metadata = {
                "symbol": symbol,
                "current_price": current_price,
                "threshold_price": threshold_price,
                "direction": direction.value,
            }

            insert_query = """
                INSERT INTO public.notification_history 
                (user_id, notification_type, sent_at, delivery_status, resend_id, metadata)
                VALUES ($1, $2, NOW(), $3, $4, $5::jsonb)
            """

            await db.execute(
                insert_query,
                user_id,
                NotificationType.PRICE_ALERT.value,
                status.value,
                resend_id,
                json.dumps(metadata),
            )

            logger.info(
                "Price alert sent",
                symbol=symbol,
                user_id=str(user_id),
                direction=direction.value,
                status=status.value,
            )

        except Exception as e:
            logger.error(
                "Failed to send price alert",
                symbol=symbol,
                user_id=str(user_id),
                error=str(e),
            )
            record_failure(NotificationType.PRICE_ALERT, "send_failed")
