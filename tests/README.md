# LiveTxt Test Suite

Comprehensive test suite for LiveTxt - testing that LiveKit agents work in text-only mode.

## 📁 Directory Structure

```
tests/
├── README.md                      # This file
├── conftest.py                    # Pytest configuration
├── __init__.py                    # Test package initialization
│
├── fixtures/                      # Test agent examples
│   ├── __init__.py
│   └── weather_agent.py          # Weather agent for testing
│
├── helpers/                       # Test utilities
│   ├── __init__.py
│   ├── mock_helpers.py           # Mock objects (HTTP, API responses)
│   └── test_utils.py             # Test helper functions
│
├── test_weather_agent.py         # ⭐ Comprehensive weather agent tests
├── test_livekit_examples.py      # Integration tests with examples/
├── test_runtime.py               # Core runtime tests
├── test_models.py                # Data model tests
├── test_mock_llm.py              # MockLLM tests
└── test_multi_agent.py           # Multi-agent pattern tests
```

## 🎯 Test Categories

### 1. Unit Tests
- **test_models.py** - Tests for JobRequest, JobResult, SerializableSessionState
- **test_mock_llm.py** - Tests for MockLLM and MockFunctionCallingLLM

### 2. Runtime Tests
- **test_runtime.py** - Core execute_job() functionality
- **test_multi_agent.py** - Multi-agent patterns

### 3. Integration Tests
- **test_weather_agent.py** - Comprehensive weather agent testing (⭐ **START HERE**)
- **test_livekit_examples.py** - Tests real examples from examples/ folder

## 🚀 Running Tests

### Run All Tests
```bash
cd livetxt
pytest tests/ -v
```

### Run Specific Test File
```bash
# Weather agent tests (comprehensive)
pytest tests/test_weather_agent.py -v

# Only tests that don't need API keys
pytest tests/test_weather_agent.py -v -k "not real_api"

# With output
pytest tests/test_weather_agent.py -v -s
```

### Run Specific Test
```bash
pytest tests/test_weather_agent.py::test_weather_agent_import -v
```

### Run Tests That Require API Keys
```bash
# Set your OpenAI API key
export OPENAI_API_KEY=sk-...

# Run all tests (including API tests)
pytest tests/test_weather_agent.py -v
```

## 📝 Test Coverage

### test_weather_agent.py (⭐ Main Test File)

Comprehensive testing of a real LiveKit voice agent with LiveTxt:

#### ✅ Basic Functionality
- `test_weather_agent_import` - Agent imports correctly
- `test_weather_agent_structure` - Agent has proper structure

#### ✅ Mock LLM Tests (No API Keys Needed)
- `test_weather_with_mock_llm_simple` - Simple greeting with MockLLM
- `test_weather_with_mock_function_calling_llm` - Function calling with MockLLM

#### ✅ Real API Tests (Requires OPENAI_API_KEY)
- `test_weather_basic_real_api` - Basic weather query
- `test_weather_multiple_locations` - Multiple location queries
- `test_weather_multiturn_conversation` - Multi-turn conversation with state
- `test_weather_compare_locations` - Context-aware follow-up questions

#### ✅ Error Handling & Edge Cases
- `test_weather_api_error_handling` - Handles API failures gracefully
- `test_weather_unclear_input` - Handles unclear/vague input
- `test_weather_timeout_handling` - Respects timeout settings

#### ✅ State Management
- `test_weather_state_serialization` - State survives serialization
- `test_weather_empty_state_handling` - Works with empty state

#### ✅ Integration Tests
- `test_weather_full_conversation_flow` - Complete conversation flow

#### ✅ Performance Tests
- `test_weather_processing_performance` - Validates processing times

### test_livekit_examples.py

Tests the actual example agents in `examples/` folder:
- Weather agent
- Smart home agent
- Customer support agent

## 🧪 Fixtures and Helpers

### Fixtures (tests/fixtures/)

Reusable test agents that mimic real LiveKit agents:

```python
from tests.fixtures import WeatherAgent, weather_entrypoint

# Use in your tests
result = await execute_job(weather_entrypoint, request)
```

