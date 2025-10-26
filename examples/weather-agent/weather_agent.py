"""
LiveKit Weather Agent Example - Works with LiveTxt!

This is a REAL LiveKit voice agent that uses:
- AgentSession with LLM
- Function tools (@function_tool)
- Async function calls

🎯 from original LiveKit agent!
   Just change how you run it (see test_livekit_agent_weather.py)
"""
import logging

import aiohttp
from dotenv import load_dotenv

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession
from livekit.agents.voice.room_io import RoomInputOptions, RoomOutputOptions
from livekit.plugins import openai

# livetxt imports
from livetxt import cli as livetxt_cli

logger = logging.getLogger("weather-example")
logger.setLevel(logging.INFO)

load_dotenv()


class WeatherAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are a weather agent.",
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
        weather_data = {}
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # response from the function call is returned to the LLM
                    weather_data = {
                        "temperature": data["current"]["temperature_2m"],
                        "temperature_unit": "Celsius",
                    }
                else:
                    raise Exception(f"Failed to get weather data, status code: {response.status}")

        return weather_data


async def entrypoint(ctx: JobContext):
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room_name": ctx.room.name,
        "user_id": "your user_id",
    }

    session = AgentSession()

    await session.start(
        agent=WeatherAgent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )


if __name__ == "__main__":
    ## Run with LiveKit CLI (Voice Mode) ##
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

    ### Run with LiveTxt CLI (SMS Mode) ###
    ## Set these environment variables: ##
    ## export LIVETXT_GATEWAY_URL=http://localhost:8000 ##
    ## export LIVETXT_API_KEY=sk_live_1234567890 ##
    livetxt_cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))