"""
Weather Agent Test Fixture

This is a REAL LiveKit voice agent that uses:
- AgentSession with LLM
- Function tools (@function_tool)
- Async function calls

Use this for testing LiveTxt compatibility with real LiveKit agents.
"""
import logging
import aiohttp

from livekit.agents import JobContext
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.voice.room_io import RoomInputOptions, RoomOutputOptions
from livekit.plugins import openai

logger = logging.getLogger("weather-agent-test")


class WeatherAgent(Agent):
    """Weather agent that can fetch real weather data."""
    
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a weather agent. Help users check weather conditions.",
            llm=openai.LLM(model="gpt-4.1-mini"),    
        )

    @function_tool
    async def get_weather(
        self,
        latitude: str,
        longitude: str,
    ):
        """Called when the user asks about the weather. This function will return the weather for
        the given location. When given a location, please estimate the latitude and longitude of the
        location and do not ask the user for them.

        Args:
            latitude: The latitude of the location
            longitude: The longitude of the location
        """
        logger.info(f"getting weather for {latitude}, {longitude}")
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "temperature": data["current"]["temperature_2m"],
                        "temperature_unit": "Celsius",
                    }
                else:
                    raise Exception(f"Failed to get weather data, status code: {response.status}")


async def weather_entrypoint(ctx: JobContext):
    """
    Weather agent entrypoint.
    
    This is the standard LiveKit agent entrypoint pattern.
    It works with ZERO changes in LiveTxt!
    """
    ctx.log_context_fields = {
        "room_name": ctx.room.name,
        "user_id": "test_user",
    }

    session = AgentSession()

    await session.start(
        agent=WeatherAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )

