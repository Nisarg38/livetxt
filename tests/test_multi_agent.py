"""
Tests for multi-agent scenarios.

This module tests various patterns of using multiple agents
within a single entry point.
"""
import os

import pytest

# We'll need these imports once we implement AgentSession support
# For now, these tests will be marked as expected to fail (xfail)


@pytest.mark.anyio
@pytest.mark.xfail(reason="AgentSession support not yet implemented")
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
async def test_sequential_agents():
    """Test two agents running in sequence."""
    from livekit.agents import Agent, AgentSession, JobContext, function_tool
    from livekit.plugins import openai
    
    from livetxt import execute_job, JobRequest, SerializableSessionState
    
    class GreetingAgent(Agent):
        """Greets users and introduces the service."""
        
        def __init__(self):
            super().__init__(
                instructions="You are a friendly greeter. Keep it brief.",
                llm=openai.realtime.RealtimeModel()
            )
    
    class WeatherAgent(Agent):
        """Handles weather queries."""
        
        def __init__(self):
            super().__init__(
                instructions="You are a weather specialist. Be concise.",
                llm=openai.realtime.RealtimeModel()
            )
        
        @function_tool
        async def get_weather(self, context, location: str):
            """
            Get weather for a location.
            
            Args:
                location: City name
            """
            return f"Weather in {location}: Sunny, 72°F"
    
    async def entrypoint(ctx: JobContext):
        # Agent 1: Greeter
        greeter = GreetingAgent()
        session1 = AgentSession(llm=openai.realtime.RealtimeModel())
        await session1.start(agent=greeter, room=ctx.room)
        
        # Agent 2: Weather specialist
        weather = WeatherAgent()
        session2 = AgentSession(llm=openai.realtime.RealtimeModel())
        await session2.start(agent=weather, room=ctx.room)
    
    request = JobRequest(
        job_id="multi_agent_test",
        user_input="What's the weather in San Francisco?",
        state=SerializableSessionState()
    )
    
    result = await execute_job(entrypoint, request, timeout_ms=10000)
    
    # Both agents should have responded
    assert result.status == "success"
    assert result.response_text is not None
    
    # Should contain responses from both agents
    print(f"Multi-agent response: {result.response_text}")


@pytest.mark.anyio
@pytest.mark.xfail(reason="AgentSession support not yet implemented")
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
async def test_agent_routing():
    """Test router agent that dispatches to specialists."""
    from livekit.agents import Agent, AgentSession, JobContext
    from livekit.plugins import openai
    
    from livetxt import execute_job, JobRequest, SerializableSessionState
    
    class RouterAgent(Agent):
        """Routes requests to appropriate specialists."""
        
        def __init__(self):
            super().__init__(
                instructions="""
                Analyze the user's request and respond with ONLY:
                - "ROUTE_WEATHER" for weather questions
                - "ROUTE_GENERAL" for other questions
                """,
                llm=openai.realtime.RealtimeModel()
            )
    
    class WeatherAgent(Agent):
        """Handles weather queries."""
        
        def __init__(self):
            super().__init__(
                instructions="You are a weather specialist.",
                llm=openai.realtime.RealtimeModel()
            )
    
    async def entrypoint(ctx: JobContext):
        # Step 1: Router decides
        router = RouterAgent()
        router_session = AgentSession(llm=openai.realtime.RealtimeModel())
        await router_session.start(agent=router, room=ctx.room)
        
        # Step 2: Dispatch to specialist
        # In real implementation, would parse router response
        specialist = WeatherAgent()
        specialist_session = AgentSession(llm=openai.realtime.RealtimeModel())
        await specialist_session.start(agent=specialist, room=ctx.room)
    
    request = JobRequest(
        job_id="routing_test",
        user_input="How's the weather in Seattle?",
        state=SerializableSessionState()
    )
    
    result = await execute_job(entrypoint, request, timeout_ms=10000)
    
    assert result.status == "success"
    assert result.response_text is not None


@pytest.mark.anyio
@pytest.mark.xfail(reason="AgentSession support not yet implemented")
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
async def test_parallel_agents():
    """Test multiple agents running in parallel."""
    from livekit.agents import Agent, AgentSession, JobContext
    from livekit.plugins import openai
    
    from livetxt import execute_job, JobRequest, SerializableSessionState
    
    class GreetingAgent(Agent):
        """Greets users."""
        
        def __init__(self):
            super().__init__(
                instructions="You are a friendly greeter.",
                llm=openai.realtime.RealtimeModel()
            )
    
    class WeatherAgent(Agent):
        """Handles weather."""
        
        def __init__(self):
            super().__init__(
                instructions="You are a weather specialist.",
                llm=openai.realtime.RealtimeModel()
            )
    
    async def entrypoint(ctx: JobContext):
        import asyncio  # Import for isolated execution
        
        # Create both agents
        agent1 = GreetingAgent()
        agent2 = WeatherAgent()
        
        # Run in parallel
        async def run_agent_1():
            session = AgentSession(llm=openai.realtime.RealtimeModel())
            await session.start(agent=agent1, room=ctx.room)
        
        async def run_agent_2():
            session = AgentSession(llm=openai.realtime.RealtimeModel())
            await session.start(agent=agent2, room=ctx.room)
        
        # Run both simultaneously
        await asyncio.gather(run_agent_1(), run_agent_2())
    
    request = JobRequest(
        job_id="parallel_test",
        user_input="Hello!",
        state=SerializableSessionState()
    )
    
    result = await execute_job(entrypoint, request, timeout_ms=10000)
    
    # Both should have responded (order may vary)
    assert result.status == "success"
    assert result.response_text is not None


