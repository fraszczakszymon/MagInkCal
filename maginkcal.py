#!/usr/bin/env python3

import logging
import os

from display.display import Display
from modules.config import ConfigLoader
from modules.events import Calendar
from modules.power import Power
from modules.render import TemplateRenderer
from modules.weather import Weather


def main():
    logger = logging.getLogger('MagInkCal')
    config = ConfigLoader().config
    power = Power()
    power.sync_time()
    battery_status = power.battery_status

    logger.info('Battery level at start: {:.3f}'.format(battery_status.level))

    calendar = Calendar(config)
    calendar.load_events()

    weather_forecast = Weather(config).forecast

    renderer = TemplateRenderer(config)

    black_image, red_image = renderer.render(calendar, weather_forecast=weather_forecast, battery_status=battery_status)

    try:
        display_service = Display(config.screen_width, config.screen_height)
        if calendar.today.weekday() == 0:
            display_service.calibrate(cycles=0)  # calibrate display once a week to prevent ghosting
            display_service.update(black_image, red_image)
            display_service.sleep()
    except Exception as e:
        logger.error(e)

    logger.info("Completed daily calendar update")

    if config.auto_power_off and not battery_status.is_charging:
        os.system("sudo shutdown -h now")


if __name__ == "__main__":
    main()
