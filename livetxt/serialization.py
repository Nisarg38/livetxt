"""
Serialization utilities for livekit-agents objects.

This module provides functions to convert AgentSession state objects
(ChatContext, ChatItems, FunctionCalls, etc.) to/from JSON-serializable dicts.

Note: We leverage LiveKit's built-in to_dict/from_dict methods where available,
which handle the complex internal structure correctly.
"""

from __future__ import annotations

import logging
from typing import Any

from livekit.agents import llm

logger = logging.getLogger(__name__)


def serialize_chat_context(chat_ctx: llm.ChatContext) -> dict[str, Any]:
    """
    Convert ChatContext to JSON-serializable dict.

    Uses LiveKit's built-in to_dict() method for proper serialization.

    Args:
        chat_ctx: The ChatContext to serialize

    Returns:
        A dictionary containing all chat items
    """
    return chat_ctx.to_dict(
        exclude_image=True,  # Exclude images (too large for persistence)
        exclude_audio=True,  # Exclude audio (not needed for text mode)
        exclude_timestamp=False,  # Keep timestamps
        exclude_function_call=False,  # Keep function calls
    )


def deserialize_chat_context(data: dict[str, Any]) -> llm.ChatContext:
    """
    Restore ChatContext from dict.

    Uses LiveKit's built-in from_dict() method for proper deserialization.

    Args:
        data: Dictionary containing serialized chat context

    Returns:
        A restored ChatContext
    """
    if not data or not data.get("items"):
        return llm.ChatContext.empty()

    return llm.ChatContext.from_dict(data)


def serialize_chat_item(item: llm.ChatItem) -> dict[str, Any]:
    """
    Serialize a single ChatItem (message, function call, etc).

    Args:
        item: The ChatItem to serialize

    Returns:
        Dictionary representation of the item
    """
    # ChatItem has a to_dict() method we can use
    if hasattr(item, "to_dict"):
        return item.to_dict()

    # Fallback: manual serialization
    result: dict[str, Any] = {
        "id": item.id,
        "type": item.type,
    }

    # Add type-specific fields
    if item.type == "message":
        result["role"] = item.role
        result["content"] = item.content

    return result


def serialize_function_tool_call(call: llm.FunctionToolCall) -> dict[str, Any]:
    """
    Convert FunctionToolCall to dict.

    Args:
        call: The FunctionToolCall to serialize

    Returns:
        A dictionary representation
    """
    import json as _json

    # FunctionToolCall.arguments is a JSON string in livekit-agents
    try:
        arguments_obj = _json.loads(call.arguments) if isinstance(call.arguments, str) else call.arguments
    except Exception:
        arguments_obj = {"_raw": call.arguments}

    return {
        "call_id": call.call_id,
        "name": call.name,
        "arguments": arguments_obj,
    }


def deserialize_function_tool_call(data: dict[str, Any]) -> llm.FunctionToolCall:
    """
    Restore FunctionToolCall from dict.

    Args:
        data: Dictionary containing serialized tool call

    Returns:
        A restored FunctionToolCall
    """
    import json as _json

    # Accept both 'name' and legacy 'function_name'
    name = data.get("name") or data.get("function_name")
    args = data.get("arguments", {})
    arguments_str = _json.dumps(args) if not isinstance(args, str) else args

    return llm.FunctionToolCall(
        call_id=data.get("call_id", ""),
        name=name,
        arguments=arguments_str,
    )


def serialize_session_state(
    chat_context: llm.ChatContext | None = None,
    function_calls: list[dict[str, Any]] | None = None,
    user_state: str = "listening",
    agent_state: str = "idle",
) -> dict[str, Any]:
    """
    Serialize complete agent session state.

    This packages all captured state into a single dictionary for gateway persistence.

    Args:
        chat_context: The chat context to serialize (optional)
        function_calls: List of function calls executed
        user_state: Current user state (e.g., "listening", "speaking")
        agent_state: Current agent state (e.g., "idle", "thinking", "speaking")

    Returns:
        A complete serialized state dictionary
    """
    return {
        "chat_context": serialize_chat_context(chat_context) if chat_context else {"items": []},
        "function_calls": function_calls or [],
        "user_state": user_state,
        "agent_state": agent_state,
        "version": "1.0",  # For future compatibility
    }


def deserialize_session_state(data: dict[str, Any]) -> dict[str, Any]:
    """
    Deserialize agent session state.

    Args:
        data: Serialized state dictionary

    Returns:
        Validated state dictionary with defaults for missing fields
    """
    # Validate version if present
    version = data.get("version", "1.0")
    if version != "1.0":
        logger.warning(f"Unknown state version: {version}, attempting to parse anyway")

    chat_context_data = data.get("chat_context", {"items": []})
    chat_context = deserialize_chat_context(chat_context_data) if chat_context_data else None

    return {
        "chat_context": chat_context,
        "function_calls": data.get("function_calls", []),
        "user_state": data.get("user_state", "listening"),
        "agent_state": data.get("agent_state", "idle"),
    }
