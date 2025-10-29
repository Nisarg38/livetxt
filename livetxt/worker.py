"""
Stateless worker that executes agent jobs.

This module provides the core execution logic for running livekit-agents
in a text-only, stateless mode.
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from collections.abc import Callable
from typing import Any

from .models import JobRequest, JobResult, SerializableSessionState

logger = logging.getLogger(__name__)

# Import AgentSession for patching (optional - will work without it too)
try:
    from livekit.agents import AgentSession

    AGENT_SESSION_AVAILABLE = True
except ImportError:
    AGENT_SESSION_AVAILABLE = False
    logger.debug("AgentSession not available - voice agents will not work")


class TextOnlyJobContext:
    """
    Fake JobContext for text-only execution.

    This provides the minimal API that agents expect from JobContext
    while capturing text output and managing state.
    """

    def __init__(self, request: JobRequest, output_buffer: list[str]):
        self.request = request
        self._output_buffer = output_buffer
        self._connected = False

        # Create fake job object
        self.job = type(
            "Job",
            (),
            {
                "id": request.job_id,
                "type": "room",
                "room": type("RoomInfo", (), {"name": f"session_{request.job_id}"})(),
                "agent_name": "text-agent",
                "metadata": "{}",
            },
        )()

        # Create fake room
        self.room = TextOnlyRoom(request, output_buffer)

        # Expose local participant
        self.agent = self.room.local_participant

    async def connect(self, **kwargs: Any) -> None:
        """Fake connect to room."""
        if self._connected:
            return

        self._connected = True
        logger.debug(f"[Job {self.request.job_id}] Agent connected")

        # Schedule message injection for after handlers are set up
        asyncio.create_task(self._inject_user_message())

    async def _inject_user_message(self) -> None:
        """Inject the user's input as a data_received event."""
        # Wait a bit longer for agent to fully set up handlers
        await asyncio.sleep(0.3)

        # Emit data_received event with the user's message
        data = self.request.user_input.encode("utf-8")
        remote_participant = self.room.remote_participants.get("user")

        logger.debug(
            f"[Job {self.request.job_id}] Injecting user message: {self.request.user_input}"
        )
        logger.debug(
            f"[Job {self.request.job_id}] Registered handlers: {list(self.room._event_handlers.keys())}"
        )

        if self.room._event_handlers.get("data_received"):
            for handler in self.room._event_handlers["data_received"]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data, "lk.chat", remote_participant)
                    else:
                        handler(data, "lk.chat", remote_participant)
                    logger.debug(f"[Job {self.request.job_id}] Called data_received handler")
                except Exception as e:
                    logger.error(f"Error in data_received handler: {e}")
        else:
            logger.warning(f"[Job {self.request.job_id}] No data_received handlers registered!")


class FakeParticipant:
    """Minimal fake participant."""

    def __init__(self, identity: str, name: str):
        self.identity = identity
        self.name = name
        self.sid = f"PA_{identity}"
        self.metadata = "{}"
        self.attributes = {}  # Agent attributes (needed by AgentSession)
        self.kind = "standard"  # Participant kind (needed by AgentSession)
        self._publish_override = None

    def publish_data(self, data: bytes, *, topic: str = "", reliable: bool = True) -> None:
        """
        Fake publish - synchronous to match typical agent usage.

        Note: In real LiveKit, this is async, but many simple agents call it
        without await from synchronous handlers. We make this work by scheduling
        the actual work asynchronously.
        """
        logger.debug(
            f"FakeParticipant.publish_data called with {len(data) if isinstance(data, bytes) else 'non-bytes'} bytes"
        )

        if self._publish_override:
            # Schedule the async work
            try:
                asyncio.get_event_loop()
                if asyncio.iscoroutinefunction(self._publish_override):
                    # Create task to run the async override
                    asyncio.create_task(
                        self._publish_override(data, topic=topic, reliable=reliable)
                    )
                else:
                    # Call sync override directly
                    self._publish_override(data, topic=topic, reliable=reliable)
            except RuntimeError:
                # No event loop, call synchronously if possible
                if not asyncio.iscoroutinefunction(self._publish_override):
                    self._publish_override(data, topic=topic, reliable=reliable)
                else:
                    logger.error("Cannot schedule async publish_data without event loop")
        else:
            logger.warning("publish_data called but no override set!")

    async def set_attributes(self, attributes: dict):
        """Set participant attributes (needed by AgentSession)."""
        self.attributes.update(attributes)
        logger.debug(f"FakeParticipant.set_attributes: {attributes}")

    def get(self, key: str, default=None):
        """Get attribute value."""
        return self.attributes.get(key, default)


