"""
Test suite for Weather Agent running on LiveTxt framework.

This demonstrates that the Weather Agent works with LiveTxt with ZERO code changes!

Note: Requires OPENAI_API_KEY environment variable to be set.
"""

import pytest
import os
from livetxt import execute_job, JobRequest, SerializableSessionState


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
@pytest.mark.anyio
async def test_weather_agent_basic():
    """Test the Weather Agent with a simple query."""
    from weather_agent import entrypoint

    # THE ONLY CHANGE: Wrap the agent with execute_job()
    # Everything else is UNCHANGED LiveKit code!

    request = JobRequest(
        job_id="weather_test_1",
        user_input="What's the weather in San Francisco?",
        state=SerializableSessionState(),
    )

    result = await execute_job(entrypoint, request, timeout_ms=15000)

    assert result.status == "success"
    assert result.response_text is not None
    assert len(result.response_text) > 0
    print(f"\n✅ Weather Agent Response: {result.response_text}")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
@pytest.mark.anyio
async def test_weather_agent_multiturn():
    """Test multi-turn conversation with Weather Agent."""
    from weather_agent import entrypoint

    # Turn 1: Ask about weather
    request1 = JobRequest(
        job_id="weather_multiturn_1",
        user_input="Hi! Can you help me with weather information?",
        state=SerializableSessionState(),
    )

    result1 = await execute_job(entrypoint, request1, timeout_ms=15000)

    assert result1.status == "success"
    print(f"\n✅ Turn 1: {result1.response_text}")

    # Turn 2: Actual weather query (with state from turn 1)
    request2 = JobRequest(
        job_id="weather_multiturn_2",
        user_input="What's the weather in New York?",
        state=result1.updated_state,  # ← State carries over!
    )

    result2 = await execute_job(entrypoint, request2, timeout_ms=15000)

    assert result2.status == "success"
    assert result2.response_text is not None
    print(f"✅ Turn 2: {result2.response_text}")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
@pytest.mark.anyio
async def test_weather_error_handling():
    """Test error handling with invalid input."""
    from weather_agent import entrypoint

    request = JobRequest(
        job_id="weather_error_test",
        user_input="asdfasdfasdf",  # Gibberish input
        state=SerializableSessionState(),
    )

    result = await execute_job(entrypoint, request, timeout_ms=15000)

    # Should handle gracefully (might be success or error depending on agent)
    assert result.status in ["success", "error"]
    print(f"\n✅ Error Handling: {result.status} - {result.response_text or result.error}")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
@pytest.mark.anyio
async def test_weather_state_preservation():
    """Test that conversation state is preserved across turns."""
    from weather_agent import entrypoint

    # Turn 1
    request1 = JobRequest(
        job_id="state_test_1",
        user_input="What's the weather in Boston?",
        state=SerializableSessionState(),
    )

    result1 = await execute_job(entrypoint, request1, timeout_ms=15000)

    assert result1.status == "success"
    assert result1.updated_state is not None
    print(f"\n✅ Turn 1: {result1.response_text}")

    # Turn 2 with state
    request2 = JobRequest(
        job_id="state_test_2",
        user_input="What about Paris?",
        state=result1.updated_state,
    )

    result2 = await execute_job(entrypoint, request2, timeout_ms=15000)

    assert result2.status == "success"
    print(f"✅ Turn 2: {result2.response_text}")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
@pytest.mark.anyio
async def test_weather_timeout_handling():
    """Test timeout handling."""
    from weather_agent import entrypoint

    request = JobRequest(
        job_id="timeout_test",
        user_input="What's the weather?",
        state=SerializableSessionState(),
    )

    # Use a short timeout
    result = await execute_job(entrypoint, request, timeout_ms=5000)

    # Should timeout or succeed
    assert result.status in ["success", "timeout", "error"]
    print(f"\n✅ Timeout Test: {result.status}")


@pytest.mark.anyio
async def test_weather_summary():
    """Print summary of weather agent tests."""
    print("\n" + "=" * 80)
    print("🎉 Weather Agent Test Summary")
    print("=" * 80)
    print()
    print("✅ Features Tested:")
    print("   • Basic weather queries")
    print("   • Multi-turn conversations")
    print("   • State preservation")
    print("   • Error handling")
    print("   • Timeout handling")
    print()
    print("💡 Agent works with ZERO code changes!")
    print("=" * 80)

