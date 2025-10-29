# LiveTxt: Run LiveKit Agents with SMS, Chat, and API Channels

Run your existing **LiveKit agents** across any text channel (like **SMS**, chat, or API) without modifying your agent code. **LiveTxt** extends **LiveKit**'s real-time voice and video capabilities to text, enabling channel-agnostic **AI agents** for **SMS** and other messaging platforms. Enjoy drop-in compatibility with `livekit-agents`.

- Channel-agnostic by design (voice/video via LiveKit, text/API via LiveTxt)
- Drop-in compatibility with livekit-agents (no agent rewrites)
- Stateless text execution (each turn in → result out)

## Aim and vision

A single agents/multi-agent system API (livekit-agents) that runs on any channel.

- One codebase → many channels
- Works for single agents and coordinating multi-agent entrypoints
- LiveKit handles real-time voice/video; LiveTxt handles chat, SMS, and API
- Keep agent code identical; switch runtimes by channel

## Channels

- Voice/Video: LiveKit room runtime
- Chat/SMS/API: LiveTxt `execute_job()`

## Install

```bash
pip install -e .
# or with dev tools
pip install -e ".[dev]"
```

## Quick start: HTTP Worker

The easiest way to run an agent is with the built-in HTTP server that **auto-loads** your agent:

```bash
# Start worker (agent auto-loads on startup)
python -m livetxt.cli serve examples/weather-agent/weather_agent.py --port 8081

# Agent is ready to receive requests - no manual loading needed!
```

Then send requests from the gateway or directly:

```bash
curl -X POST http://localhost:8081/execute \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req_1",
    "session_id": "session_1",
    "user_id": "user_1",
    "message": "What's the weather?"
  }'
```

## Quick start: Programmatic

Define your agent exactly as you do for livekit-agents, then execute it with a user message.

```python
from livetxt import execute_job, JobRequest, SerializableSessionState
from livekit.agents import JobContext

async def my_agent(ctx: JobContext):
    await ctx.connect()

    @ctx.room.on("data_received")
    def handle_message(data: bytes, topic: str, participant):
        msg = data.decode("utf-8")
        ctx.room.local_participant.publish_data(
            f"You said: {msg}".encode("utf-8"),
            topic="lk.chat",
        )

request = JobRequest(
    job_id="conversation_123",
    user_input="Hello!",
    state=SerializableSessionState(),
)

result = await execute_job(my_agent, request)
print(result.response_text)  # You said: Hello!
```

### Multi‑turn

Pass the previous turn's state into the next request.

```python
# turn 1
r1 = JobRequest(job_id="t1", user_input="My name is Alice", state=SerializableSessionState())
res1 = await execute_job(my_agent, r1)

# turn 2
r2 = JobRequest(job_id="t2", user_input="What's my name?", state=res1.updated_state)
res2 = await execute_job(my_agent, r2)
```

## How it works (brief)

- `execute_job()` creates a text‑only JobContext with a fake Room and Participant.
- Your agent registers handlers (e.g., `data_received`).
- The user message is injected after handlers are registered.
- When your agent calls `publish_data()`, the text is captured and returned as a `JobResult`.

## What works today

- Single-agent and multi-agent entrypoints (multiple handlers/agents)
- Text agents using `ctx.room.on("data_received")`
- Multi‑turn conversations via `SerializableSessionState`

Not yet:
- Agents built on `AgentSession` + LLM
- Function/tool calling
- Audio/video (handled by LiveKit runtime)

## Examples

See `examples/` for runnable agents. A good place to start:
- `examples/weather-agent/`

Each example folder includes its own README with run instructions.

## Testing

```bash
# run all tests
pytest tests/ -v

# with coverage
pytest --cov=livetxt --cov-report=term tests/
```

## Troubleshooting

- No response? Ensure your handler listens to `data_received` and you call `await ctx.connect()` before relying on events.
- Byte/str issues? Encode/decode UTF‑8 around `publish_data()` and handler inputs.
- State not sticking? Always pass `result.updated_state` into the next `JobRequest`.

## Contributing

See `DEVELOPMENT.md` for development setup, architecture notes, and testing guidelines. Before opening a PR, run:

```bash
black livetxt/ && ruff check --fix livetxt/ && mypy livetxt/
```

## License

Apache‑2.0. See `LICENSE` and `NOTICE`.

## Related

- livekit-agents: https://github.com/livekit/agents
