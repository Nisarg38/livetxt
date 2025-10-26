"""
Data models for livetxt.

These models define the protocol for communication between the gateway and runtime worker.
"""

from __future__ import annotations

from typing import Any, Literal

from livekit.agents.llm import ChatContext
from pydantic import BaseModel, Field


class SerializableSessionState(BaseModel):
    """
    Represents the complete conversation state that can be serialized and passed between jobs.

    This is the core state object that gets saved to Redis and restored on each turn.
    It contains everything needed to reconstruct the agent's context.
    """

    chat_items: list[dict[str, Any]] = Field(default_factory=list)
    """
    The chat history as a list of serialized ChatItem objects.
    Includes messages, function calls, and function outputs.
    """

    metadata: dict[str, Any] = Field(default_factory=dict)
    """
    Custom metadata for the session (user info, session ID, etc.)
    This is user-defined and not interpreted by the runtime.
    """

    @classmethod
    def from_chat_context(
        cls, chat_ctx: ChatContext, metadata: dict[str, Any] | None = None
    ) -> SerializableSessionState:
        """
        Create a SerializableSessionState from a ChatContext.

        Args:
            chat_ctx: The ChatContext to serialize
            metadata: Optional metadata to include

        Returns:
            A new SerializableSessionState
        """
        # Serialize chat items to dict format
        chat_dict = chat_ctx.to_dict(
            exclude_image=True,  # Don't serialize images (too large)
            exclude_audio=True,  # Don't serialize audio frames
            exclude_timestamp=False,  # Keep timestamps for ordering
            exclude_function_call=False,  # Keep function calls
        )

        return cls(chat_items=chat_dict.get("items", []), metadata=metadata or {})

    def to_chat_context(self) -> ChatContext:
        """
        Convert this state back to a ChatContext.

        Returns:
            A ChatContext reconstructed from the serialized state
        """
        if not self.chat_items:
            return ChatContext.empty()

        # Deserialize the chat items
        return ChatContext.from_dict({"items": self.chat_items})

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Override to ensure proper serialization."""
        return super().model_dump(mode="json", **kwargs)


class JobRequest(BaseModel):
    """
    Request sent from the gateway to the worker to process a user message.

    This contains the user's input and the current conversation state.
    """

    job_id: str
    """Unique identifier for this job (for tracking and correlation)."""

    user_input: str
    """The text input from the user (e.g., SMS message content)."""

    state: SerializableSessionState
    """The current conversation state."""

    timeout_ms: int = Field(default=30000)
    """Maximum time to wait for agent processing (milliseconds)."""


class JobResult(BaseModel):
    """
    Result returned from the worker to the gateway after processing.

    Contains the agent's response and the updated conversation state.
    """

    job_id: str
    """The job ID from the request."""

    status: Literal["success", "error", "timeout"]
    """The status of the job execution."""

    response_text: str | None = None
    """The agent's text response to send back to the user."""

    updated_state: SerializableSessionState | None = None
    """The updated conversation state after processing."""

    error: str | None = None
    """Error message if status is 'error'."""

    processing_time_ms: float | None = None
    """Time taken to process the job (for monitoring)."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Additional metadata about the execution (token usage, etc.)."""
