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


class ForecastConditionEnum(Enum):
    sunny = 1000
    partly_cloudy = 1003
    cloudy = 1006
    overcast = 1009
    mist = 1030
    patchy_rain_possible = 1063
    patchy_snow_possible = 1066
    patchy_sleet_possible = 1069
    patchy_freezing_drizzle_possible = 1072
    thundery_outbreaks_possible = 1087
    blowing_snow = 1114
    blizzard = 1117
    fog = 1135
    freezing_fog = 1147
    patchy_light_drizzle = 1150
    light_drizzle = 1153
    freezing_drizzle = 1168
    heavy_freezing_drizzle = 1171
    patchy_light_rain = 1180
    light_rain = 1183
    moderate_rain_at_times = 1186
    moderate_rain = 1189
    heavy_rain_at_times = 1192
    heavy_rain = 1195
    light_freezing_rain = 1198
    moderate_or_heavy_freezing_rain = 1201
    light_sleet = 1204
    moderate_or_heavy_sleet = 1207
    patchy_light_snow = 1210
    light_snow = 1213
    patchy_moderate_snow = 1216
    moderate_snow = 1219
    patchy_heavy_snow = 1222
    heavy_snow = 1225
    ice_pellets = 1237
    light_rain_shower = 1240
    moderate_or_heavy_rain_shower = 1243
    torrential_rain_shower = 1246
    light_sleet_showers = 1249
    moderate_or_heavy_sleet_showers = 1252
    light_snow_showers = 1255
    moderate_or_heavy_snow_showers = 1258
    light_showers_of_ice_pellets = 1261
    moderate_or_heavy_showers_of_ice_pellets = 1264
    patchy_light_rain_with_thunder = 1273
    moderate_or_heavy_rain_with_thunder = 1276
    patchy_light_snow_with_thunder = 1279
    moderate_or_heavy_snow_with_thunder = 1282


ICONS_MAP = {
    ForecastConditionEnum.sunny: "02",
    ForecastConditionEnum.partly_cloudy: "08",
    ForecastConditionEnum.cloudy: "14",
    ForecastConditionEnum.overcast: "25",
    ForecastConditionEnum.mist: "12",
    ForecastConditionEnum.patchy_rain_possible: "17",
    ForecastConditionEnum.patchy_snow_possible: "21",
    ForecastConditionEnum.patchy_sleet_possible: "21",
    ForecastConditionEnum.patchy_freezing_drizzle_possible: "21",
    ForecastConditionEnum.thundery_outbreaks_possible: "15",
    ForecastConditionEnum.blowing_snow: "21",
    ForecastConditionEnum.blizzard: "23",
    ForecastConditionEnum.fog: "12",
    ForecastConditionEnum.freezing_fog: "12",
    ForecastConditionEnum.patchy_light_drizzle: "17",
    ForecastConditionEnum.light_drizzle: "17",
    ForecastConditionEnum.freezing_drizzle: "17",
    ForecastConditionEnum.heavy_freezing_drizzle: "17",
    ForecastConditionEnum.patchy_light_rain: "17",
    ForecastConditionEnum.light_rain: "17",
    ForecastConditionEnum.moderate_rain_at_times: "17",
    ForecastConditionEnum.moderate_rain: "17",
    ForecastConditionEnum.heavy_rain_at_times: "18",
    ForecastConditionEnum.heavy_rain: "18",
    ForecastConditionEnum.light_freezing_rain: "24",
    ForecastConditionEnum.moderate_or_heavy_freezing_rain: "24",
    ForecastConditionEnum.light_sleet: "24",
    ForecastConditionEnum.moderate_or_heavy_sleet: "24",
    ForecastConditionEnum.patchy_light_snow: "21",
    ForecastConditionEnum.light_snow: "21",
    ForecastConditionEnum.patchy_moderate_snow: "21",
    ForecastConditionEnum.moderate_snow: "21",
    ForecastConditionEnum.patchy_heavy_snow: "23",
    ForecastConditionEnum.heavy_snow: "23",
    ForecastConditionEnum.ice_pellets: "24",
    ForecastConditionEnum.light_rain_shower: "17",
    ForecastConditionEnum.moderate_or_heavy_rain_shower: "18",
    ForecastConditionEnum.torrential_rain_shower: "18",
    ForecastConditionEnum.light_sleet_showers: "24",
    ForecastConditionEnum.moderate_or_heavy_sleet_showers: "24",
    ForecastConditionEnum.light_snow_showers: "21",
    ForecastConditionEnum.moderate_or_heavy_snow_showers: "23",
    ForecastConditionEnum.light_showers_of_ice_pellets: "24",
    ForecastConditionEnum.moderate_or_heavy_showers_of_ice_pellets: "24",
    ForecastConditionEnum.patchy_light_rain_with_thunder: "15",
    ForecastConditionEnum.moderate_or_heavy_rain_with_thunder: "15",
    ForecastConditionEnum.patchy_light_snow_with_thunder: "26",
    ForecastConditionEnum.moderate_or_heavy_snow_with_thunder: "26",
}

NIGHT_ICONS_MAP = {
    ForecastConditionEnum.sunny: "03",
    ForecastConditionEnum.partly_cloudy: "09",
}


class ForecastHour(BaseModel):
    condition: ForecastConditionEnum
    hour: str
    is_day: bool
    temperature: int

    @property
    def icon(self):
        icon_index = ICONS_MAP[self.condition]
        if not self.is_day and self.condition in NIGHT_ICONS_MAP:
            icon_index = NIGHT_ICONS_MAP[self.condition]
        return f"001lighticons-{icon_index}.png"


class ForecastDay(BaseModel):
    day: str
    hours: List[ForecastHour]


class WeatherApiForecastCondition(BaseModel):
    code: ForecastConditionEnum
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
                            condition=ForecastConditionEnum(forecast_hour.condition.code),
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
