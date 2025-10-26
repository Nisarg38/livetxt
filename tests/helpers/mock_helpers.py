"""
Mock helpers for testing.

Provides reusable mock objects and functions.
"""
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any


def create_mock_weather_response(temperature: float = 20.0) -> Dict[str, Any]:
    """
    Create a mock weather API response.
    
    Args:
        temperature: Temperature in Celsius
        
    Returns:
        Dict that mimics the open-meteo API response
    """
    return {
        "current": {
            "temperature_2m": temperature,
            "time": "2025-10-25T12:00"
        },
        "current_units": {
            "temperature_2m": "°C"
        }
    }


def create_mock_http_session(status: int = 200, response_data: Dict[str, Any] = None):
    """
    Create a mock aiohttp.ClientSession for testing.
    
    Args:
        status: HTTP status code
        response_data: Response data to return
        
    Returns:
        Mock session that can be used to patch aiohttp.ClientSession
    """
    if response_data is None:
        response_data = create_mock_weather_response()
    
    mock_session = MagicMock()
    mock_get = AsyncMock()
    mock_get.return_value.__aenter__.return_value.status = status
    mock_get.return_value.__aenter__.return_value.json = AsyncMock(
        return_value=response_data
    )
    mock_session.return_value.__aenter__.return_value.get = mock_get
    
    return mock_session

