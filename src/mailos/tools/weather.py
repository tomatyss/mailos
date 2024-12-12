"""Weather tool for getting current weather information using OpenWeatherMap API."""

import os
from typing import Dict

import requests
from dotenv import load_dotenv

from mailos.utils.logger_utils import logger
from mailos.vendors.models import Tool

# Load environment variables
load_dotenv()

# OpenWeatherMap configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def kelvin_to_celsius(kelvin: float) -> float:
    """Convert Kelvin to Celsius."""
    return kelvin - 273.15


def get_weather(city: str) -> Dict:
    """Get current weather for a given city using OpenWeatherMap API.

    Args:
        city: Name of the city to get weather for

    Returns:
        Dict containing weather data or error message
    """
    # Get API key at runtime to support testing
    api_key = OPENWEATHER_API_KEY
    if not api_key:
        logger.error("OpenWeatherMap API key not found in environment variables")
        return {
            "status": "error",
            "message": (
                "Weather API key not configured. Please set OPENWEATHER_API_KEY "
                "environment variable."
            ),
        }

    try:
        # Make API request
        params = {
            "q": city,
            "appid": api_key,
        }
        response = requests.get(OPENWEATHER_BASE_URL, params=params)
        response.raise_for_status()

        # Parse response
        data = response.json()

        # Extract relevant weather information
        weather_data = {
            "temperature": round(kelvin_to_celsius(data["main"]["temp"]), 1),
            "feels_like": round(kelvin_to_celsius(data["main"]["feels_like"]), 1),
            "description": data["weather"][0]["description"].title(),
            "humidity": data["main"]["humidity"],
            "wind_speed": round(data["wind"]["speed"] * 3.6, 1),  # Convert m/s to km/h
            "pressure": data["main"]["pressure"],
            "location": f"{data['name']}, {data['sys']['country']}",
        }

        # Add optional fields if available
        if "rain" in data:
            weather_data["rain_1h"] = data["rain"].get("1h", 0)
        if "snow" in data:
            weather_data["snow_1h"] = data["snow"].get("1h", 0)
        if "clouds" in data:
            weather_data["cloudiness"] = data["clouds"]["all"]

        return {
            "status": "success",
            "data": weather_data,
            "units": {
                "temperature": "°C",
                "wind_speed": "km/h",
                "pressure": "hPa",
                "humidity": "%",
                "precipitation": "mm",
            },
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {str(e)}")
        return {"status": "error", "message": f"Failed to fetch weather data: {str(e)}"}
    except (KeyError, ValueError) as e:
        logger.error(f"Error parsing weather data: {str(e)}")
        return {"status": "error", "message": f"Failed to parse weather data: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error getting weather: {str(e)}")
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


# Define the weather tool
weather_tool = Tool(
    name="get_weather",
    description=(
        "Get current weather information for a specified city using OpenWeatherMap API"
    ),
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": (
                    "The name of the city to get weather for (e.g., 'London,UK')"
                ),
            }
        },
    },
    required_params=["city"],
    function=get_weather,
)