### Helpers (tests/helpers/)

Utility functions for testing:

```python
from tests.helpers import (
    create_mock_weather_response,
    create_mock_http_session,
    create_test_request,
    assert_successful_result
)

# Create test data
request = create_test_request("job_1", "What's the weather?")
mock_session = create_mock_http_session(status=200)

# Assertions
assert_successful_result(result, min_response_length=10)
```

## 🎓 Writing New Tests

### Template for New Agent Tests

```python
import pytest
from livetxt import execute_job, JobRequest, SerializableSessionState
from tests.helpers import create_test_request, assert_successful_result
from tests.fixtures import your_agent_entrypoint

@pytest.mark.anyio
async def test_your_agent_basic():
    """Test your agent with basic input."""
    request = create_test_request(
        job_id="test_1",
        user_input="Your test input here"
    )
    
    result = await execute_job(your_agent_entrypoint, request)
    
    assert_successful_result(result)
    print(f"✅ Response: {result.response_text}")
```

### Testing with MockLLM

```python
from livetxt import MockLLM
from unittest.mock import patch

@pytest.mark.anyio
async def test_with_mock_llm():
    """Test without needing API keys."""
    mock_llm = MockLLM(responses=["Test response"])
    
    with patch('livekit.plugins.openai.realtime.RealtimeModel', return_value=mock_llm):
        result = await execute_job(entrypoint, request)
        assert result.status == "success"
```

### Testing Multi-Turn Conversations

```python
@pytest.mark.anyio
async def test_multiturn():
    """Test conversation with state preservation."""
    # Turn 1
    result1 = await execute_job(entrypoint, request1)
    
    # Turn 2 - pass previous state
    request2 = create_test_request(
        job_id="turn_2",
        user_input="Follow-up question",
        state=result1.updated_state  # ← State from turn 1
    )
    result2 = await execute_job(entrypoint, request2)
    
    # Verify state grew
    assert len(result2.updated_state.chat_items) > len(result1.updated_state.chat_items)
```

## 🐛 Debugging Tests

### Verbose Output
```bash
pytest tests/test_weather_agent.py -v -s --tb=short
```

### Run Single Test with Full Output
```bash
pytest tests/test_weather_agent.py::test_weather_basic_real_api -v -s --tb=long
```

### See All Logs
```bash
pytest tests/ -v -s --log-cli-level=DEBUG
```

## 📊 Test Statistics

Current test coverage (as of October 2025):

| Test File | Tests | Passing | Coverage |
|-----------|-------|---------|----------|
| test_weather_agent.py | 15 | 15 ✅ | Weather agent |
| test_livekit_examples.py | 9 | 9 ✅ | Examples integration |
| test_runtime.py | 5 | 5 ✅ | Core runtime |
| test_models.py | 10 | 10 ✅ | Data models |
| test_mock_llm.py | 3 | 3 ✅ | Mock utilities |
| test_multi_agent.py | 2 | 2 ✅ | Multi-agent |
| **Total** | **44+** | **44+ ✅** | **Comprehensive** |

## 🎯 Key Testing Principles

1. **ZERO Code Changes** - Tests verify that real LiveKit agents work without modification
2. **Mock When Possible** - Use MockLLM to avoid API costs
3. **Test Real APIs** - But mark with `@pytest.mark.skipif` for optional execution
4. **State Preservation** - Always test multi-turn conversations
5. **Error Handling** - Test failure scenarios, not just happy path
6. **Performance** - Validate processing times are reasonable

## 📚 Additional Resources

- **[Main README](../README.md)** - Project overview
- **[QUICKSTART](../internal-docs/QUICKSTART.md)** - Getting started guide

## 🤝 Contributing Tests

When adding new tests:

1. Follow the existing patterns in `test_weather_agent.py`
2. Add helper functions to `tests/helpers/` if reusable
3. Add test agents to `tests/fixtures/` if needed
4. Update this README with new test descriptions
5. Ensure tests work both with and without API keys

---

**Questions?** Check the test files themselves - they're heavily documented with examples!