@pytest.mark.anyio
@pytest.mark.xfail(reason="AgentSession support not yet implemented")
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
async def test_multi_turn_agent_handoff():
    """Test conversation that switches between agents across turns."""
    from livekit.agents import Agent, AgentSession, JobContext
    from livekit.plugins import openai
    
    from livetxt import execute_job, JobRequest, SerializableSessionState
    
    class GreetingAgent(Agent):
        """Greets users."""
        
        def __init__(self):
            super().__init__(
                instructions="You are a friendly greeter.",
                llm=openai.realtime.RealtimeModel()
            )
    
    class WeatherAgent(Agent):
        """Handles weather queries."""
        
        def __init__(self):
            super().__init__(
                instructions="You are a weather specialist.",
                llm=openai.realtime.RealtimeModel()
            )
    
    async def greeter_entrypoint(ctx: JobContext):
        greeter = GreetingAgent()
        session = AgentSession(llm=openai.realtime.RealtimeModel())
        await session.start(agent=greeter, room=ctx.room)
    
    async def weather_entrypoint(ctx: JobContext):
        weather = WeatherAgent()
        session = AgentSession(llm=openai.realtime.RealtimeModel())
        await session.start(agent=weather, room=ctx.room)
    
    # Turn 1: Initial greeting
    request1 = JobRequest(
        job_id="turn1",
        user_input="Hello",
        state=SerializableSessionState()
    )
    result1 = await execute_job(greeter_entrypoint, request1)
    
    assert result1.status == "success"
    
    # Turn 2: Weather query (switch to weather agent)
    request2 = JobRequest(
        job_id="turn2",
        user_input="What's the weather?",
        state=result1.updated_state
    )
    result2 = await execute_job(weather_entrypoint, request2)
    
    assert result2.status == "success"


# Simple test that works NOW (no AgentSession)
@pytest.mark.anyio
async def test_multi_agent_simple_pattern():
    """
    Test multi-agent pattern with simple agents (no AgentSession).
    
    This demonstrates the architecture works for multi-agent scenarios
    even before we implement AgentSession support.
    """
    from livetxt import execute_job, JobRequest, SerializableSessionState
    
    # Track which agents ran
    agent_calls = []
    
    async def entrypoint(ctx):
        """Entrypoint with multiple agent-like handlers."""
        
        # "Agent 1": Greeter
        @ctx.room.on("data_received")
        async def greeter_handler(data, topic, participant):
            agent_calls.append("greeter")
            message = "Hello! Connecting you to specialist."
            ctx.room.local_participant.publish_data(
                message.encode("utf-8"),
                topic="lk.chat"
            )
        
        # "Agent 2": Specialist
        @ctx.room.on("data_received")
        async def specialist_handler(data, topic, participant):
            agent_calls.append("specialist")
            message = "I'm the specialist. How can I help?"
            ctx.room.local_participant.publish_data(
                message.encode("utf-8"),
                topic="lk.chat"
            )
        
        await ctx.connect()
    
    request = JobRequest(
        job_id="simple_multi_agent",
        user_input="Hello",
        state=SerializableSessionState()
    )
    
    result = await execute_job(entrypoint, request, timeout_ms=5000)
    
    assert result.status == "success"
    assert result.response_text is not None
    
    # Both handlers should have been called
    assert len(agent_calls) == 2
    assert "greeter" in agent_calls
    assert "specialist" in agent_calls
    
    # Both responses should be in output
    assert "Hello" in result.response_text
    assert "specialist" in result.response_text
    
    print(f"✅ Multi-agent simple pattern works: {result.response_text}")


@pytest.mark.anyio
async def test_conditional_agent_routing_simple():
    """
    Test conditional routing between different agent handlers.
    
    This works TODAY without AgentSession.
    """
    from livetxt import execute_job, JobRequest, SerializableSessionState
    
    async def entrypoint(ctx):
        """Route to different handlers based on input."""
        
        user_input = ctx.request.user_input.lower()
        
        if "weather" in user_input:
            # Weather agent
            @ctx.room.on("data_received")
            async def weather_handler(data, topic, participant):
                message = "The weather is sunny!"
                ctx.room.local_participant.publish_data(
                    message.encode("utf-8"),
                    topic="lk.chat"
                )
        elif "time" in user_input:
            # Time agent
            @ctx.room.on("data_received")
            async def time_handler(data, topic, participant):
                message = "The time is 3:00 PM"
                ctx.room.local_participant.publish_data(
                    message.encode("utf-8"),
                    topic="lk.chat"
                )
        else:
            # General agent
            @ctx.room.on("data_received")
            async def general_handler(data, topic, participant):
                message = "I'm a general assistant. How can I help?"
                ctx.room.local_participant.publish_data(
                    message.encode("utf-8"),
                    topic="lk.chat"
                )
        
        await ctx.connect()
    
    # Test 1: Weather query
    request1 = JobRequest(
        job_id="route_weather",
        user_input="What's the weather?",
        state=SerializableSessionState()
    )
    result1 = await execute_job(entrypoint, request1, timeout_ms=5000)
    
    assert result1.status == "success"
    assert "sunny" in result1.response_text.lower()
    
    # Test 2: Time query
    request2 = JobRequest(
        job_id="route_time",
        user_input="What time is it?",
        state=SerializableSessionState()
    )
    result2 = await execute_job(entrypoint, request2, timeout_ms=5000)
    
    assert result2.status == "success"
    assert "time" in result2.response_text.lower()
    
    # Test 3: General query
    request3 = JobRequest(
        job_id="route_general",
        user_input="Hello there",
        state=SerializableSessionState()
    )
    result3 = await execute_job(entrypoint, request3, timeout_ms=5000)
    
    assert result3.status == "success"
    assert "assistant" in result3.response_text.lower()
    
    print("✅ Conditional routing works for all 3 agent types")

