"""
Session wrapper for capturing Agent events and state.

This module provides a wrapper around livekit-agents Agent instances
to capture conversation state, function calls, and events for persistence.
"""

from __future__ import annotations

import logging
from typing import Any

from livekit.agents import Agent, llm

from .serialization import (
    serialize_session_state,
)

logger = logging.getLogger(__name__)


class LiveTxtSessionWrapper:
    """
    Wraps an Agent instance to capture events and state changes.

    This wrapper:
    - Captures conversation history from the agent's chat_ctx
    - Tracks function calls executed during the session
    - Records state changes (user/agent state)
    - Provides serializable state for persistence

    Usage:
        agent = MyAgent()
        wrapper = LiveTxtSessionWrapper(agent)

        # Agent runs normally
        await agent.on_enter()
        # ...

        # Get captured state
        state = wrapper.get_serializable_state()
    """

    def __init__(self, agent: Agent):
        """
        Initialize the wrapper around an agent.

        Args:
            agent: The Agent instance to wrap
        """
        self.agent = agent
        self.captured_state: dict[str, Any] = {
            "function_calls": [],
            "user_state": "listening",
            "agent_state": "idle",
            "events": [],  # Optional: track events for debugging
        }

        logger.debug(f"LiveTxtSessionWrapper initialized for agent: {type(agent).__name__}")

    def capture_function_call(
        self, function_name: str, arguments: dict[str, Any], result: Any = None, error: str | None = None
    ) -> None:
        """
        Manually capture a function call.

        This should be called by agents when they execute function tools.

        Args:
            function_name: Name of the function called
            arguments: Arguments passed to the function
            result: Result returned by the function (optional)
            error: Error message if function call failed (optional)
        """
        call_info = {
            "function_name": function_name,
            "arguments": arguments,
            "result": result,
            "error": error,
            "timestamp": None,  # Could add timestamp if needed
        }
        self.captured_state["function_calls"].append(call_info)
        logger.debug(f"Captured function call: {function_name}")

    def capture_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Capture an arbitrary event for debugging/logging.

        Args:
            event_type: Type of event (e.g., "user_state_changed")
            data: Event data
        """
        event_info = {"type": event_type, "data": data}
        self.captured_state["events"].append(event_info)
        logger.debug(f"Captured event: {event_type}")

    def update_user_state(self, state: str) -> None:
        """
        Update the user state.

        Args:
            state: New user state (e.g., "listening", "speaking")
        """
        self.captured_state["user_state"] = state
        logger.debug(f"User state updated: {state}")

    def update_agent_state(self, state: str) -> None:
        """
        Update the agent state.

        Args:
            state: New agent state (e.g., "idle", "thinking", "speaking")
        """
        self.captured_state["agent_state"] = state
        logger.debug(f"Agent state updated: {state}")

    def get_chat_context(self) -> llm.ChatContext | None:
        """
        Get the agent's current chat context.

        Returns:
            The agent's ChatContext, or None if not available
        """
        if hasattr(self.agent, "chat_ctx"):
            return self.agent.chat_ctx
        return None

    def get_serializable_state(self) -> dict[str, Any]:
        """
        Get complete state for gateway persistence.

        This extracts the agent's chat context and combines it with
        captured function calls and state changes.

        Returns:
            A dictionary containing all serializable state
        """
        chat_ctx = self.get_chat_context()

        return serialize_session_state(
            chat_context=chat_ctx,
            function_calls=self.captured_state["function_calls"],
            user_state=self.captured_state["user_state"],
            agent_state=self.captured_state["agent_state"],
        )

    def restore_state(self, state: dict[str, Any]) -> None:
        """
        Restore agent state from serialized data.

        This updates the agent's chat context with previously saved state.

        Args:
            state: Previously serialized state dictionary
        """
        # Restore chat context if available
        if "chat_context" in state and state["chat_context"]:
            from .serialization import deserialize_chat_context

            restored_ctx = deserialize_chat_context(state["chat_context"])

            # Update agent's chat context
            if hasattr(self.agent, "update_chat_ctx"):
                self.agent.update_chat_ctx(restored_ctx)
                logger.info(f"Restored {len(restored_ctx.items)} chat items to agent")
            else:
                logger.warning("Agent does not support update_chat_ctx()")

        # Restore function call history
        if "function_calls" in state:
            self.captured_state["function_calls"] = state["function_calls"]

        # Restore state values
        if "user_state" in state:
            self.captured_state["user_state"] = state["user_state"]
        if "agent_state" in state:
            self.captured_state["agent_state"] = state["agent_state"]

        logger.info("State restored to agent wrapper")


class SessionContext:
    """
    Context manager for agent sessions with state capture.

    Usage:
        async with SessionContext(agent) as wrapper:
            # Run agent
            await agent.on_enter()
            # ...

            # Get state at end
            state = wrapper.get_serializable_state()
    """

    def __init__(self, agent: Agent, initial_state: dict[str, Any] | None = None):
        """
        Initialize session context.

        Args:
            agent: The Agent instance
            initial_state: Optional initial state to restore
        """
        self.agent = agent
        self.initial_state = initial_state
        self.wrapper: LiveTxtSessionWrapper | None = None

    async def __aenter__(self) -> LiveTxtSessionWrapper:
        """Start the session context."""
        self.wrapper = LiveTxtSessionWrapper(self.agent)

        # Restore initial state if provided
        if self.initial_state:
            self.wrapper.restore_state(self.initial_state)

        # Call agent's on_enter if it has one
        if hasattr(self.agent, "on_enter"):
            await self.agent.on_enter()

        return self.wrapper

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the session context."""
        # Call agent's on_exit if it has one
        if hasattr(self.agent, "on_exit"):
            try:
                await self.agent.on_exit()
            except Exception as e:
                logger.error(f"Error in agent.on_exit(): {e}")

        return False  # Don't suppress exceptions
