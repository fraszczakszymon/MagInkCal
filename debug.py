#!/usr/bin/env python3
import sys

from modules.config import ConfigLoader
from modules.events import Calendar
from modules.power import Power
from modules.render import TemplateRenderer
from modules.weather import Weather

assert len(sys.argv) == 2, f"Expected 1 argument, {len(sys.argv) - 1} given"
cmd = sys.argv[1]

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
                print(f"  {event.start_date.strftime('%H:%M')} {event.summary}")
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
    for forecast in Weather(config).forecast:
        print(forecast.day)
        for hour in forecast.hours:
            print(f"  {hour.hour}: {hour.condition.value} - {hour.temperature}°C")
else:
    print(f"Unknown '{cmd}' command")
