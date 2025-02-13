#!/usr/bin/env python3
import logging
import sys
from datetime import datetime

from pytz import timezone

from modules.calendar import Calendar, get_months_preview
from modules.config import ConfigLoader
from modules.logger import log_setup
from modules.power import Power
from modules.render import TemplateRenderer
from modules.schedule import Scheduler
from modules.weather import ForecastConditionEnum, Weather

assert len(sys.argv) == 2, f"Expected 1 argument, {len(sys.argv) - 1} given"
cmd = sys.argv[1]

log_setup("debug.log")

logger = logging.getLogger('debug')
logger.info(f"Debug {cmd}")

config = ConfigLoader().config

if cmd == "config":
    print(config.json(ensure_ascii=False, indent=4))
elif cmd == "events":
    calendar = Calendar(config)
    calendar.load_events()
    for date, day in calendar.days.items():
        print(date)
        for event in day.events:
            if event.all_day:
                print(f"  {event.summary}")
            else:
                print(f"  {event.start_time} {event.summary}")
elif cmd == "months":
    for month in get_months_preview(2):
        print(f"{config.i18n.preview_months[month.number - 1]} {month.year}")
        for index, day in enumerate(month.days):
            print(f"  {day.number}", end="\n" if index % 7 == 6 else " ")
elif cmd == "battery":
    power = Power()
    print(power.battery_status)
elif cmd == "render":
    renderer = TemplateRenderer(config)
    calendar = Calendar(config)
    calendar.load_events()
    weather_forecast = None
    if config.weather.is_enabled:
        weather_forecast = Weather(config).forecast
    renderer.render(calendar, weather_forecast=weather_forecast)
elif cmd == "weather":
    forecast = Weather(config).forecast
    print(forecast.day)
    for hour in forecast.hours:
        print(f"  {hour.hour}: {hour.condition.name} - {hour.temperature}°C")
elif cmd == "scheduler_times":
    scheduler = Scheduler(config)
    now = datetime.now().astimezone(timezone(config.timezone))
    next_wakeup = scheduler.get_next_wakeup_time()
    print(f"Current time: {now.isoformat()}")
    if next_wakeup:
        print(f"Configured wake up times: {', '.join(scheduler.wakeup_hours)}")
        print(f"Next wake up time: {next_wakeup.isoformat()}")
    else:
        print("No wake up time configured")
elif cmd == "scheduler":
    Scheduler(config).schedule_next_wakeup()
else:
    print(f"Unknown '{cmd}' command")
