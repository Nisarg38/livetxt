"""
Automatic monkey-patching for zero-code-change LiveKit integration.

This module transparently wraps livekit-agents Agent class to:
1. Automatically capture conversation state
2. Automatically restore state on agent creation
3. Track function calls without user code changes
4. Work with unmodified livekit-agents code
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Global state storage
_PATCHING_APPLIED = False
_AGENT_STATES: dict[int, dict[str, Any]] = {}
_CURRENT_CONTEXT: dict[str, Any] = {}


def set_execution_context(context: dict[str, Any]) -> None:
    """
    Set context for current execution.
    
    This is called by the worker before running an agent to provide
    previous state and user context.
    """
    global _CURRENT_CONTEXT
    _CURRENT_CONTEXT = context
    logger.debug(f"Execution context set: {list(context.keys())}")


def get_agent_state(agent: Any) -> dict[str, Any]:
    """Get automatically captured state for an agent."""
    agent_id = id(agent)
    return _AGENT_STATES.get(agent_id, {
        "chat_context": None,
        "function_calls": [],
        "user_state": "listening",
        "agent_state": "idle",
    })


def clear_agent_state(agent: Any) -> None:
    """Clear captured state for an agent (cleanup)."""
    agent_id = id(agent)
    if agent_id in _AGENT_STATES:
        del _AGENT_STATES[agent_id]


def _auto_capture_state(agent: Any) -> None:
    """Automatically capture current state from agent."""
    from ..serialization import serialize_chat_context

    agent_id = id(agent)
    state: dict[str, Any] = {
        "chat_context": None,
        "function_calls": getattr(agent, '_livetxt_function_calls', []),
        "user_state": "listening",
        "agent_state": "idle",
    }

    # Capture chat context if available
    # Access _chat_ctx directly to avoid triggering the wrapped property and recursion
    if hasattr(agent, '_chat_ctx') and agent._chat_ctx is not None:
        try:
            state["chat_context"] = serialize_chat_context(agent._chat_ctx)
            logger.debug(f"Captured chat_ctx with {len(agent._chat_ctx.items)} items")
        except Exception as e:
            logger.warning(f"Failed to serialize chat_ctx: {e}")

    _AGENT_STATES[agent_id] = state


def _auto_restore_state(agent: Any) -> None:
    """Automatically restore state to agent from context."""
    from ..serialization import deserialize_chat_context

    # Get state from current execution context
    state = _CURRENT_CONTEXT.get("previous_state")
    if not state:
        logger.debug("No previous state to restore")
        return

    # Restore chat context
    if "chat_context" in state and state["chat_context"]:
        try:
            restored_ctx = deserialize_chat_context(state["chat_context"])
            if hasattr(agent, 'update_chat_ctx'):
                agent.update_chat_ctx(restored_ctx)
                logger.info(f"✅ Auto-restored {len(restored_ctx.items)} chat items")
            else:
                # Fallback: set directly
                agent._chat_ctx = restored_ctx
        except Exception as e:
            logger.warning(f"Failed to restore chat_ctx: {e}")

    # Restore function call history
    if "function_calls" in state:
        agent._livetxt_function_calls = state["function_calls"].copy()


def _wrap_agent_init(original_init: Callable) -> Callable:
    """Wrap Agent.__init__ to auto-restore state."""

    @functools.wraps(original_init)
    def wrapped_init(self, *args: Any, **kwargs: Any) -> Any:
        # Call original init
        result = original_init(self, *args, **kwargs)

        # Initialize function call tracking
        self._livetxt_function_calls = []

        # Auto-restore state if available
        _auto_restore_state(self)

        logger.debug(f"Agent initialized with auto-restore: {type(self).__name__}")
        return result

    return wrapped_init


def _wrap_chat_ctx_property(agent_class: type) -> None:
    """Wrap chat_ctx property to auto-capture on access."""

    # Get original property
    original_property = None
    for cls in agent_class.__mro__:
        if 'chat_ctx' in cls.__dict__:
            original_property = cls.__dict__['chat_ctx']
            break

    if not original_property or not isinstance(original_property, property):
        logger.warning("Could not find chat_ctx property to wrap")
        return

    original_fget = original_property.fget

    def wrapped_fget(self: Any) -> Any:
        """Get chat_ctx and auto-capture state."""
        ctx = original_fget(self) if original_fget else self._chat_ctx

        # Auto-capture state when chat_ctx is accessed
        # (This captures after agent has processed/updated context)
        _auto_capture_state(self)

        return ctx

    # Replace property
    agent_class.chat_ctx = property(
        fget=wrapped_fget,
        fset=original_property.fset if hasattr(original_property, 'fset') else None,
        doc=original_property.__doc__
    )


def _wrap_function_tools(agent: Any) -> None:
    """Wrap function tools to auto-track calls."""

    # Find all methods decorated with @llm.function_tool()
    for attr_name in dir(agent):
        try:
            attr = getattr(agent, attr_name)

            # Check if it's a function tool (has metadata from decorator)
            if not callable(attr) or attr_name.startswith('_'):
                continue

            # If it has function tool metadata, wrap it
            if hasattr(attr, '__wrapped__') or hasattr(attr, '_is_function_tool'):
                original_func = attr

                @functools.wraps(original_func)
                async def wrapped_tool(*args: Any, **kwargs: Any) -> Any:
                    func_name = original_func.__name__
                    logger.debug(f"Function tool called: {func_name}")

                    # Call original function
                    try:
                        result = await original_func(*args, **kwargs)

                        # Track the call
                        if not hasattr(agent, '_livetxt_function_calls'):
                            agent._livetxt_function_calls = []

                        agent._livetxt_function_calls.append({
                            "function_name": func_name,
                            "arguments": kwargs,
                            "result": result,
                            "error": None
                        })

                        return result
                    except Exception as e:
                        # Track error
                        if not hasattr(agent, '_livetxt_function_calls'):
                            agent._livetxt_function_calls = []

                        agent._livetxt_function_calls.append({
                            "function_name": func_name,
                            "arguments": kwargs,
                            "result": None,
                            "error": str(e)
                        })
                        raise

                # Replace method
                setattr(agent, attr_name, wrapped_tool)
        except Exception as e:
            logger.debug(f"Could not wrap {attr_name}: {e}")


def patch_livekit_auto() -> None:
    """
    Apply automatic monkey-patches to livekit-agents.
    
    This makes state capture and restoration completely transparent.
    User code requires ZERO changes.
    """
    global _PATCHING_APPLIED

    if _PATCHING_APPLIED:
        logger.debug("Auto-patching already applied")
        return

    try:
        from livekit.agents import Agent

        # Store original __init__
        original_init = Agent.__init__

        # Wrap __init__ to auto-restore state
        Agent.__init__ = _wrap_agent_init(original_init)

        # Wrap chat_ctx property to auto-capture state
        _wrap_chat_ctx_property(Agent)

        logger.info("✅ LiveKit auto-patching applied successfully")
        _PATCHING_APPLIED = True

    except ImportError:
        logger.warning("livekit-agents not installed, skipping auto-patch")
        _PATCHING_APPLIED = True
    except Exception as e:
        logger.error(f"Failed to apply auto-patches: {e}", exc_info=True)
        _PATCHING_APPLIED = True


def install_agent_hooks(agent: Any) -> None:
    """
    Install hooks on a specific agent instance after creation.
    
    This is called after agent is instantiated to wrap function tools.
    """
    try:
        _wrap_function_tools(agent)
        logger.debug(f"Installed hooks on agent: {type(agent).__name__}")
    except Exception as e:
        logger.warning(f"Failed to install agent hooks: {e}")
