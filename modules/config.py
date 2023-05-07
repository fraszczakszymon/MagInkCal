import functools
import json
import logging
import os
import pathlib

from pydantic import BaseModel
from typing import List, Optional


logger = logging.getLogger('config')


class I18nConfig(BaseModel):
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December"
    ]
    no_events = "No events"
    upcoming_days = ["Today", "Tomorrow"]
    week_days = ["M", "T", "W", "T", "F", "S", "S"]


class WeatherConfig(BaseModel):
    api_key: str
    is_enabled = False
    latitude: float
    longitude: float


class Calendar(BaseModel):
    url: str
    important = False


class Config(BaseModel):
    auto_power_off = True
    display_battery = True
    calendars: List[Calendar]
    i18n: I18nConfig
    image_width = 984
    image_height = 1304
    max_events_per_day = 5
    number_of_weeks = 3
    rotate = 0
    screen_width = 1304
    screen_height = 984
    timezone: str
    weather: Optional[WeatherConfig]


class ConfigLoader:
    @property
    @functools.lru_cache()
    def config(self) -> Config:
        path = f"{pathlib.Path(__file__).parent.parent.absolute()}/config.json"
        assert os.path.exists(path), "config.json does not exist"
        with open(path) as file:
            config_data = json.load(file)
            logger.info('Config file loaded')
        return Config(**config_data)
