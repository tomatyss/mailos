"""Tests for the weather tool."""

import os
from unittest.mock import patch

import pytest
import requests
from dotenv import load_dotenv

from mailos.tools.weather import get_weather, kelvin_to_celsius

# Load environment variables
load_dotenv()


def test_kelvin_to_celsius():
    """Test Kelvin to Celsius conversion."""
    assert kelvin_to_celsius(273.15) == 0.0  # 0°C
    assert kelvin_to_celsius(293.15) == 20.0  # 20°C
    assert kelvin_to_celsius(373.15) == 100.0  # 100°C
    assert round(kelvin_to_celsius(283.15), 1) == 10.0  # 10°C


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

    # Validate data ranges
    assert -100 < data["temperature"] < 100  # Reasonable temperature range
    assert 0 <= data["humidity"] <= 100  # Humidity is a percentage
    assert data["wind_speed"] >= 0  # Non-negative wind speed
    assert data["description"].istitle()  # Description should be capitalized


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
    assert result["units"]["pressure"] == "hPa"
    assert result["units"]["humidity"] == "%"
    assert result["units"]["precipitation"] == "mm"


def test_get_weather_api_error(mock_weather_api):
    """Test handling of API errors."""
    mock_weather_api.ok = False
    mock_weather_api.raise_for_status.side_effect = (
        requests.exceptions.RequestException("API error")
    )

    result = get_weather("London,UK")
    assert result["status"] == "error"
    assert "Failed to fetch weather data" in result["message"]


def test_get_weather_network_error(mock_weather_api):
    """Test handling of network errors."""
    mock_weather_api.ok = False
    mock_weather_api.raise_for_status.side_effect = requests.exceptions.ConnectionError(
        "Network error"
    )

    result = get_weather("London,UK")
    assert result["status"] == "error"
    assert "Failed to fetch weather data" in result["message"]


def test_get_weather_parse_error(mock_weather_api):
    """Test handling of response parsing errors."""
    # Return invalid JSON structure
    mock_weather_api.json.return_value = {"invalid": "structure"}

    result = get_weather("London,UK")
    assert result["status"] == "error"
    assert "Failed to parse weather data" in result["message"]


def test_get_weather_optional_fields(mock_weather_api):
    """Test handling of optional weather fields."""
    # Add optional fields to mock response
    mock_response = mock_weather_api.json.return_value
    mock_response.update(
        {"rain": {"1h": 2.5}, "snow": {"1h": 0.5}, "clouds": {"all": 75}}
    )

    result = get_weather("London,UK")
    assert result["status"] == "success"
    data = result["data"]
    assert "rain_1h" in data
    assert "snow_1h" in data
    assert "cloudiness" in data
    assert data["cloudiness"] == 75
