# Zero-Code-Change Example

This example demonstrates the **core value proposition** of LiveTxt: **ZERO code changes** required to run your livekit-agents over SMS/chat.

## The Agent

`my_agent.py` is a **100% standard livekit-agents Agent**. It contains:
- ✅ Normal `Agent` class
- ✅ Standard `@llm.function_tool()` decorators
- ✅ Regular async methods
- ❌ NO livetxt imports
- ❌ NO wrapper code
- ❌ NO state management code

## How to Run

```bash
# Set environment variables
export LIVETXT_GATEWAY_URL=http://localhost:8000
export LIVETXT_API_KEY=your_api_key

# Run the agent - that's it!
livetxt run my_agent.py
```

## What Happens Behind the Scenes

When you run `livetxt run my_agent.py`, LiveTxt automatically:

1. **🔧 Patches livekit-agents** before your code loads
2. **🔍 Discovers your Agent class** automatically
3. **📦 Wraps Agent.__init__** to restore state
4. **🎣 Hooks chat_ctx property** to capture state  
5. **🛠️ Wraps function tools** to track calls
6. **🌐 Connects to gateway** for message routing
7. **💾 Manages state** transparently across turns

## The User Experience

### Turn 1
```
SMS: "What's the weather in San Francisco?"
→ Agent processes (function get_weather called)
→ Response: "It's 72°F and sunny in San Francisco!"
→ State automatically saved
```

### Turn 2 (New worker instance)
```
SMS: "How about tomorrow?"
→ State automatically restored
→ Agent remembers we're talking about SF
→ Function get_forecast("San Francisco") called
→ Response: "Tomorrow it will be 68°F and cloudy"
→ Updated state saved
```

## Comparison: Voice vs SMS

### Voice Mode (Original)
```python
from livekit.agents import cli, WorkerOptions

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
```

### SMS Mode (LiveTxt)
```bash
# No code changes - just run with livetxt CLI
livetxt run my_agent.py
```

That's it! Your agent code **never changes**.

## Multiple Agents in One File

If your file has multiple Agent classes:

```bash
# Specify which one to use
livetxt run my_agent.py --agent-class WeatherAssistant
```

## What Gets Captured Automatically

- ✅ **Chat Context**: Full conversation history
- ✅ **Function Calls**: All tool invocations with args/results
- ✅ **State Changes**: User and agent state
- ✅ **Context**: User metadata, preferences, etc.

## Next Steps

- **Gateway**: Set up livetxt-gateway to receive SMS
- **Production**: Configure Redis for persistent state storage
- **Scale**: Run multiple workers for load balancing
- **Monitor**: Add logging and metrics

## More Examples

- `examples/weather-agent/` - Full weather agent with API calls
- `examples/customer-support/` - Customer support bot
- `examples/smart-home/` - Smart home control agent

All examples work with **ZERO code changes** - just `livetxt run <file>.py`!
