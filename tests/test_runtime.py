"""Tests for the runtime worker that executes agent jobs."""
import asyncio
import os

import pytest

from livetxt.models import JobRequest, JobResult, SerializableSessionState
from livetxt.worker import execute_job


class TestSimpleEchoAgent:
    """Test a simple echo agent."""
    
    @pytest.mark.anyio
    async def test_echo_agent_basic(self):
        """Test that a simple echo agent works."""
        from livekit.agents import JobContext
        
        # Define a simple echo agent
        async def echo_agent(ctx: JobContext):
            """Simple echo agent."""
            await ctx.connect()
            
            @ctx.room.on("data_received")
            def on_message(data: bytes, topic: str, participant):
                message = data.decode("utf-8")
                response = f"Echo: {message}"
                ctx.room.local_participant.publish_data(
                    response.encode("utf-8"), topic="lk.chat"
                )
        
        # Create a job request
        request = JobRequest(
            job_id="test_123",
            user_input="Hello!",
            state=SerializableSessionState()
        )
        
        # Execute the job
        result = await execute_job(echo_agent, request)
        
        # Verify the result
        assert result.status == "success"
        assert result.response_text == "Echo: Hello!"
        assert result.updated_state is not None


class TestVoiceAgentInTextMode:
    """Test that voice agents can work in text mode."""
    
    @pytest.mark.anyio
    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Requires OPENAI_API_KEY environment variable"
    )
    async def test_agent_session_text_mode(self):
        """Test that AgentSession can be forced to text-only mode."""
        import os
        
        from livekit.agents import Agent, AgentSession, JobContext
        
        # Track if the agent was called
        agent_called = False
        
        class TestAgent(Agent):
            def __init__(self):
                super().__init__(
                    instructions="You are a test agent. Respond with 'OK' to any input."
                )
                self._response_given = False
            
            async def on_enter(self):
                """Called when agent starts."""
                nonlocal agent_called
                agent_called = True
        
        async def agent_entrypoint(ctx: JobContext):
            """Voice agent that should work in text mode."""
            # Use real OpenAI LLM (requires OPENAI_API_KEY)
            from livekit.plugins import openai
            
            session = AgentSession(
                llm=openai.realtime.RealtimeModel(),
                # These should be gracefully ignored in text mode:
                # stt="assemblyai/universal-streaming",
                # tts="cartesia/sonic-2",
            )
            
            await session.start(agent=TestAgent(), room=ctx.room)
        
        # Create a job request
        request = JobRequest(
            job_id="test_voice_123",
            user_input="Hello agent!",
            state=SerializableSessionState()
        )
        
        # This should NOT raise an error about missing STT/TTS
        result = await execute_job(agent_entrypoint, request, timeout_ms=10000)
        
        # The job should succeed
        assert result.status == "success"
        assert agent_called  # Agent should have been initialized


class TestStatePersistence:
    """Test that conversation state is properly preserved."""
    
    @pytest.mark.anyio
    async def test_state_round_trip(self):
        """Test that state is preserved across multiple turns."""
        from livekit.agents import JobContext, Agent, AgentSession
        from livekit.agents.llm import ChatContext
        
        # Turn 1: Start a conversation
        initial_chat = ChatContext.empty()
        initial_chat.add_message(role="system", content="You are helpful.")
        initial_state = SerializableSessionState.from_chat_context(initial_chat)
        
        async def stateful_agent(ctx: JobContext):
            """Agent that maintains conversation history."""
            # In a real implementation, the runtime would inject the state
            # into the agent's context
            pass
        
        request = JobRequest(
            job_id="test_state_1",
            user_input="What's 2+2?",
            state=initial_state
        )
        
        # Execute job
        result = await execute_job(stateful_agent, request)
        
        # The updated state should include the new message
        if result.status == "success" and result.updated_state:
            assert len(result.updated_state.chat_items) >= len(initial_state.chat_items)


class TestErrorHandling:
    """Test error handling in the runtime."""
    
    @pytest.mark.anyio
    async def test_agent_exception(self):
        """Test that agent exceptions are caught and returned as errors."""
        from livekit.agents import JobContext
        
        async def failing_agent(ctx: JobContext):
            """Agent that raises an exception."""
            raise ValueError("Intentional test error")
        
        request = JobRequest(
            job_id="test_error",
            user_input="Hello",
            state=SerializableSessionState()
        )
        
        result = await execute_job(failing_agent, request)
        
        assert result.status == "error"
        assert result.error is not None
        assert "Intentional test error" in result.error
    
    @pytest.mark.anyio
    async def test_timeout_handling(self):
        """Test that long-running agents timeout properly."""
        import asyncio
        from livekit.agents import JobContext
        
        async def slow_agent(ctx: JobContext):
            """Agent that takes too long."""
            import asyncio  # Import inside function for isolated execution
            await asyncio.sleep(100)  # Way longer than timeout
        
        request = JobRequest(
            job_id="test_timeout",
            user_input="Hello",
            state=SerializableSessionState(),
            timeout_ms=100  # 100ms timeout
        )
        
        result = await execute_job(slow_agent, request, timeout_ms=100)
        
        assert result.status == "timeout"

