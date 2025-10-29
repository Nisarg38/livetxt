"""
Example: Zero-Code-Change Agent

This is a standard livekit-agents Agent with ZERO livetxt-specific code.
It works exactly as written - just run with: livetxt run my_agent.py
"""

from livekit.agents import Agent, llm, WorkerOptions
from livetxt.cli import cli as livetxt_cli


class WeatherAssistant(Agent):
    """A simple weather assistant agent."""
    
    def __init__(self):
        super().__init__(
            instructions="You are a helpful weather assistant. You can check weather for any location."
        )
    
    @llm.function_tool()
    async def get_weather(self, location: str) -> dict:
        """
        Get current weather for a location.
        
        Args:
            location: City name or location
            
        Returns:
            Weather information
        """
        # In a real agent, this would call a weather API
        # For demo, return mock data
        return {
            "location": location,
            "temperature": 72,
            "condition": "Sunny",
            "humidity": 45
        }
    
    @llm.function_tool()
    async def get_forecast(self, location: str, days: int = 3) -> list:
        """
        Get weather forecast for a location.
        
        Args:
            location: City name
            days: Number of days (1-7)
            
        Returns:
            List of forecast data
        """
        # Mock forecast data
        return [
            {"day": 1, "temp": 72, "condition": "Sunny"},
            {"day": 2, "temp": 68, "condition": "Cloudy"},
            {"day": 3, "temp": 65, "condition": "Rainy"}
        ][:days]

def entrypoint():
    return WeatherAssistant()



# That's it! No livetxt imports, no wrapper code, no state management
# Just run: livetxt run my_agent.py
if __name__ == "__main__":
    livetxt_cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint, 
        ws_url="http://localhost:8000", 
        api_key="test_key_123"
    ))