"""Tests for data models (SerializableSessionState, JobRequest, JobResult)."""
import pytest
from livetxt.models import SerializableSessionState, JobRequest, JobResult


@pytest.fixture
def sample_chat_history():
    """Sample chat history for testing."""
    from livekit.agents.llm import ChatContext
    
    # Create a proper ChatContext and serialize it
    chat_ctx = ChatContext.empty()
    chat_ctx.add_message(role="system", content="You are a helpful assistant.")
    chat_ctx.add_message(role="user", content="Hello!")
    chat_ctx.add_message(role="assistant", content="Hi there! How can I help you?")
    
    # Return the serialized items
    return chat_ctx.to_dict()["items"]


class TestSerializableSessionState:
    """Test the SerializableSessionState model."""
    
    def test_create_empty_state(self):
        """Test creating an empty state."""
        state = SerializableSessionState()
        assert state.chat_items == []
        assert state.metadata == {}
    
    def test_create_state_with_history(self, sample_chat_history):
        """Test creating a state with chat history."""
        state = SerializableSessionState(
            chat_items=sample_chat_history,
            metadata={"session_id": "test_123"}
        )
        assert len(state.chat_items) == 3
        assert state.chat_items[0]["type"] == "message"
        assert state.chat_items[0]["role"] == "system"
        assert state.metadata["session_id"] == "test_123"
    
    def test_serialization_round_trip(self, sample_chat_history):
        """Test that state can be serialized and deserialized."""
        state = SerializableSessionState(
            chat_items=sample_chat_history,
            metadata={"key": "value"}
        )
        
        # Serialize to dict
        state_dict = state.model_dump()
        
        # Deserialize back
        restored = SerializableSessionState(**state_dict)
        
        assert len(restored.chat_items) == len(state.chat_items)
        assert restored.metadata == state.metadata
    
    def test_to_chat_context(self, sample_chat_history):
        """Test converting state to ChatContext."""
        state = SerializableSessionState(chat_items=sample_chat_history)
        
        # This will test that we can properly convert to livekit ChatContext
        chat_ctx = state.to_chat_context()
        
        assert len(chat_ctx.items) == 3
        # Chat items have dynamic IDs, so we check by type
        assert all(item.type == "message" for item in chat_ctx.items)
        # Verify roles
        roles = [item.role for item in chat_ctx.items]
        assert "system" in roles
        assert "user" in roles
        assert "assistant" in roles
    
    def test_from_chat_context(self, sample_chat_history):
        """Test creating state from ChatContext."""
        from livekit.agents.llm import ChatContext
        
        # Create a ChatContext
        chat_ctx = ChatContext.empty()
        chat_ctx.add_message(role="system", content="You are helpful.")
        chat_ctx.add_message(role="user", content="Hi!")
        
        # Convert to SerializableSessionState
        state = SerializableSessionState.from_chat_context(chat_ctx)
        
        assert len(state.chat_items) == 2


class TestJobRequest:
    """Test the JobRequest model."""
    
    def test_create_job_request(self):
        """Test creating a job request."""
        request = JobRequest(
            job_id="job_123",
            user_input="Hello, how are you?",
            state=SerializableSessionState()
        )
        
        assert request.job_id == "job_123"
        assert request.user_input == "Hello, how are you?"
        assert request.state.chat_items == []
    
    def test_job_request_with_state(self, sample_chat_history):
        """Test creating a job request with existing state."""
        state = SerializableSessionState(chat_items=sample_chat_history)
        request = JobRequest(
            job_id="job_456",
            user_input="What's the weather?",
            state=state
        )
        
        assert len(request.state.chat_items) == 3


class TestJobResult:
    """Test the JobResult model."""
    
    def test_create_success_result(self):
        """Test creating a successful job result."""
        result = JobResult(
            job_id="job_123",
            status="success",
            response_text="Hello! How can I help you today?",
            updated_state=SerializableSessionState()
        )
        
        assert result.status == "success"
        assert result.response_text is not None
        assert result.error is None
    
    def test_create_error_result(self):
        """Test creating an error result."""
        result = JobResult(
            job_id="job_123",
            status="error",
            error="LLM timeout",
            updated_state=None
        )
        
        assert result.status == "error"
        assert result.error == "LLM timeout"
        assert result.response_text is None
    
    def test_serialize_result(self):
        """Test serializing a result."""
        result = JobResult(
            job_id="job_123",
            status="success",
            response_text="Test response",
            updated_state=SerializableSessionState(
                chat_items=[],
                metadata={"test": "value"}
            )
        )
        
        result_dict = result.model_dump()
        assert result_dict["job_id"] == "job_123"
        assert result_dict["status"] == "success"
        assert result_dict["response_text"] == "Test response"

