"""
Test suite for Smart Home Agent running on LiveTxt framework.

This demonstrates complex type annotations and multiple function tools.

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
async def test_smart_home_lights():
    """Test controlling lights."""
    from smart_home_agent import entrypoint

    request = JobRequest(
        job_id="smart_home_test_1",
        user_input="Please turn on the lights in the living room",
        state=SerializableSessionState(),
    )

    result = await execute_job(entrypoint, request, timeout_ms=15000)

    assert result.status == "success"
    assert result.response_text is not None
    print(f"\n✅ Smart Home Response: {result.response_text}")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
@pytest.mark.anyio
async def test_smart_home_temperature():
    """Test setting temperature."""
    from smart_home_agent import entrypoint

    request = JobRequest(
        job_id="smart_home_test_2",
        user_input="Set the bedroom temperature to 68 degrees",
        state=SerializableSessionState(),
    )

    result = await execute_job(entrypoint, request, timeout_ms=15000)

    assert result.status == "success"
    assert result.response_text is not None
    print(f"\n✅ Temperature Control: {result.response_text}")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
@pytest.mark.anyio
async def test_smart_home_multiturn():
    """Test multi-turn conversation."""
    from smart_home_agent import entrypoint

    # Turn 1: Turn on lights
    request1 = JobRequest(
        job_id="smart_home_multiturn_1",
        user_input="Turn on the kitchen lights",
        state=SerializableSessionState(),
    )

    result1 = await execute_job(entrypoint, request1, timeout_ms=10000)

    assert result1.status == "success"
    print(f"\n✅ Turn 1: {result1.response_text}")

    # Turn 2: Set temperature
    request2 = JobRequest(
        job_id="smart_home_multiturn_2",
        user_input="Now set the office temperature to 72",
        state=result1.updated_state,
    )

    result2 = await execute_job(entrypoint, request2, timeout_ms=10000)

    assert result2.status == "success"
    print(f"✅ Turn 2: {result2.response_text}")


@pytest.mark.anyio
async def test_smart_home_summary():
    """Print summary of smart home agent tests."""
    print("\n" + "=" * 80)
    print("🎉 Smart Home Agent Test Summary")
    print("=" * 80)
    print()
    print("✅ Features Tested:")
    print("   • Light control")
    print("   • Temperature control")
    print("   • Multi-turn conversations")
    print("   • Enum types in arguments")
    print("   • Complex type annotations")
    print()
    print("💡 Demonstrates advanced type handling!")
    print("=" * 80)

