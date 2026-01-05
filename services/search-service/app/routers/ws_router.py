"""
WebSocket router for real-time stock price streaming.

Proxies Massive WebSocket API to provide live price updates
to frontend clients. Supports subscription management and
broadcasts price updates to connected clients.

WebSocket Endpoints:
- Real-time: wss://socket.massive.com/stocks (Advanced/Business plans)
- 15-min delayed: wss://delayed.massive.com/stocks (Starter/Developer plans)
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class MessageType(str, Enum):
    """WebSocket message types."""
    AUTH = "auth"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    TRADE = "T"
    QUOTE = "Q"
    AGGREGATE = "AM"
    STATUS = "status"
    ERROR = "error"


@dataclass
class PriceUpdate:
    """Real-time price update from Massive."""
    ticker: str
    price: float
    size: int
    timestamp: int
    event_type: str  # T=trade, Q=quote, AM=aggregate


@dataclass
class ClientConnection:
    """Represents a connected WebSocket client."""
    websocket: WebSocket
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.now)


class MassiveWebSocketManager:
    """
    Manages WebSocket connections to Polygon.io API and client broadcasts.
    
    Features:
    - Single upstream connection to Polygon (shared across clients)
    - Client subscription management
    - Automatic reconnection on disconnect
    - Message filtering by subscription
    """
    
    # Polygon.io WebSocket URLs (Massive API uses Polygon infrastructure)
    REALTIME_URL = "wss://socket.polygon.io/stocks"
    DELAYED_URL = "wss://delayed.polygon.io/stocks"
    
    def __init__(self, use_realtime: bool = False):
        """
        Initialize WebSocket manager.
        
        Args:
            use_realtime: Use real-time feed (requires Advanced/Business plan)
        """
        self.api_key = os.getenv("MASSIVE_API_KEY")
        self.ws_url = self.REALTIME_URL if use_realtime else self.DELAYED_URL
        
        # Connected clients
        self.clients: Dict[str, ClientConnection] = {}
        
        # All subscribed tickers (union of all client subscriptions)
        self.active_subscriptions: Set[str] = set()
        
        # Upstream Massive connection
        self._upstream_ws: Optional[websockets.WebSocketClientProtocol] = None
        self._upstream_task: Optional[asyncio.Task] = None
        self._reconnect_delay = 1
        self._max_reconnect_delay = 60
        
        # Connection state
        self._is_connected = False
        self._is_shutting_down = False

    async def connect_client(self, client_id: str, websocket: WebSocket) -> None:
        """
        Register a new client connection.
        
        Args:
            client_id: Unique client identifier
            websocket: FastAPI WebSocket connection
        """
        await websocket.accept()
        self.clients[client_id] = ClientConnection(websocket=websocket)
        logger.info(f"Client connected: {client_id}, total clients: {len(self.clients)}")
        
        # Send welcome message
        await self._send_to_client(client_id, {
            "type": "status",
            "message": "connected",
            "timestamp": datetime.now().isoformat(),
        })
        
        # Start upstream connection if this is first client
        if len(self.clients) == 1 and self.api_key:
            await self._start_upstream_connection()

    async def disconnect_client(self, client_id: str) -> None:
        """
        Remove a client connection.
        
        Args:
            client_id: Client to disconnect
        """
        if client_id in self.clients:
            client = self.clients[client_id]
            
            # Remove client's subscriptions
            for ticker in client.subscriptions:
                await self._update_upstream_subscription(ticker, subscribe=False)
            
            del self.clients[client_id]
            logger.info(f"Client disconnected: {client_id}, remaining: {len(self.clients)}")
        
        # Stop upstream if no clients
        if not self.clients:
            await self._stop_upstream_connection()

    async def subscribe(self, client_id: str, tickers: List[str]) -> None:
        """
        Subscribe a client to ticker updates.
        
        Args:
            client_id: Client ID
            tickers: List of ticker symbols to subscribe to
        """
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        for ticker in tickers:
            ticker_upper = ticker.upper()
            client.subscriptions.add(ticker_upper)
            
            # Add to upstream if not already subscribed
            if ticker_upper not in self.active_subscriptions:
                await self._update_upstream_subscription(ticker_upper, subscribe=True)
        
        logger.info(f"Client {client_id} subscribed to: {tickers}")
        
        await self._send_to_client(client_id, {
            "type": "subscribed",
            "tickers": list(client.subscriptions),
        })

    async def unsubscribe(self, client_id: str, tickers: List[str]) -> None:
        """
        Unsubscribe a client from ticker updates.
        
        Args:
            client_id: Client ID
            tickers: List of tickers to unsubscribe from
        """
        if client_id not in self.clients:
            return
        
        client = self.clients[client_id]
        
        for ticker in tickers:
            ticker_upper = ticker.upper()
            client.subscriptions.discard(ticker_upper)
            
            # Check if any other client needs this ticker
            still_needed = any(
                ticker_upper in c.subscriptions 
                for cid, c in self.clients.items() 
                if cid != client_id
            )
            
            if not still_needed:
                await self._update_upstream_subscription(ticker_upper, subscribe=False)
        
        logger.info(f"Client {client_id} unsubscribed from: {tickers}")

    async def broadcast_price(self, update: PriceUpdate) -> None:
        """
        Broadcast price update to subscribed clients.
        
        Args:
            update: Price update to broadcast
        """
        message = {
            "type": "price",
            "ticker": update.ticker,
            "price": update.price,
            "size": update.size,
            "timestamp": update.timestamp,
            "event": update.event_type,
        }
        
        # Send to clients subscribed to this ticker
        for client_id, client in list(self.clients.items()):
            if update.ticker in client.subscriptions:
                try:
                    await client.websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to client {client_id}: {e}")

    async def _send_to_client(self, client_id: str, message: dict) -> None:
        """Send message to a specific client."""
        if client_id in self.clients:
            try:
                await self.clients[client_id].websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client {client_id}: {e}")

    async def _start_upstream_connection(self) -> None:
        """Start connection to Massive WebSocket."""
        if self._upstream_task is not None:
            return
        
        self._is_shutting_down = False
        self._upstream_task = asyncio.create_task(self._upstream_loop())
        logger.info("Started upstream WebSocket connection task")

    async def _stop_upstream_connection(self) -> None:
        """Stop upstream connection."""
        self._is_shutting_down = True
        
        if self._upstream_ws:
            await self._upstream_ws.close()
            self._upstream_ws = None
        
        if self._upstream_task:
            self._upstream_task.cancel()
            try:
                await self._upstream_task
            except asyncio.CancelledError:
                pass
            self._upstream_task = None
        
        self.active_subscriptions.clear()
        logger.info("Stopped upstream WebSocket connection")

    async def _upstream_loop(self) -> None:
        """Main loop for upstream Massive connection."""
        while not self._is_shutting_down:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self._upstream_ws = ws
                    self._is_connected = True
                    self._reconnect_delay = 1
                    
                    logger.info(f"Connected to Massive WebSocket: {self.ws_url}")
                    
                    # Authenticate
                    await self._authenticate()
                    
                    # Re-subscribe to all active tickers
                    if self.active_subscriptions:
                        await self._send_upstream({
                            "action": "subscribe",
                            "params": ",".join(f"T.{t}" for t in self.active_subscriptions),
                        })
                    
                    # Process incoming messages
                    async for message in ws:
                        await self._process_upstream_message(message)
                        
            except ConnectionClosed as e:
                logger.warning(f"Upstream connection closed: {e}")
            except Exception as e:
                logger.error(f"Upstream connection error: {e}")
            finally:
                self._is_connected = False
                self._upstream_ws = None
            
            # Reconnect with backoff
            if not self._is_shutting_down:
                logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self._max_reconnect_delay
                )

    async def _authenticate(self) -> None:
        """Authenticate with Massive WebSocket."""
        if not self.api_key:
            logger.error("No API key configured for WebSocket auth")
            return
        
        await self._send_upstream({
            "action": "auth",
            "params": self.api_key,
        })
        logger.info("Sent authentication to Massive")

    async def _send_upstream(self, message: dict) -> None:
        """Send message to upstream Massive WebSocket."""
        if self._upstream_ws and self._is_connected:
            await self._upstream_ws.send(json.dumps(message))

    async def _update_upstream_subscription(self, ticker: str, subscribe: bool) -> None:
        """Update upstream subscription for a ticker."""
        if subscribe:
            self.active_subscriptions.add(ticker)
            action = "subscribe"
        else:
            self.active_subscriptions.discard(ticker)
            action = "unsubscribe"
        
        if self._is_connected:
            await self._send_upstream({
                "action": action,
                "params": f"T.{ticker}",  # Trade events
            })
            logger.debug(f"Upstream {action}: T.{ticker}")

    async def _process_upstream_message(self, raw_message: str) -> None:
        """Process message from Polygon.io WebSocket."""
        try:
            data = json.loads(raw_message)
            logger.debug(f"Received upstream message: {raw_message[:200]}")
            
            # Handle different message formats
            if isinstance(data, list):
                # Array of events (Polygon.io format)
                for event in data:
                    await self._process_event(event)
            elif isinstance(data, dict):
                # Single event or status
                await self._process_event(data)
                    
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON from upstream: {e}")
        except Exception as e:
            logger.error(f"Error processing upstream message: {e}")

    async def _process_event(self, event: dict) -> None:
        """Process a single event from Polygon.io."""
        event_type = event.get("ev")
        status = event.get("status")
        message = event.get("message", "")
        
        # Handle status messages
        if event_type == "status" or status:
            status_value = status or message
            if status_value in ("connected", "auth_success", "success"):
                logger.info(f"Polygon.io WebSocket: {status_value} - {message}")
                return
            elif "not authorized" in str(message).lower():
                # Subscription not authorized - plan limitation
                logger.warning(f"Polygon.io subscription not authorized: {message}")
                # Notify all clients that real-time data isn't available
                await self._notify_clients_no_realtime()
                return
            elif status_value == "error" or "error" in str(message).lower():
                logger.error(f"Polygon.io error: {message or event}")
                return
            else:
                logger.info(f"Polygon.io status: {event}")
                return
        
        if event_type == "T":  # Trade
            update = PriceUpdate(
                ticker=event.get("sym", ""),
                price=event.get("p", 0),
                size=event.get("s", 0),
                timestamp=event.get("t", 0),
                event_type="trade",
            )
            await self.broadcast_price(update)
            
        elif event_type == "AM":  # Aggregate minute bar
            update = PriceUpdate(
                ticker=event.get("sym", ""),
                price=event.get("c", 0),  # Close price
                size=event.get("v", 0),   # Volume
                timestamp=event.get("e", 0),  # End timestamp
                event_type="aggregate",
            )
            await self.broadcast_price(update)

    async def _notify_clients_no_realtime(self) -> None:
        """Notify all clients that real-time streaming isn't available."""
        message = {
            "type": "status",
            "status": "limited",
            "message": "Real-time streaming not available on current plan. Using REST API for price updates.",
        }
        for client_id, client in list(self.clients.items()):
            try:
                await client.websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to notify client {client_id}: {e}")


