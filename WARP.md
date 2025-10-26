# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**LiveTxt** is a Python library that enables existing [livekit-agents](https://github.com/livekit/agents) to work in text-based channels (SMS, web chat, messaging apps) without rewriting agent logic. It provides a stateless execution layer that makes real-time voice agents compatible with asynchronous text messaging.

**Key Principle**: Drop-in compatibility. Existing LiveKit agent code should run with ZERO code changes.

## Development Commands

### Setup
```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_weather_agent.py -v

# Run tests with coverage
pytest --cov=livetxt --cov-report=html --cov-report=term tests/

# Run single test
pytest tests/test_weather_agent.py::test_weather_agent_import -v

# Run with verbose output
pytest tests/ -v -s --tb=short

# Skip tests requiring API keys
pytest tests/ -v -k "not real_api"
```

### Code Quality
```bash
# Format code
black livetxt/

# Lint with ruff
ruff check livetxt/
ruff check --fix livetxt/

# Type checking
mypy livetxt/

# All quality checks
black livetxt/ && ruff check --fix livetxt/ && mypy livetxt/
```

### Running Examples
```bash
# Run example agents (navigate to examples directory)
cd examples/weather-agent
python agent.py

# Each example directory has its own README with specific instructions
```

## Architecture

### Core Concept: Shim Layer

LiveTxt works by creating **fake LiveKit objects** that implement the same API as real LiveKit components. When an agent calls `ctx.room.local_participant.publish_data()`, we intercept it and capture the text output.

```
User Input (SMS/Chat)
    ↓
JobRequest (Pydantic model)
    ↓
execute_job() → Creates TextOnlyJobContext
    ↓
TextOnlyJobContext
  ├─ Fake Job object
  ├─ TextOnlyRoom (fake room)
  │   ├─ FakeParticipant (local agent)
  │   └─ FakeParticipant (remote user)
  └─ Event handlers registry
    ↓
Agent entrypoint runs (unchanged code)
    ↓
Agent publishes data → Captured by shim
    ↓
JobResult (response + updated state)
```

### Key Modules

#### `models.py` - Data Structures
- **`SerializableSessionState`**: Conversation state (chat history, metadata) that survives across turns
- **`JobRequest`**: Input to worker (user_input + state)
- **`JobResult`**: Output from worker (response_text + updated_state)

All use **Pydantic** for validation and serialization.

#### `worker.py` - Execution Engine
- **`execute_job()`**: Main entry point. Takes an agent entrypoint function and a JobRequest, returns JobResult
- **`TextOnlyJobContext`**: Fake `JobContext` that agents receive
- **`TextOnlyRoom`**: Fake `Room` that captures text output
- **`FakeParticipant`**: Minimal participant implementation

**Critical Pattern**: `publish_data()` must work both sync and async because agents often call it from sync event handlers.

#### `shim/` - LiveKit API Compatibility
- **`context.py`**: Extended shim objects for runtime mode (connects to gateway)
- **`patch.py`**: Monkey-patches LiveKit SDK to force text-only mode

#### `runtime.py` - Worker Daemon
- **`LiveTxtWorker`**: Connects to gateway, maintains active sessions
- Manages session lifecycle (create → run entrypoint → cleanup)

#### `client.py` - Gateway Communication
- **`LiveTxtClient`**: WebSocket client for communicating with livetxt-gateway
- Handles connection, message routing, and response delivery

### State Management

**Important**: State must survive across conversation turns.

```python
# Turn 1
request1 = JobRequest(
    job_id="turn1",
    user_input="My name is Alice",
    state=SerializableSessionState()
)
result1 = await execute_job(my_agent, request1)

# Turn 2 - MUST pass previous state
request2 = JobRequest(
    job_id="turn2", 
    user_input="What's my name?",
    state=result1.updated_state  # ← State from turn 1
)
result2 = await execute_job(my_agent, request2)
```

State is serialized using `ChatContext.to_dict()` and restored using `ChatContext.from_dict()`.

## Coding Standards

### Type Hints (MANDATORY)
All functions must have complete type hints. Use `from __future__ import annotations` for forward references.

```python
from __future__ import annotations
from typing import Any

async def execute_job(
    entrypoint: Callable[[Any], Any],
    request: JobRequest
) -> JobResult:
    ...
```

### Pydantic for Data Models
All data structures (requests, responses, state) use Pydantic models.

```python
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    field: str = Field(description="Field description")
    optional_field: int | None = None
```

### Named Parameters (3+ arguments)
When calling functions with 3+ parameters, use named arguments.

```python
# Good
result = JobResult(
    job_id=request.job_id,
    status="success",
    response_text=response,
    updated_state=state
)

# Bad
result = JobResult(request.job_id, "success", response, state)
```

### Docstrings (Required for Public APIs)
All public functions, classes, and methods need docstrings explaining purpose, args, returns, and exceptions.

```python
async def execute_job(
    entrypoint: Callable[[Any], Any],
    request: JobRequest
) -> JobResult:
    """
    Execute an agent entrypoint in text-only mode.
    
    Args:
        entrypoint: Agent entrypoint function (standard livekit-agents signature)
        request: Job request containing user input and state
        
    Returns:
        JobResult with agent response and updated state
        
    Raises:
        TimeoutError: If execution exceeds timeout_ms
    """
```

### Async/Await Patterns
LiveTxt is fully async. Be careful with sync vs async contexts:

