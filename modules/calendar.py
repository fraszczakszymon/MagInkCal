import functools
import logging
import requests

from datetime import datetime, timedelta
from dateutil import rrule
from ics import Calendar as IcsCalendar, Event as IcsEvent
from modules.config import Config
from pydantic import BaseModel
from pytz import timezone
from typing import Dict, List, Optional

SUPPORTED_RRULE_PROPERTIES = ("RRULE", "RDATE", "EXRULE", "EXDATE", "DTSTART")


logger = logging.getLogger('events')


class Event(BaseModel):
    all_day: bool
    end_date: datetime
    important = False
    start_date: datetime
    start_time: Optional[str] = None
    summary: str


class Day(BaseModel):
    date_label: str
    datetime: datetime
    events: List[Event] = []
    number: int


class MonthDay(BaseModel):
    datetime: datetime
    is_current_month: bool
    is_today: bool
    number: int


class Month(BaseModel):
    number: int
    year: int
    days: List[MonthDay] = []


def get_months_preview(number_of_months) -> List[Month]:
    for i in range(number_of_months):
        yield _get_month_preview(i)


def _get_month_preview(month_offset: int) -> Month:
    today = datetime.today()
    year = today.year
    month_with_offset = today.month + month_offset
    if month_with_offset > 12:
        year += int(month_with_offset / 12)
        month_with_offset = month_with_offset % 12
    first_day_of_month = today.replace(day=1, month=month_with_offset, year=year)
    day = first_day_of_month - timedelta(days=first_day_of_month.weekday())
    month = Month(number=first_day_of_month.month, year=first_day_of_month.year)
    while True:
        month.days.append(
            MonthDay(
                datetime=day,
                is_current_month=day.month == first_day_of_month.month,
                is_today=day == today and month_offset == 0,
                number=int(day.strftime("%d")),
            )
        )
        day = day + timedelta(days=1)
        if day.month != first_day_of_month.month and len(month.days) % 7 == 0:
            break
    return month


class Calendar:
    config: Config
    days: Dict[str, Day]

    def __init__(self, config: Config):
        self.config = config
        self.timezone = timezone(config.timezone)
        self.days = self._get_empty_days_range()

    @property
    @functools.lru_cache()
    def today(self) -> datetime:
        return datetime.today().astimezone(self.timezone).replace(hour=0, minute=0, second=0, microsecond=0)

    @property
    @functools.lru_cache()
    def start_date(self) -> datetime:
        return self.today - timedelta(days=self.today.weekday())

    @property
    @functools.lru_cache()
    def end_date(self) -> datetime:
        return self.start_date + timedelta(weeks=self.config.number_of_weeks)

    def load_events(self) -> None:
        logger.info(f"Fetching events from {len(self.config.calendars)} calendars")
        number_of_events = 0
        for calendar in self.config.calendars:
            ics_calendar = IcsCalendar(requests.get(calendar.url).text)
            for event in ics_calendar.events:
                event_description = event.serialize()
                if "RRULE" in event_description:
                    number_of_events += self._process_recurring_event(event, event_description, calendar.important)
                else:
                    number_of_events += self._process_single_event(event, calendar.important)
        self._sort_events()
        logger.info(f"Fetched {number_of_events} events to display")

    def _is_within_range(self, date: datetime) -> bool:
        return self.start_date <= date < self.end_date

    def _get_empty_days_range(self) -> Dict[str, Day]:
        days = {}
        date = self.start_date
        while date < self.end_date:
            day = Day(
                date_label=date.strftime("%Y-%m-%d"),
                datetime=date,
                number=int(date.strftime("%d")),
            )
            days[day.date_label] = day
            date = date + timedelta(days=1)
        return days

    def _process_single_event(self, ics_event: IcsEvent, important=False) -> int:
        start_date = ics_event.begin.datetime.astimezone(self.timezone)
        end_date = ics_event.end.datetime.astimezone(self.timezone)
        if self._is_within_range(start_date) or self._is_within_range(end_date):
            start_time = None
            if not ics_event.all_day:
                start_time = start_date.strftime("%H:%M")
            self._add_event(
                Event(
                    all_day=ics_event.all_day,
                    end_date=end_date,
                    important=important,
                    start_date=start_date,
                    start_time=start_time,
                    summary=ics_event.name,
                )
            )
            return 1
        return 0

    def _process_recurring_event(self, ics_event: IcsEvent, event_description: str, important=False) -> int:
        added_events = 0
        event_duration = ics_event.end.datetime - ics_event.begin.datetime
        rules = "\n".join([rule for rule in event_description.split("\n") if rule.startswith(SUPPORTED_RRULE_PROPERTIES)])
        start_time = None
        for next_event_start_datetime in rrule.rrulestr(rules):
            next_event_start_datetime = next_event_start_datetime.astimezone(self.timezone)
            if not start_time and not ics_event.all_day:
                start_time = next_event_start_datetime.strftime("%H:%M")
            if next_event_start_datetime > self.end_date:
                break
            next_event_end_datetime = next_event_start_datetime + event_duration
            if next_event_end_datetime < self.start_date:
                continue
            if self._is_within_range(next_event_start_datetime) or self._is_within_range(next_event_end_datetime):
                self._add_event(
                    Event(
                        all_day=ics_event.all_day,
                        end_date=next_event_end_datetime,
                        important=important,
                        start_date=next_event_start_datetime,
                        start_time=start_time,
                        summary=ics_event.name,
                    )
                )
                added_events += 1
        return added_events

    def _add_event(self, event: Event) -> None:
        date_keys = []
        date = event.start_date
        while date < event.end_date:
            date_keys.append(date.strftime("%Y-%m-%d"))
            date = date + timedelta(days=1)

        for key in date_keys:
            if key in self.days:
                self.days[key].events.append(event)

    def _sort_events(self) -> None:
        # Sort events in the day by hour and calendar order
        for key, events in self.days.items():
            day_events = [(i, event) for i, event in enumerate(self.days[key].events)]
            day_events.sort(key=lambda item: (item[1].start_time or "00:00", item[0]))
            self.days[key].events = [event for i, event in day_events]