# Singleton manager instance
_ws_manager: Optional[MassiveWebSocketManager] = None


def get_ws_manager() -> MassiveWebSocketManager:
    """Get singleton WebSocket manager."""
    global _ws_manager
    if _ws_manager is None:
        use_realtime = os.getenv("MASSIVE_USE_REALTIME", "false").lower() == "true"
        _ws_manager = MassiveWebSocketManager(use_realtime=use_realtime)
    return _ws_manager


@router.websocket("/ws/prices")
async def websocket_prices(
    websocket: WebSocket,
    tickers: Optional[str] = Query(
        default=None,
        description="Comma-separated list of tickers to subscribe to",
    ),
):
    """
    WebSocket endpoint for real-time price updates.
    
    Connect and optionally provide initial tickers to subscribe to.
    After connection, send JSON messages to manage subscriptions:
    
    Subscribe:
    ```json
    {"action": "subscribe", "tickers": ["AAPL", "MSFT"]}
    ```
    
    Unsubscribe:
    ```json
    {"action": "unsubscribe", "tickers": ["AAPL"]}
    ```
    
    Price updates are sent as:
    ```json
    {
        "type": "price",
        "ticker": "AAPL",
        "price": 185.92,
        "size": 100,
        "timestamp": 1704067200000,
        "event": "trade"
    }
    ```
    """
    manager = get_ws_manager()
    
    # Generate unique client ID
    client_id = f"{websocket.client.host}:{websocket.client.port}:{id(websocket)}"
    
    try:
        # Connect client
        await manager.connect_client(client_id, websocket)
        
        # Subscribe to initial tickers if provided
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
            if ticker_list:
                await manager.subscribe(client_id, ticker_list)
        
        # Process client messages
        while True:
            try:
                data = await websocket.receive_json()
                action = data.get("action")
                
                if action == "subscribe":
                    ticker_list = data.get("tickers", [])
                    if ticker_list:
                        await manager.subscribe(client_id, ticker_list)
                        
                elif action == "unsubscribe":
                    ticker_list = data.get("tickers", [])
                    if ticker_list:
                        await manager.unsubscribe(client_id, ticker_list)
                        
                elif action == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"Error processing client message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
                
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
    finally:
        await manager.disconnect_client(client_id)


@router.get("/ws/status")
async def websocket_status():
    """
    Get WebSocket connection status.
    
    Returns information about the upstream connection and active subscriptions.
    """
    manager = get_ws_manager()
    
    return {
        "connected_clients": len(manager.clients),
        "active_subscriptions": list(manager.active_subscriptions),
        "upstream_connected": manager._is_connected,
        "websocket_url": manager.ws_url,
        "api_key_configured": bool(manager.api_key),
    }