```python
# Agent handlers are often sync
@ctx.room.on("data_received")
def handle_message(data, topic, participant):
    # Sync function - can't use await
    ctx.room.local_participant.publish_data(data)

# But publish_data needs to work async internally
# Solution: Schedule as task in event loop
asyncio.create_task(self._async_publish(data))
```

## Testing Requirements

### Test Structure
- **Unit tests**: `test_models.py`, `test_runtime.py`
- **Integration tests**: `test_livekit_examples.py`, `test_weather_agent.py`
- **Fixtures**: Reusable test agents in `tests/fixtures/`
- **Helpers**: Test utilities in `tests/helpers/`

### Writing Tests
All new features MUST have tests. Tests should:

1. **Test with ZERO agent code changes** - Verify drop-in compatibility
2. **Use MockLLM when possible** - Avoid API costs in CI
3. **Test multi-turn conversations** - State preservation is critical
4. **Test error handling** - Not just happy paths
5. **Mark API tests appropriately** - Use `@pytest.mark.skipif` for optional tests

```python
import pytest
from livetxt import execute_job, JobRequest, SerializableSessionState

@pytest.mark.anyio
async def test_my_feature():
    """Test description."""
    request = JobRequest(
        job_id="test_1",
        user_input="Hello",
        state=SerializableSessionState()
    )
    
    result = await execute_job(my_agent, request)
    
    assert result.status == "success"
    assert result.response_text is not None
```

### Running Tests Before Committing
Always run tests and linting before committing:

```bash
# Full quality check
pytest tests/ -v && black livetxt/ && ruff check --fix livetxt/
```

## Common Development Tasks

### Adding a New Feature to the Shim Layer
1. Check what LiveKit API the agent expects
2. Implement minimal fake version in `worker.py` or `shim/context.py`
3. Test with an actual LiveKit example agent
4. Add tests to verify compatibility

### Debugging Agent Compatibility Issues
1. Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`
2. Check what events the agent registers: Look for `@ctx.room.on("event_name")`
3. Verify fake objects have required attributes: Add missing attrs to FakeParticipant/TextOnlyRoom
4. Test with `pytest tests/ -v -s` to see all output

### Adding Support for New LiveKit Agent Patterns
1. Find example agent in `livekit-agents` repo or examples
2. Copy to `tests/fixtures/` or `examples/`
3. Run it with `execute_job()` - see what breaks
4. Implement missing APIs in shim layer
5. Add integration test to `test_livekit_examples.py`

## Project Structure Reference

```
livetxt/
├── livetxt/              # Core library
│   ├── __init__.py       # Public API exports
│   ├── models.py         # Pydantic models (JobRequest, JobResult, State)
│   ├── worker.py         # Stateless execution (execute_job)
│   ├── runtime.py        # Worker daemon (connects to gateway)
│   ├── client.py         # Gateway WebSocket client
│   ├── config.py         # Configuration
│   └── shim/             # LiveKit API compatibility
│       ├── context.py    # Extended fake objects for runtime
│       └── patch.py      # SDK monkey-patching
├── tests/                # Comprehensive test suite
│   ├── fixtures/         # Test agent examples
│   ├── helpers/          # Test utilities
│   └── test_*.py         # Test files
├── examples/             # Example agents (weather, smart-home, etc.)
├── internal-docs/        # Internal documentation (PRD, planning docs)
├── pyproject.toml        # Project config
└── README.md             # User documentation
```

## Important Patterns

### Event Handler Registration
Agents register handlers using decorators:

```python
@ctx.room.on("data_received")
def handle_message(data: bytes, topic: str, participant):
    # Handle message
    pass
```

Our shim must:
1. Store handlers in `_event_handlers` dict
2. Call them when events are emitted
3. Support both sync and async handlers

### Message Injection Timing
Critical: User message must be injected AFTER agent sets up handlers.

```python
async def connect(self):
    self._connected = True
    # Schedule message injection with delay
    asyncio.create_task(self._inject_user_message())

async def _inject_user_message(self):
    await asyncio.sleep(0.3)  # Let agent set up handlers
    # Now inject message
    await self._emit_event("data_received", data, topic, participant)
```

### Capturing Agent Output
Agent calls `publish_data()` → We intercept → Store in output buffer.

```python
def _capture_agent_output(self, data: bytes, *, topic: str = "", reliable: bool = True):
    message = data.decode("utf-8")
    self._output_buffer.append(message)
    logger.debug(f"Captured: {message}")
```

## Dependencies

- **livekit-agents** (>=0.9.0): Core SDK we're shimming
- **pydantic** (>=2.0.0): Data validation
- **aiohttp** (>=3.9.0): HTTP client for gateway

## Known Limitations

1. **AgentSession/LLM agents**: In progress, not fully working yet
2. **Function tools**: Planned, not yet implemented
3. **Audio/Video**: Explicitly not supported (text-only by design)
4. **Real-time features**: Not supported (stateless/async by design)

## Performance Expectations

- **Processing overhead**: <50ms (excluding LLM calls)
- **State serialization**: <10ms for typical conversations
- **Test execution**: All tests should pass in <60 seconds

## Security Considerations

- Never hardcode API keys - use environment variables
- Sanitize user input before passing to LLM
- Validate all Pydantic models at runtime
- Log errors but don't expose internal details to users

## Questions to Ask

Before implementing:
- Does this maintain drop-in compatibility with existing agents?
- Will this work with the stateless execution model?
- Can this be tested without external API calls?
- Does this follow existing patterns in the codebase?

When debugging:
- What LiveKit API does the agent expect?
- Are event handlers being registered properly?
- Is the message injection timing correct?
- Is state being preserved across turns?
