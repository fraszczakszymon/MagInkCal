import logging
import pathlib

from jinja2 import Environment, FileSystemLoader
from modules.calendar import Calendar, get_months_preview
from modules.config import Config
from modules.power import BatteryStatus
from modules.weather import ForecastDay
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from time import sleep


logger = logging.getLogger('render')


CALENDAR_SPACE = 717
WEEK_HEADER_HEIGHT = 42
WEEK_EVENT_HEIGHT = 24
DETAILED_WEEK_HEADER_HEIGHT = 52
DETAILED_WEEK_EVENT_HEIGHT = 28
WEEK_MARGINS = 20
MINIMUM_EVENTS_HEIGHT = 96


class TemplateRenderer:
    def __init__(self, config: Config):
        self.config = config
        self.workdir = f"{pathlib.Path(__file__).parent.parent.absolute()}/build"

    def render(self, calendar: Calendar, battery_status: BatteryStatus = None, weather_forecast: ForecastDay = None):
        self._build_html(calendar, battery_status, weather_forecast)

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--hide-scrollbars")
        options.add_argument('--force-device-scale-factor=1')
        driver = webdriver.Chrome(options=options)
        self._set_driver_viewport_size(driver)
        driver.get(f"file://{self.workdir}/calendar.html")
        sleep(1)
        image_path = f"{self.workdir}/calendar.png"
        driver.get_screenshot_as_file(image_path)
        driver.quit()

        logger.info("Screenshot ready")

        red_image = Image.open(image_path)
        red_pixels = red_image.load()
        black_image = Image.open(image_path)
        black_pixels = black_image.load()

        for i in range(red_image.size[0]):
            for j in range(red_image.size[1]):
                if red_pixels[i, j][0] <= red_pixels[i, j][1] and red_pixels[i, j][0] <= red_pixels[i, j][2]:
                    red_pixels[i, j] = (255, 255, 255)
                else:
                    red_pixels[i, j] = (0, 0, 0)
                if black_pixels[i, j][0] > black_pixels[i, j][1] and black_pixels[i, j][0] > black_pixels[i, j][2]:
                    black_pixels[i, j] = (255, 255, 255)

        red_image = red_image.rotate(self.config.rotate, expand=True)
        black_image = black_image.rotate(self.config.rotate, expand=True)

        # red_file = open(f"{self.workdir}/red.png", "wb")
        # red_image.save(red_file)
        # black_file = open(f"{self.workdir}/black.png", "wb")
        # black_image.save(black_file)

        logger.info("Image file rendered")

        return black_image, red_image

    def _build_html(self, calendar: Calendar, battery_status: BatteryStatus = None, weather_forecast: ForecastDay = None):
        templates_path = f"{pathlib.Path(__file__).parent.parent.absolute()}/template"
        environment = Environment(loader=FileSystemLoader(templates_path))
        template = environment.get_template("calendar_template.jinja2")

        battery_icon = None
        if battery_status and (battery_status.level is not None or battery_status.is_charging):
            battery_icon = self._get_battery_icon_name(battery_status)

        html = template.render(
            calendar=calendar,
            battery_icon=battery_icon,
            detailed_weeks=self.config.detailed_weeks,
            height=self.config.image_height,
            i18n=self.config.i18n,
            max_events_per_day=self.config.max_events_per_day,
            month_number=int(calendar.today.strftime("%-m")),
            no_wifi=calendar.offline_events,
            number_of_weeks=self._calculate_maximum_number_of_weeks(calendar),
            preview_months=get_months_preview(self.config.number_of_months),
            width=self.config.image_width,
            today=calendar.today,
            today_day_number=int(calendar.today.strftime("%-d")),
            weather_forecast=weather_forecast,
        )

        output_file = open(f"{self.workdir}/calendar.html", "w")
        output_file.write(html)
        output_file.close()

        logger.info("HTML file rendered")

    def _get_battery_icon_name(self, battery_status: BatteryStatus) -> str:
        if battery_status.is_charging:
            return "charging"
        if battery_status.level > 95:
            return "full"
        if battery_status.level > 85:
            return "three-quarters"
        if battery_status.level > 70:
            return "half"
        if battery_status.level > 50:
            return "quarter"
        return "empty"

    def _set_driver_viewport_size(self, driver):
        current_window_size = driver.get_window_size()

        html = driver.find_element(By.TAG_NAME, "html")
        inner_width = int(html.get_attribute("clientWidth"))
        inner_height = int(html.get_attribute("clientHeight"))

        target_width = self.config.image_width + (current_window_size["width"] - inner_width)
        target_height = self.config.image_height + (current_window_size["height"] - inner_height)

        driver.set_window_rect(width=target_width, height=target_height)

    def _calculate_maximum_number_of_weeks(self, calendar: Calendar) -> int:
        days = list(calendar.days.values())
        space = CALENDAR_SPACE
        for week in range(1, self.config.number_of_weeks + 1):
            header_height = WEEK_HEADER_HEIGHT
            event_height = WEEK_EVENT_HEIGHT
            maximum_number_of_events = self.config.max_events_per_day
            if week <= self.config.detailed_weeks:
                header_height = DETAILED_WEEK_HEADER_HEIGHT
                event_height = DETAILED_WEEK_EVENT_HEIGHT
                maximum_number_of_events = 999  # let it be big enough
            week_events_height = MINIMUM_EVENTS_HEIGHT
            week_days = days[7*week-7:7*week]
            for day in week_days:
                if day.events:
                    week_events_height = max(week_events_height, min(maximum_number_of_events, len(day.events)) * event_height)
            week_height = header_height + week_events_height + WEEK_MARGINS
            space = space - week_height
            if space < 0:
                return max(1, week - 1)

        return self.config.number_of_weeks
