"""Weather tool for getting current weather information."""

from typing import Dict

from mailos.vendors.models import Tool


def get_weather(city: str) -> Dict:
    """Get current weather for a given city using OpenWeatherMap API."""
    # Note: In a real implementation, API key would be loaded from config
    # This is a mock implementation for demonstration
    try:
        # Mock weather data for demonstration
        weather_data = {
            "temperature": 22,
            "description": "Partly cloudy",
            "humidity": 65,
            "wind_speed": 12,
        }
        return {"status": "success", "data": weather_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Define the weather tool
weather_tool = Tool(
    name="get_weather",
    description="Get current weather information for a specified city",
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "The name of the city to get weather for",
            }
        },
    },
    required_params=["city"],
    function=get_weather,
)
