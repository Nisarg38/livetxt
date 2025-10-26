"""
LiveKit Smart Home Agent Example - Works with LiveTxt!

This demonstrates:
- Enum types in function arguments
- Multiple function tools
- Type annotations with Literal
- Complex argument types

🎯 ZERO CODE CHANGES from original LiveKit agent!
"""

import logging
from enum import Enum
from typing import Literal

from dotenv import load_dotenv

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.agents.llm import function_tool
from livekit.plugins import openai

# livetxt imports
from livetxt import cli as livetxt_cli

logger = logging.getLogger("smart-home-agent")
logger.setLevel(logging.INFO)

load_dotenv()


class RoomName(str, Enum):
    """Supported rooms in the smart home."""
    BEDROOM = "bedroom"
    LIVING_ROOM = "living room"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    OFFICE = "office"


class SmartHomeAgent(Agent):
    """An agent that controls smart home devices."""
    
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a smart home assistant. "
                "You can control lights and check the weather. "
                "Be helpful and confirm actions clearly."
            ),
            llm=openai.LLM(model="gpt-4.1-mini"),
        )
    
    @function_tool
    async def toggle_light(self, room: RoomName, switch_to: Literal["on", "off"]) -> str:
        """
        Turn lights on or off in a specific room.
        
        Args:
            room: The room to control the light in
            switch_to: Whether to turn the light "on" or "off"
        """
        logger.info(f"Toggling light in {room} to {switch_to}")
        return f"The light in the {room.value} is now {switch_to}."
    
    @function_tool
    async def get_weather(self, location: str) -> str:
        """
        Get current weather for a location.
        
        Args:
            location: The location to get weather for (e.g., "San Francisco")
        """
        logger.info(f"Getting weather for {location}")
        # Mock response
        return f"The weather in {location} is sunny and 72°F."
    
    @function_tool
    async def set_temperature(self, room: RoomName, temperature: int) -> str:
        """
        Set the thermostat temperature for a room.
        
        Args:
            room: The room to set temperature for
            temperature: Target temperature in Fahrenheit
        """
        logger.info(f"Setting {room} temperature to {temperature}°F")
        return f"Set the {room.value} temperature to {temperature}°F."


async def entrypoint(ctx: JobContext):
    """
    Standard LiveKit agent entrypoint.
    
    ✅ Works with both LiveKit (voice) and LiveTxt (text) unchanged!
    """
    session = AgentSession()
    
    await session.start(
        agent=SmartHomeAgent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    ## Run with LiveKit CLI (Voice Mode) ##
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

    ### Run with LiveTxt CLI (SMS Mode) ###
    ## Set these environment variables: ##
    ## export LIVETXT_GATEWAY_URL=http://localhost:8000 ##
    ## export LIVETXT_API_KEY=sk_live_1234567890 ##
    livetxt_cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

