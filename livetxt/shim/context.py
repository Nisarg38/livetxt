from __future__ import annotations

"""Fake LiveKit context objects for SMS mode."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class FakeParticipant:
    """Fake participant representing an SMS user."""

    def __init__(self, identity: str, name: str = "", metadata: str = ""):
        self.identity = identity
        self.name = name or identity
        self.sid = f"PA_sms_{identity}"
        self.metadata = metadata
        self.kind = "standard"
        self.attributes = {}  # Agent attributes (needed by AgentSession)

    async def publish_data(self, data: bytes, *, topic: str = "", reliable: bool = True) -> None:
        """Intercept data publishing - this will be handled by FakeRoom."""
        # This is called by the agent when it wants to send a message
        # The FakeRoom will intercept this
        pass

    async def set_attributes(self, attributes: dict) -> None:
        """Set participant attributes (needed by AgentSession)."""
        self.attributes.update(attributes)
        logger.debug(f"FakeParticipant.set_attributes: {attributes}")

    def get(self, key: str, default=None):
        """Get attribute value."""
        return self.attributes.get(key, default)


class FakeRoom:
    """
    Fake LiveKit room that routes to SMS backend.
    Implements enough of livekit.rtc.Room API to fool agent code.
    """

    def __init__(
        self,
        session_id: str,
        user_phone: str,
        client: Any,  # LiveTxtClient
        initial_message: str | None = None,
    ):
        self.name = session_id
        self.sid = f"RM_sms_{session_id}"
        self.metadata = json.dumps({"phone": user_phone})

        self._client = client
        self._session_id = session_id
        self._user_phone = user_phone
        self._initial_message = initial_message

        # Event handlers
        self._event_handlers: dict[str, list[Callable]] = {}

        # Participants
        self.local_participant = FakeParticipant(
            identity="agent",
            name="SMS Agent",
        )

        # Remote participant (SMS user)
        self._remote_participant = FakeParticipant(
            identity=f"sms_{user_phone}",
            name=user_phone,
            metadata=json.dumps({"phone": user_phone}),
        )

        # Hook into local participant's publish_data to capture agent responses
        self.local_participant.publish_data = self._intercept_publish_data

    @property
    def remote_participants(self) -> dict[str, FakeParticipant]:
        """Get remote participants."""
        return {self._remote_participant.identity: self._remote_participant}

    def isconnected(self) -> bool:
        """Return connection status. Always True in SMS mode."""
        return True

    def on(self, event: str, callback: Callable | None = None) -> Callable | None:
        """Register an event handler."""
        if callback is None:
            # Decorator usage
            def decorator(func: Callable) -> Callable:
                self._register_handler(event, func)
                return func

            return decorator
        else:
            # Direct usage
            self._register_handler(event, callback)
            return callback

    def off(self, event: str, callback: Callable | None = None) -> None:
        """Unregister an event handler."""
        if event not in self._event_handlers:
            return
        if callback is None:
            # Remove all handlers for this event
            self._event_handlers[event] = []
        else:
            # Remove specific handler
            if callback in self._event_handlers[event]:
                self._event_handlers[event].remove(callback)

    def _register_handler(self, event: str, callback: Callable) -> None:
        """Register an event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(callback)

    async def _emit_event(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Trigger registered event handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in event handler for {event}: {e}")

    async def connect(
        self, url: str | None = None, token: str | None = None, **kwargs: Any
    ) -> None:
        """Fake connection to room."""
        logger.info(f"Agent connecting to fake room {self.name}")

        # Emit participant_connected for the user
        await self._emit_event("participant_connected", self._remote_participant)

        # If there's an initial message, inject it after a short delay
        if self._initial_message:
            asyncio.create_task(self._inject_initial_message())

    async def disconnect(self) -> None:
        """Fake disconnection."""
        logger.info(f"Agent disconnecting from room {self.name}")

    def register_byte_stream_handler(self, *args: Any, **kwargs: Any) -> None:
        """Fake method - not needed in SMS mode."""
        logger.debug("register_byte_stream_handler called (no-op in SMS mode)")

    def register_text_stream_handler(self, *args: Any, **kwargs: Any) -> None:
        """Fake method - not needed in SMS mode."""
        logger.debug("register_text_stream_handler called (no-op in SMS mode)")

    def register_audio_stream_handler(self, *args: Any, **kwargs: Any) -> None:
        """Fake method - not needed in SMS mode."""
        logger.debug("register_audio_stream_handler called (no-op in SMS mode)")

    def unregister_byte_stream_handler(self, *args: Any, **kwargs: Any) -> None:
        """Fake method - not needed in SMS mode."""
        logger.debug("unregister_byte_stream_handler called (no-op in SMS mode)")

    def unregister_text_stream_handler(self, *args: Any, **kwargs: Any) -> None:
        """Fake method - not needed in SMS mode."""
        logger.debug("unregister_text_stream_handler called (no-op in SMS mode)")

    def unregister_audio_stream_handler(self, *args: Any, **kwargs: Any) -> None:
        """Fake method - not needed in SMS mode."""
        logger.debug("unregister_audio_stream_handler called (no-op in SMS mode)")

    async def _inject_initial_message(self) -> None:
        """Inject the initial SMS message as a data_received event."""
        await asyncio.sleep(0.5)  # Give agent time to set up handlers

        # Emit data_received event
        data = self._initial_message.encode("utf-8") if self._initial_message else b""
        await self._emit_event(
            "data_received",
            data,
            "lk.chat",  # topic
            self._remote_participant,
        )

    async def _intercept_publish_data(
        self, data: bytes, *, topic: str = "", reliable: bool = True
    ) -> None:
        """
        Intercept agent's outgoing messages and route to gateway.
        """
        try:
            # Agent is sending a response
            message = data.decode("utf-8") if isinstance(data, bytes) else str(data)
            logger.info(f"Agent response: {message}")

            # Send response to gateway
            await self._client.send_response(self._session_id, message)

        except Exception as e:
            logger.error(f"Error sending response: {e}")

    async def handle_incoming_message(self, message: str) -> None:
        """Handle an incoming message from the gateway."""
        logger.info(f"Incoming message: {message}")

        # Emit as data_received event
        data = message.encode("utf-8")
        await self._emit_event(
            "data_received",
            data,
            "lk.chat",
            self._remote_participant,
        )


class FakeJobContext:
    """
    Fake JobContext that agent code receives.
    Implements enough of livekit.agents.JobContext to work.
    """

    def __init__(
        self,
        session_id: str,
        user_phone: str,
        client: Any,
        initial_message: str | None = None,
    ):
        # Create fake job object
        self.job = type(
            "Job",
            (),
            {
                "id": session_id,
                "type": "room",
                "room": type("RoomInfo", (), {"name": session_id})(),
                "agent_name": "sms-agent",
                "metadata": json.dumps({"phone": user_phone}),
            },
        )()

        # Create fake room
        self.room = FakeRoom(session_id, user_phone, client, initial_message)

        self._client = client
        self._session_id = session_id

    async def connect(self, **kwargs: Any) -> None:
        """Connect to the fake room."""
        await self.room.connect(**kwargs)

    async def disconnect(self) -> None:
        """Disconnect from the fake room."""
        await self.room.disconnect()
