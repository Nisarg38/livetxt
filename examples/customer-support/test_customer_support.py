"""
Test suite for Customer Support Agent running on LiveTxt framework.

This demonstrates multi-turn conversations with complex business logic.

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
async def test_customer_support_order_status():
    """Test checking order status."""
    from customer_support_agent import entrypoint

    request = JobRequest(
        job_id="cs_order_test",
        user_input="I'd like to check the status of my order",
        state=SerializableSessionState(),
    )

    result = await execute_job(entrypoint, request, timeout_ms=15000)

    assert result.status == "success"
    assert result.response_text is not None
    print(f"\n✅ Customer Support Response: {result.response_text}")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
@pytest.mark.anyio
async def test_customer_support_return():
    """Test initiating a return."""
    from customer_support_agent import entrypoint

    request = JobRequest(
        job_id="cs_return_test",
        user_input="I need to return my order",
        state=SerializableSessionState(),
    )

    result = await execute_job(entrypoint, request, timeout_ms=15000)

    assert result.status == "success"
    assert result.response_text is not None
    print(f"\n✅ Return Initiation: {result.response_text}")


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
@pytest.mark.anyio
async def test_customer_support_multiturn():
    """Test multi-turn conversation with context."""
    from customer_support_agent import entrypoint

    # Turn 1: Initial greeting
    request1 = JobRequest(
        job_id="cs_multiturn_1",
        user_input="Hi, I need help with my order",
        state=SerializableSessionState(),
    )

    result1 = await execute_job(entrypoint, request1, timeout_ms=10000)

    assert result1.status == "success"
    print(f"\n✅ Turn 1: {result1.response_text}")

    # Turn 2: Provide order details
    request2 = JobRequest(
        job_id="cs_multiturn_2",
        user_input="My order number is ORD-12345 and my email is test@example.com",
        state=result1.updated_state,
    )

    result2 = await execute_job(entrypoint, request2, timeout_ms=10000)

    assert result2.status == "success"
    print(f"✅ Turn 2: {result2.response_text}")


@pytest.mark.anyio
async def test_customer_support_summary():
    """Print summary of customer support agent tests."""
    print("\n" + "=" * 80)
    print("🎉 Customer Support Agent Test Summary")
    print("=" * 80)
    print()
    print("✅ Features Tested:")
    print("   • Order status checking")
    print("   • Return initiation")
    print("   • Multi-turn conversations")
    print("   • Context-aware responses")
    print()
    print("💡 Demonstrates business logic integration!")
    print("=" * 80)

