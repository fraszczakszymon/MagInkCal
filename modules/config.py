import functools
import json
import logging
import os
import pathlib

from pydantic import BaseModel
from typing import List, Optional


logger = logging.getLogger('config')


class I18nConfig(BaseModel):
    header_months = [
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
    preview_months = [
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
    detailed_weeks = 0
    i18n: I18nConfig
    image_width = 1304
    image_height = 984
    max_events_per_day = 5
    number_of_months = 0
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
        config = Config(**config_data)

        assert len(config.calendars) > 0, "No calendars configured"
        assert config.number_of_months <= 2, "Maximum number of months is 2"

        return config
