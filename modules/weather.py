import functools
import json
import logging

import requests

from enum import Enum
from modules.config import Config
from pydantic import BaseModel
from pytz import timezone
from typing import List, Optional

logger = logging.getLogger('weather')


FORECAST_HOURS = ("06:00", "12:00", "15:00", "18:00", "00:00")

ICONS_MAP = {
    "Sunny": "02",
    "Clear": "03",
    "Partly cloudy": "08",
    "Partly cloudy night": "09",
    "Cloudy": "14",
    "Overcast": "25",
    "Mist": "12",
    "Patchy rain possible": "17",
    "Patchy snow possible": "21",
    "Patchy sleet possible": "21",
    "Patchy freezing drizzle possible": "21",
    "Thundery outbreaks possible": "15",
    "Blowing snow": "21",
    "Blizzard": "23",
    "Fog": "12",
    "Freezing fog": "12",
    "Patchy light drizzle": "17",
    "Light drizzle": "17",
    "Freezing drizzle": "17",
    "Heavy freezing drizzle": "17",
    "Patchy light rain": "17",
    "Light rain": "17",
    "Moderate rain at times": "17",
    "Moderate rain": "17",
    "Heavy rain at times": "18",
    "Heavy rain": "18",
    "Light freezing rain": "24",
    "Moderate or heavy freezing rain": "24",
    "Light sleet": "24",
    "Moderate or heavy sleet": "24",
    "Patchy light snow": "21",
    "Light snow": "21",
    "Patchy moderate snow": "21",
    "Moderate snow": "21",
    "Patchy heavy snow": "23",
    "Heavy snow": "23",
    "Ice pellets": "24",
    "Light rain shower": "17",
    "Moderate or heavy rain shower": "18",
    "Torrential rain shower": "18",
    "Light sleet showers": "24",
    "Moderate or heavy sleet showers": "24",
    "Light snow showers": "21",
    "Moderate or heavy snow showers": "23",
    "Light showers of ice pellets": "24",
    "Moderate or heavy showers of ice pellets": "24",
    "Patchy light rain with thunder": "15",
    "Moderate or heavy rain with thunder": "15",
    "Patchy light snow with thunder": "26",
    "Moderate or heavy snow with thunder": "26",
}


class ForecastConditionEnum(Enum):
    sunny = "Sunny"
    partly_cloudy = "Partly cloudy"
    cloudy = "Cloudy"
    overcast = "Overcast"
    mist = "Mist"
    patchy_rain_possible = "Patchy rain possible"
    patchy_snow_possible = "Patchy snow possible"
    patchy_sleet_possible = "Patchy sleet possible"
    patchy_freezing_drizzle_possible = "Patchy freezing drizzle possible"
    thundery_outbreaks_possible = "Thundery outbreaks possible"
    blowing_snow = "Blowing snow"
    blizzard = "Blizzard"
    fog = "Fog"
    freezing_for = "Freezing fog"
    patchy_light_drizzle = "Patchy light drizzle"
    light_drizzle = "Light drizzle"
    freezing_drizzle = "Freezing drizzle"
    heavy_freezing_drizzle = "Heavy freezing drizzle"
    patchy_light_rain = "Patchy light rain"
    light_rain = "Light rain"
    moderate_rain_at_times = "Moderate rain at times"
    moderate_rain = "Moderate rain"
    heavy_rain_at_times = "Heavy rain at times"
    heavy_rain = "Heavy rain"
    light_freezing_rain = "Light freezing rain"
    moderate_or_heavy_freezing_rain = "Moderate or heavy freezing rain"
    light_sleet = "Light sleet"
    moderate_or_heavy_sleet = "Moderate or heavy sleet"
    patchy_light_snow = "Patchy light snow"
    light_snow = "Light snow"
    patchy_moderate_snow = "Patchy moderate snow"
    moderate_snow = "Moderate snow"
    patchy_heavy_snow = "Patchy heavy snow"
    heavy_snow = "Heavy snow"
    ice_pellets = "Ice pellets"
    light_rain_shower = "Light rain shower"
    moderate_or_heavy_rain_shower = "Moderate or heavy rain shower"
    torrential_rain_shower = "Torrential rain shower"
    light_sleet_showers = "Light sleet showers"
    moderate_or_heavy_sleet_showers = "Moderate or heavy sleet showers"
    light_snow_showers = "Light snow showers"
    moderate_or_heavy_snow_showers = "Moderate or heavy snow showers"
    light_showers_of_ice_pellets = "Light showers of ice pellets"
    moderate_or_heavy_showers_of_ice_pellets = "Moderate or heavy showers of ice pellets"
    patchy_light_rain_with_thunder = "Patchy light rain with thunder"
    moderate_or_heavy_rain_with_thunder = "Moderate or heavy rain with thunder"
    patchy_light_snow_with_thunder = "Patchy light snow with thunder"
    moderate_or_heavy_snow_with_thunder = "Moderate or heavy snow with thunder"


