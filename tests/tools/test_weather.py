"""Tests for the weather tool."""

import os
from unittest.mock import patch

import pytest
import requests
from dotenv import load_dotenv

from mailos.tools.weather import get_weather

# Load environment variables
load_dotenv()


def test_weather_api_key_exists():
    """Test that OpenWeatherMap API key is configured."""
    assert os.getenv("OPENWEATHER_API_KEY") is not None, (
        "OPENWEATHER_API_KEY not found in environment variables. "
        "Please set it in your .env file."
    )


def test_get_weather_success(mock_weather_api):
    """Test successful weather retrieval."""
    result = get_weather("London,UK")
    assert result["status"] == "success"
    assert "data" in result

    data = result["data"]
    assert "temperature" in data
    assert "description" in data
    assert "humidity" in data
    assert "wind_speed" in data
    assert "location" in data

    # Check data types
    assert isinstance(data["temperature"], (int, float))
    assert isinstance(data["humidity"], (int, float))
    assert isinstance(data["wind_speed"], (int, float))
    assert isinstance(data["description"], str)


def test_get_weather_invalid_city(mock_weather_api):
    """Test weather retrieval with invalid city."""
    mock_weather_api.ok = False
    mock_weather_api.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "City not found"
    )

    result = get_weather("ThisCityDoesNotExist123456")
    assert result["status"] == "error"
    assert "message" in result


def test_get_weather_no_api_key(monkeypatch):
    """Test weather retrieval without API key."""
    # Remove API key from environment and reload the weather module
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    with patch("mailos.tools.weather.OPENWEATHER_API_KEY", None):
        result = get_weather("London")
        assert result["status"] == "error"
        assert "API key not configured" in result["message"]


def test_get_weather_with_country_code(monkeypatch, mock_weather_api):
    """Test weather retrieval with city and country code."""
    # Create a new mock response for Tokyo
    tokyo_response = {
        "name": "Tokyo",
        "sys": {"country": "JP"},
        "weather": [{"description": "clear sky"}],
        "main": {
            "temp": 293.15,
            "feels_like": 292.15,
            "pressure": 1013,
            "humidity": 65,
        },
        "wind": {"speed": 3.6},
        "clouds": {"all": 20},
    }
    mock_weather_api.json.return_value = tokyo_response

    result = get_weather("Tokyo,JP")
    assert result["status"] == "success"
    assert "data" in result
    assert "Tokyo" in result["data"]["location"]
    assert "JP" in result["data"]["location"]


@pytest.mark.parametrize(
    "city", ["New York,US", "Paris,FR", "Sydney,AU", "Moscow,RU", "Beijing,CN"]
)
def test_get_weather_multiple_cities(city, monkeypatch, mock_weather_api):
    """Test weather retrieval for multiple cities."""
    # Create a new mock response for each city
    city_name, country = city.split(",")
    city_response = {
        "name": city_name,
        "sys": {"country": country},
        "weather": [{"description": "clear sky"}],
        "main": {
            "temp": 293.15,
            "feels_like": 292.15,
            "pressure": 1013,
            "humidity": 65,
        },
        "wind": {"speed": 3.6},
        "clouds": {"all": 20},
    }
    mock_weather_api.json.return_value = city_response

    result = get_weather(city)
    assert result["status"] == "success"
    assert "data" in result
    assert all(
        key in result["data"]
        for key in ["temperature", "description", "humidity", "wind_speed", "location"]
    )
    assert city_name in result["data"]["location"]
    assert country in result["data"]["location"]


def test_get_weather_with_units(mock_weather_api):
    """Test weather data includes correct units."""
    result = get_weather("London,UK")
    assert result["status"] == "success"
    assert "units" in result
    assert result["units"]["temperature"] == "°C"
    assert result["units"]["wind_speed"] == "km/h"
    assert result["units"]["humidity"] == "%"


def test_get_weather_api_error(mock_weather_api):
    """Test handling of API errors."""
    mock_weather_api.ok = False
    mock_weather_api.raise_for_status.side_effect = (
        requests.exceptions.RequestException("API error")
    )

    result = get_weather("London,UK")
    assert result["status"] == "error"
    assert "Failed to fetch weather data" in result["message"]
