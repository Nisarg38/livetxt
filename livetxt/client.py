"""WebSocket client for connecting to LiveTxt Gateway."""

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

import websockets
from websockets.client import WebSocketClientProtocol

from .config import LiveTxtConfig

logger = logging.getLogger(__name__)


MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


class LiveTxtClient:
    """WebSocket client that connects to LiveTxt Gateway."""

    def __init__(self, config: LiveTxtConfig):
        self.config = config
        self.ws: WebSocketClientProtocol | None = None
        self.worker_id: str | None = None
        self._message_handler: MessageHandler | None = None
        self._running = False
        self._heartbeat_task: asyncio.Task | None = None

    def on_message(self, handler: MessageHandler) -> None:
        """Register a message handler."""
        self._message_handler = handler

    async def connect(self) -> None:
        """Connect to the gateway."""
        # Build WebSocket URL with API key
        parsed = urlparse(self.config.gateway_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"

        # Add /worker/connect endpoint and API key
        query = urlencode({"api_key": self.config.api_key})
        ws_url = urlunparse((scheme, parsed.netloc, "/worker/connect", "", query, ""))

        logger.info(f"Connecting to {parsed.scheme}://{parsed.netloc}...")

        try:
            self.ws = await websockets.connect(ws_url)
            self._running = True

            # Wait for welcome message
            welcome = await self.ws.recv()
            data = json.loads(welcome)

            if data.get("event") == "connected":
                self.worker_id = data.get("worker_id")
                logger.info(f"✅ Connected as worker {self.worker_id}")

                # Send ready signal
                await self.send_event("ready", {"worker_id": self.worker_id})

                # Start heartbeat
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                # Start message loop
                asyncio.create_task(self._message_loop())

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from the gateway."""
        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task

        if self.ws:
            await self.ws.close()
            logger.info("Disconnected from gateway")

    async def send_event(self, event: str, data: dict[str, Any]) -> None:
        """Send an event to the gateway."""
        if not self.ws:
            raise RuntimeError("Not connected")

        message = {"event": event, **data}
        await self.ws.send(json.dumps(message))

    async def send_response(self, session_id: str, message: str) -> None:
        """Send a response for a session."""
        await self.send_event("response", {"session_id": session_id, "message": message})

    async def _message_loop(self) -> None:
        """Listen for messages from the gateway."""
        if not self.ws:
            return

        try:
            async for message in self.ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8")

                try:
                    data = json.loads(message)
                    event = data.get("event")

                    if event == "message":
                        # Incoming message from SMS
                        if self._message_handler:
                            await self._message_handler(data)

                    elif event == "heartbeat_ack":
                        # Heartbeat acknowledged
                        pass

                    else:
                        logger.warning(f"Unknown event: {event}")

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {message}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed by gateway")
            self._running = False

        except Exception as e:
            logger.error(f"Error in message loop: {e}")
            self._running = False

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to the gateway."""
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                if self._running and self.ws:
                    await self.send_event("heartbeat", {"timestamp": time.time()})

            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                break

    def is_connected(self) -> bool:
        """Check if connected to gateway."""
        return self._running and self.ws is not None