class ForecastHour(BaseModel):
    condition: str
    hour: str
    is_day: bool
    temperature: int

    @property
    def icon(self):
        night_condition = f"{self.condition} night"
        icon_index = ICONS_MAP[self.condition]
        if not self.is_day and f"{self.condition} night" in ICONS_MAP:
            icon_index = ICONS_MAP[night_condition]
        return f"001lighticons-{icon_index}.png"


class ForecastDay(BaseModel):
    day: str
    hours: List[ForecastHour]


class WeatherApiForecastCondition(BaseModel):
    text: str


class WeatherApiForecastHour(BaseModel):
    time_epoch: int
    time: str
    temp_c: float
    is_day: int
    condition: WeatherApiForecastCondition


class WeatherApiForecastDay(BaseModel):
    date: str
    date_epoch: int
    hour: List[WeatherApiForecastHour]


class WeatherApiForecast(BaseModel):
    forecastday: List[WeatherApiForecastDay]


class WeatherApiForecastResponse(BaseModel):
    forecast: WeatherApiForecast


class Weather:
    def __init__(self, config: Config):
        self.config = config
        self.number_of_forecast_days = 1
        self.timezone = timezone(config.timezone)

    @property
    @functools.lru_cache()
    def forecast(self) -> Optional[ForecastDay]:
        parameters = [
            f"key={self.config.weather.api_key}",
            f"q={self.config.weather.latitude},{self.config.weather.longitude}",
            f"days={self.number_of_forecast_days + 1}",
            "aqi=no",
            "alerts=no",
        ]
        url = f"https://api.weatherapi.com/v1/forecast.json?{'&'.join(parameters)}"
        try:
            result = requests.get(url)
            data = json.loads(result.text)
        except Exception:
            logger.error(f"Failed to fetch weather forecast", exc_info=True)
            return None

        weather_api_forecast = WeatherApiForecastResponse(**data)

        forecast_days = []
        forecast_hours = []
        first_hour = True
        for forecast_day in weather_api_forecast.forecast.forecastday[:self.number_of_forecast_days + 1]:
            day = ForecastDay(day=forecast_day.date, hours=[])
            for forecast_hour in forecast_day.hour:
                if first_hour:
                    first_hour = False
                    continue
                if forecast_hour.time.endswith(FORECAST_HOURS):
                    forecast_hours.append(
                        ForecastHour(
                            condition=forecast_hour.condition.text.strip(),
                            hour=forecast_hour.time.split(" ")[-1],
                            is_day=forecast_hour.is_day == 1,
                            temperature=round(forecast_hour.temp_c)
                        )
                    )
                if len(forecast_hours) == len(FORECAST_HOURS):
                    day.hours = forecast_hours.copy()
                    forecast_days.append(day)
                    forecast_hours = []
            if len(forecast_days) == self.number_of_forecast_days:
                break

        logger.info(f"Weather forecast for {self.number_of_forecast_days} day(s) ready")

        return forecast_days[0]
