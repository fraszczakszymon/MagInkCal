#!/usr/bin/env python3

import logging
import os

from display.display import Display
from modules.config import ConfigLoader
from modules.calendar import Calendar
from modules.logger import log_setup
from modules.power import Power
from modules.render import TemplateRenderer
from modules.schedule import Scheduler
from modules.weather import Weather


log_setup()
logger = logging.getLogger('MagInkCal')


def display_calendar():
    config = ConfigLoader().config
    power = Power()
    power.sync_time()
    battery_status = power.battery_status

    calendar = Calendar(config)
    calendar.load_events()

    weather_forecast = Weather(config).forecast

    renderer = TemplateRenderer(config)

    battery_status = power.battery_status

    black_image, red_image = renderer.render(calendar, weather_forecast=weather_forecast, battery_status=battery_status)

    display_service = Display(config.screen_width, config.screen_height)
    if calendar.today.weekday() == 0:
        display_service.calibrate(cycles=0)  # calibrate display once a week to prevent ghosting
        logger.info("Display calibrated")

    logger.info("Update display")
    display_service.update(black_image, red_image)
    display_service.sleep()

    logger.info("Completed daily calendar update")

    scheduler = Scheduler(config)
    scheduler.schedule_next_wakeup()

    if config.auto_power_off and (config.auto_power_off_while_charging or not battery_status.is_charging):
        logger.info("Power off")
        os.system("sudo shutdown -h now")


if __name__ == "__main__":
    try:
        display_calendar()
    except Exception:
        logger.info("Power off", exc_info=True)
        os.system("sudo shutdown -h now")
