"""
Test utility functions.

Provides helper functions for creating test data and assertions.
"""
from typing import Optional
from livetxt import JobRequest, JobResult, SerializableSessionState


def create_test_request(
    job_id: str,
    user_input: str,
    state: Optional[SerializableSessionState] = None,
    timeout_ms: int = 10000
) -> JobRequest:
    """
    Create a test JobRequest.
    
    Args:
        job_id: Unique job ID
        user_input: User's input text
        state: Optional conversation state
        timeout_ms: Timeout in milliseconds
        
    Returns:
        JobRequest ready for testing
    """
    if state is None:
        state = SerializableSessionState()
    
    return JobRequest(
        job_id=job_id,
        user_input=user_input,
        state=state,
        timeout_ms=timeout_ms
    )


def assert_successful_result(result: JobResult, min_response_length: int = 0):
    """
    Assert that a JobResult is successful.
    
    Args:
        result: The JobResult to check
        min_response_length: Minimum expected response length
        
    Raises:
        AssertionError: If result is not successful
    """
    assert result.status == "success", f"Expected success, got {result.status}: {result.error}"
    
    if min_response_length > 0:
        assert result.response_text is not None, "Expected response_text to be set"
        assert len(result.response_text) >= min_response_length, \
            f"Expected response length >= {min_response_length}, got {len(result.response_text)}"
    
    assert result.updated_state is not None, "Expected updated_state to be set"

