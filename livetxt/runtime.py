"""Runtime worker that executes agent code."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from .client import LiveTxtClient
from .config import LiveTxtConfig
from .shim import FakeJobContext, patch_livekit

logger = logging.getLogger(__name__)


EntrypointFunction = Callable[[Any], Any]


class LiveTxtWorker:
    """
    Worker that connects to gateway and runs agent entrypoint.
    """

    def __init__(self, config: LiveTxtConfig, entrypoint: EntrypointFunction):
        self.config = config
        self.entrypoint = entrypoint
        self.client = LiveTxtClient(config)
        self._active_sessions: dict[str, FakeJobContext] = {}

    async def start(self) -> None:
        """Start the worker."""
        # Patch LiveKit SDK
        patch_livekit()

        # Connect to gateway
        await self.client.connect()

        # Register message handler
        self.client.on_message(self._handle_message)

        logger.info("🚀 LiveTxt worker started and ready")

        # Keep running
        try:
            while self.client.is_connected():
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await self.client.disconnect()

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """
        Handle incoming message from gateway.

        Creates a FakeJobContext and runs the entrypoint.
        """
        session_id = data.get("session_id")
        from_number = data.get("from")
        message = data.get("message")

        if not session_id or not from_number or not message:
            logger.error(f"Invalid message data: {data}")
            return

        logger.info(f"📨 Message from {from_number} in session {session_id}: {message}")

        # Check if session already exists
        if session_id in self._active_sessions:
            # Existing session - just inject the message
            ctx = self._active_sessions[session_id]
            await ctx.room.handle_incoming_message(message)

        else:
            # New session - create context and run entrypoint
            await self._handle_new_session(session_id, from_number, message)

    async def _handle_new_session(self, session_id: str, from_number: str, message: str) -> None:
        """Handle a new session by running the entrypoint."""
        logger.info(f"🆕 New session {session_id}")

        # Create fake JobContext
        ctx = FakeJobContext(
            session_id=session_id,
            user_phone=from_number,
            client=self.client,
            initial_message=message,
        )

        # Store session
        self._active_sessions[session_id] = ctx

        try:
            # Run the entrypoint
            logger.info(f"Running entrypoint for session {session_id}")

            if asyncio.iscoroutinefunction(self.entrypoint):
                await self.entrypoint(ctx)
            else:
                self.entrypoint(ctx)

        except Exception as e:
            logger.error(f"Error in entrypoint for session {session_id}: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # Clean up session
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]

            logger.info(f"✅ Session {session_id} ended")


async def run_worker(config: LiveTxtConfig, entrypoint: EntrypointFunction) -> None:
    """
    Run a LiveTxt worker.

    Args:
        config: Configuration for the worker
        entrypoint: Agent entrypoint function
    """
    worker = LiveTxtWorker(config, entrypoint)
    await worker.start()