class TextOnlyRoom:
    """
    Fake Room for text-only execution.

    Captures agent responses via publish_data and manages events.
    """

    def __init__(self, request: JobRequest, output_buffer: list[str]):
        self.request = request
        self._output_buffer = output_buffer

        self.name = f"session_{request.job_id}"
        self.sid = f"RM_{request.job_id}"
        self.metadata = "{}"

        # Connection state (needed by AgentSession)
        self.isconnected = lambda: True  # Always report as connected

        # Event handlers
        self._event_handlers: dict[str, list[Callable]] = {}

        # Participants
        self.local_participant = FakeParticipant("agent", "Agent")
        self._remote_participant = FakeParticipant("user", "User")

        # Override local participant's publish_data to capture output
        self.local_participant._publish_override = self._capture_agent_output

    @property
    def remote_participants(self) -> dict[str, FakeParticipant]:
        """Get remote participants."""
        return {"user": self._remote_participant}

    def on(self, event: str, callback: Callable | None = None) -> Callable | None:
        """Register event handler."""
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

    def _register_handler(self, event: str, callback: Callable) -> None:
        """Register an event handler."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(callback)

    def _capture_agent_output(self, data: bytes, *, topic: str = "", reliable: bool = True) -> None:
        """
        Capture agent's output when it calls publish_data.

        This is the key interception point - when the agent wants to send
        a message, we capture it here.

        This is synchronous to match the synchronous publish_data signature.
        """
        try:
            message = data.decode("utf-8") if isinstance(data, bytes) else str(data)
            logger.debug(f"[Job {self.request.job_id}] Captured output: {message[:100]}...")
            self._output_buffer.append(message)
        except Exception as e:
            logger.error(f"Error capturing agent output: {e}")

    # Fake methods that AgentSession might call
    def register_byte_stream_handler(self, *args, **kwargs):
        """Fake method - not needed in text mode."""
        logger.debug("register_byte_stream_handler called (no-op in text mode)")
        pass

    def register_text_stream_handler(self, *args, **kwargs):
        """Fake method - not needed in text mode."""
        logger.debug("register_text_stream_handler called (no-op in text mode)")
        pass

    def register_audio_stream_handler(self, *args, **kwargs):
        """Fake method - not needed in text mode."""
        logger.debug("register_audio_stream_handler called (no-op in text mode)")
        pass

    async def disconnect(self):
        """Fake disconnect."""
        logger.debug("Room.disconnect called (no-op in text mode)")
        pass


async def execute_job(
    entrypoint: Callable[[Any], Any], request: JobRequest, timeout_ms: int | None = None
) -> JobResult:
    """
    Execute a single agent job in a stateless manner.

    This is the core function that:
    1. Creates a fake JobContext with the request's state
    2. Runs the agent entrypoint
    3. Captures the agent's text responses
    4. Returns a JobResult with updated state

    Supports both simple agents (data_received handlers) and voice agents (AgentSession).

    Args:
        entrypoint: The agent entrypoint function (same signature as livekit-agents)
        request: The job request containing user input and state
        timeout_ms: Optional timeout in milliseconds (overrides request.timeout_ms)

    Returns:
        JobResult with status, response, and updated state
    """
    start_time = time.time()
    timeout = (timeout_ms or request.timeout_ms) / 1000.0  # Convert to seconds

    # Buffer to capture agent's text output
    output_buffer: list[str] = []

    # Reference to captured agent (for extracting chat_ctx)
    captured_agent = None
    captured_session = None

    # Create the fake context
    ctx = TextOnlyJobContext(request, output_buffer)

    # Install AgentSession hooks if available
    cleanup_hook = None
    if AGENT_SESSION_AVAILABLE:
        def _set_captured_agent(agent):
            nonlocal captured_agent
            captured_agent = agent

        def _set_captured_session(session):
            nonlocal captured_session
            captured_session = session

        cleanup_hook = _install_agent_session_hooks(
            output_buffer,
            _set_captured_agent,
            _set_captured_session
        )

    async def _execute_with_timeout():
        # Run the entrypoint with timeout
        if asyncio.iscoroutinefunction(entrypoint):
            await asyncio.wait_for(entrypoint(ctx), timeout=timeout)
        else:
            # Sync function - run in executor
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, entrypoint, ctx), timeout=timeout
            )

        # For text-based LLMs, use AgentSession.run() to process the message
        if captured_session and hasattr(captured_session, '_livetxt_use_run_method') and captured_session._livetxt_use_run_method:
            logger.info("Using AgentSession.run() for text-based LLM")
            try:
                # Give session a moment to fully start
                await asyncio.sleep(0.1)

                # Use run() to process the user input
                result = await captured_session.run(user_input=request.user_input)
                logger.info(f"AgentSession.run() completed, result type: {type(result)}")

                # Extract response from result
                if hasattr(result, 'last_message') and result.last_message:
                    msg = result.last_message
                    if hasattr(msg, 'content'):
                        if isinstance(msg.content, str):
                            logger.info(f"✅ Captured response from run(): {msg.content[:100]}...")
                            output_buffer.append(msg.content)
                        elif isinstance(msg.content, list):
                            for part in msg.content:
                                if hasattr(part, 'text'):
                                    logger.info(f"✅ Captured text from content part: {part.text[:100]}...")
                                    output_buffer.append(part.text)
                                elif isinstance(part, str):
                                    output_buffer.append(part)
            except Exception as e:
                logger.error(f"Error using AgentSession.run(): {e}")
                logger.error(traceback.format_exc())
        else:
            # Voice-based model or legacy approach: wait for async message injection
            logger.debug("Using voice-based approach with message injection")
            await asyncio.sleep(1.0)

    try:
        # Run the entire execution with timeout
        await asyncio.wait_for(_execute_with_timeout(), timeout=timeout)

        # Try to extract response from chat context if we haven't captured it yet
        if not output_buffer and captured_agent and hasattr(captured_agent, 'chat_ctx'):
            logger.info("No output captured via hooks, trying to extract from chat_ctx")
            try:
                chat_ctx = captured_agent.chat_ctx
                logger.info(f"Agent has chat_ctx: {chat_ctx}")
                logger.info(f"chat_ctx type: {type(chat_ctx)}")
                logger.info(f"chat_ctx dir: {[x for x in dir(chat_ctx) if not x.startswith('_')]}")

                # ChatContext uses 'items' not 'messages'
                if chat_ctx:
                    items = chat_ctx.items if hasattr(chat_ctx, 'items') else []
                    logger.info(f"Chat context has {len(items)} items")
                    for item in items:
                        logger.info(f"  Item role={getattr(item, 'role', None)}, type={type(item)}")
                        if hasattr(item, 'role') and item.role == 'assistant' and hasattr(item, 'content'):
                            # Extract assistant message
                                content = item.content
                                logger.info(f"  Assistant content type: {type(content)}")
                                if isinstance(content, str):
                                    logger.info(f"✅ Captured assistant message from chat_ctx: {content[:100]}...")
                                    output_buffer.append(content)
                                elif isinstance(content, list):
                                    # Content might be a list of content parts
                                    for part in content:
                                        if hasattr(part, 'text'):
                                            logger.info(f"✅ Captured assistant text from content part: {part.text[:100]}...")
                                            output_buffer.append(part.text)
                                        elif isinstance(part, dict) and 'text' in part:
                                            logger.info(f"✅ Captured assistant text from dict: {part['text'][:100]}...")
                                            output_buffer.append(part['text'])
                                else:
                                    logger.warning(f"⚠️ Assistant content is not string or list: {content}")
            except Exception as e:
                logger.error(f"Error extracting from chat_ctx: {e}")
                logger.error(traceback.format_exc())

        # Collect the response
        response_text = " ".join(output_buffer) if output_buffer else None
        logger.debug(
            f"[Job {request.job_id}] Captured {len(output_buffer)} messages: {output_buffer}"
        )

        # Extract updated state from agent if available
        if captured_agent and hasattr(captured_agent, "_chat_ctx"):
            logger.debug(f"[Job {request.job_id}] Extracting state from agent's chat_ctx")
            try:
                updated_state = SerializableSessionState.from_chat_context(captured_agent._chat_ctx)
            except Exception as e:
                logger.warning(f"Failed to extract chat context: {e}")
                updated_state = request.state
        else:
            # For simple agents without AgentSession, just track metadata
            updated_state = request.state
            if updated_state.metadata is None:
                updated_state.metadata = {}
            updated_state.metadata["last_turn"] = {
                "user_input": request.user_input,
                "agent_response": response_text,
                "timestamp": time.time(),
            }

        processing_time_ms = (time.time() - start_time) * 1000

        return JobResult(
            job_id=request.job_id,
            status="success",
            response_text=response_text,
            updated_state=updated_state,
            processing_time_ms=processing_time_ms,
        )

    except asyncio.TimeoutError:
        processing_time_ms = (time.time() - start_time) * 1000
        logger.warning(f"Job {request.job_id} timed out after {processing_time_ms}ms")

        return JobResult(
            job_id=request.job_id,
            status="timeout",
            error=f"Job execution exceeded timeout of {timeout_ms}ms",
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        processing_time_ms = (time.time() - start_time) * 1000
        error_details = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Job {request.job_id} failed: {error_details}")
        logger.debug(traceback.format_exc())

        return JobResult(
            job_id=request.job_id,
            status="error",
            error=error_details,
            processing_time_ms=processing_time_ms,
        )

    finally:
        # Cleanup hooks
        if cleanup_hook:
            cleanup_hook()


def _install_agent_session_hooks(
    output_buffer: list[str],
    on_agent_captured: Callable,
    on_session_captured: Callable
) -> Callable:
    """
    Install hooks into AgentSession to capture LLM responses.

    This patches AgentSession.start() to:
    1. Hook into conversation events
    2. Capture assistant messages from the LLM
    3. Extract the agent instance for state capture
    4. Capture the session instance for text-based processing

    Args:
        output_buffer: List to append captured messages to
        on_agent_captured: Callback when agent is captured
        on_session_captured: Callback when session is captured

    Returns:
        Cleanup function to restore original AgentSession.start
    """
    if not AGENT_SESSION_AVAILABLE:
        return lambda: None

    original_start = AgentSession.start

    async def patched_start(self, *args, **kwargs):
        """Patched start method that hooks into conversation events."""
        # Capture the session reference
        on_session_captured(self)

        # Extract agent from args/kwargs
        agent = kwargs.get("agent") if "agent" in kwargs else (args[0] if args else None)

        if agent:
            # Capture the agent reference
            on_agent_captured(agent)

            # Replace RealtimeModel with text-based LLM for text-only mode
            is_text_based_llm = False
            if hasattr(agent, 'llm') and agent.llm is not None:
                llm_type = type(agent.llm).__name__

                # Check if it's a RealtimeModel (voice-based)
                if 'realtime' in llm_type.lower() or 'RealtimeModel' in llm_type:
                    logger.warning(
                        f"Agent uses {llm_type} which requires audio. "
                        "Replacing with text-based LLM (gpt-5-mini) for text-only mode."
                    )
                    try:
                        from livekit.plugins import openai
                        # Replace with text-based model
                        agent._llm = openai.LLM(model="gpt-5-mini")
                        is_text_based_llm = True
                        logger.info("Successfully replaced RealtimeModel with text-based LLM")
                    except Exception as e:
                        logger.error(f"Failed to replace RealtimeModel: {e}")
                        logger.error("Agent may not respond correctly in text-only mode")
                else:
                    # Already a text-based LLM
                    is_text_based_llm = 'LLM' in llm_type and 'Realtime' not in llm_type

            # Store flag on session for later use
            self._livetxt_use_run_method = is_text_based_llm

        # AgentSession setup complete

        # Install minimal debug hook for events (only log key events)
        original_emit = None
        if hasattr(self, 'emit'):
            original_emit = self.emit
            def debug_emit(event_name, *args, **kwargs):
                # Only log important events, not all events
                if event_name in ('agent_state_changed', 'conversation_item_added'):
                    logger.debug(f"AgentSession: {event_name}")
                return original_emit(event_name, *args, **kwargs)
            self.emit = debug_emit

        # Hook into conversation events to capture assistant messages
        @self.on("conversation_item_added")
        def on_conversation_item(event):
            """Capture assistant messages from the conversation."""
            logger.debug("Conversation item added")
            try:
                item = event.item
                if hasattr(item, "role") and item.role == "assistant":
                    # Extract text content from the message
                    if hasattr(item, "text_content") and item.text_content:
                        text = item.text_content
                        logger.info(f"✅ Captured assistant message: {text[:100]}...")
                        output_buffer.append(text)
                    elif hasattr(item, "content") and isinstance(item.content, str):
                        logger.info(f"✅ Captured assistant content: {item.content[:100]}...")
                        output_buffer.append(item.content)
                    else:
                        logger.warning("Assistant item has no extractable text content")
            except Exception as e:
                logger.error(f"Error in conversation_item_added handler: {e}")

        # Hook into say() method as alternative capture mechanism
        if hasattr(self, 'say'):
            original_say = self.say
            async def patched_say(text: str, *args, **kwargs):
                logger.info(f"✅ Agent said: {text[:100]}...")
                output_buffer.append(text)
                return await original_say(text, *args, **kwargs)
            self.say = patched_say

        # Call original start method with original args
        logger.debug("AgentSession hooks installed")
        return await original_start(self, *args, **kwargs)

    # Install the patch
    AgentSession.start = patched_start

    # Return cleanup function
    def cleanup():
        AgentSession.start = original_start
        logger.debug("AgentSession: Hooks cleaned up")

    return cleanup
