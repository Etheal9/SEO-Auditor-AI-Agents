fimport os
import requests
from langchain_core.tools import tool


@mcp.tool
def get_weather_data(location: str) -> str:
    """
    Provides real-time weather information for a given location using the OpenWeatherMap API.

    To use this tool, you must set the 'OPENWEATHER_API_KEY' environment variable.

    Args:
        location: The city name for which to retrieve weather information (e.g., "London" or "New York, US").

    Returns:
        A string describing the current weather conditions or an error message if the data could not be retrieved.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Error: The OPENWEATHER_API_KEY environment variable is not set. Please set it to use this tool."

    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "appid": api_key,
        "units": "metric"  # Use 'imperial' for Fahrenheit
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        data = response.json()

        if data.get("cod") != 200:
            return f"Error: Could not retrieve weather for {location}. Reason: {data.get('message', 'Unknown error')}"

        weather_desc = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        return f"The current weather in {data['name']} is {weather_desc} with a temperature of {temp}°C."
    except requests.exceptions.RequestException as e:
        return f"Error: Failed to connect to the weather service. Details: {e}"