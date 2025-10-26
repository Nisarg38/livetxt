# LiveTxt Examples

This directory contains example agents that demonstrate how to use the LiveTxt framework to run LiveKit agents in text-only mode.

## Structure

Each example follows the drive-thru pattern where tests are co-located with the agent:

```
examples/
├── weather-agent/
│   ├── weather_agent.py         # The agent implementation
│   └── test_weather_agent.py     # Tests for the agent
├── customer-support/
│   ├── customer_support_agent.py
│   └── test_customer_support.py
├── smart-home/
│   ├── smart_home_agent.py
│   └── test_smart_home.py
└── drive-thru/
    ├── drivethru_agent.py
    ├── database.py
    ├── order.py
    └── test_agent.py
```

## Running Tests

### Run All Example Tests

```bash
# From the project root
pytest examples/ -v
```

### Run Specific Example Tests

```bash
# Weather agent tests
pytest examples/weather-agent/ -v

# Customer support tests
pytest examples/customer-support/ -v

# Smart home tests
pytest examples/smart-home/ -v

# Drive-thru tests
pytest examples/drive-thru/ -v
```

## Key Concepts

### Zero Code Changes

All agents are **standard LiveKit agents** with ZERO modifications. They work seamlessly with both:

1. **LiveKit (Voice Mode)** - Original voice/video functionality
2. **LiveTxt (Text Mode)** - SMS/chat functionality via the framework

### The Only Change: Test Wrapper

To test an agent with LiveTxt, you only need to wrap it:

```python
from livetxt import execute_job, JobRequest, SerializableSessionState
from weather_agent import entrypoint  # ← Your unchanged agent

request = JobRequest(
    job_id="test_1",
    user_input="What's the weather?",
    state=SerializableSessionState()
)

result = await execute_job(entrypoint, request)
```

### State Preservation

Conversations maintain state across multiple turns:

```python
# Turn 1
result1 = await execute_job(entrypoint, request1, ...)

# Turn 2 - state carries over!
request2 = JobRequest(
    job_id="turn_2",
    user_input="What about Paris?",
    state=result1.updated_state  # ← State from turn 1
)
result2 = await execute_job(entrypoint, request2, ...)
```

## Examples Explained

### Weather Agent

**Features:**
- Function tools with async calls
- Real API integration (open-meteo)
- Complex argument types

**Use Case:** Demonstrates how agents with external API calls work in text mode.

### Customer Support Agent

**Features:**
- Multi-turn conversations
- Complex business logic
- Context-aware responses

**Use Case:** Shows how stateful agents handle complex workflows.

### Smart Home Agent

**Features:**
- Enum types in arguments
- Multiple function tools
- Literal type annotations

**Use Case:** Demonstrates advanced type handling in function calls.

### Drive-Thru Agent

**Features:**
- Complex order management
- Multiple menu categories
- Real-world business logic

**Use Case:** Comprehensive example of a production-ready agent.

## Testing Philosophy

These examples demonstrate that **real LiveKit agents** work with LiveTxt without modification. The tests validate:

1. ✅ Drop-in compatibility
2. ✅ State preservation
3. ✅ Multi-turn conversations
4. ✅ Error handling
5. ✅ Function tool execution

## Adding New Examples

To add a new example:

1. Create a folder: `examples/my-agent/`
2. Add agent file: `my_agent.py`
3. Add test file: `test_my_agent.py`
4. Add `__init__.py`

Follow the pattern shown in the existing examples!

## See Also

- [Main README](../README.md) - Project overview
- [Testing Guide](../internal-docs/README_TESTING.md) - Detailed testing docs
- [Quick Start](../internal-docs/QUICKSTART.md) - Getting started guide

