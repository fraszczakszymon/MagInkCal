from functools import cached_property

import requests

from datetime import datetime, timedelta
from dateutil import rrule
from ics import Calendar as IcsCalendar, Event as IcsEvent
from modules.config import Config
from pydantic import BaseModel
from pytz import timezone
from typing import Dict, List


SUPPORTED_RRULE_PROPERTIES = ("RRULE", "RDATE", "EXRULE", "EXDATE", "DTSTART")


class Event(BaseModel):
    all_day: bool
    end_date: datetime
    important = False
    start_date: datetime
    summary: str


class Day(BaseModel):
    date_label: str
    datetime: datetime
    events: List[Event] = []
    number: int


class Calendar:
    config: Config
    days: Dict[str, Day]

    def __init__(self, config: Config):
        self.config = config
        self.timezone = timezone(config.timezone)
        self.days = self._get_empty_days_range()

    @cached_property
    def today(self) -> datetime:
        return datetime.today().astimezone(self.timezone).replace(hour=0, minute=0, second=0, microsecond=0)

    @cached_property
    def start_date(self) -> datetime:
        return self.today - timedelta(days=self.today.weekday())

    @cached_property
    def end_date(self) -> datetime:
        return self.start_date + timedelta(weeks=self.config.number_of_weeks)

    def load_events(self) -> None:
        for calendar in self.config.calendars:
            ics_calendar = IcsCalendar(requests.get(calendar.url).text)
            for event in ics_calendar.events:
                event_description = event.serialize()
                if "RRULE" in event_description:
                    self._process_recurring_event(event, event_description, calendar.important)
                elif self._starts_within_range(event.begin.datetime) or self._end_within_range(event.end.datetime):
                    self._process_single_event(event, calendar.important)
        self._sort_events()

    def _starts_within_range(self, start_datetime: datetime) -> bool:
        return self.start_date <= start_datetime < self.end_date

    def _end_within_range(self, end_datetime: datetime) -> bool:
        return self.start_date <= end_datetime < self.end_date

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

    def _process_single_event(self, ics_event: IcsEvent, important=False) -> None:
        self._add_event(
            Event(
                all_day=ics_event.all_day,
                end_date=ics_event.end.datetime.astimezone(self.timezone),
                important=important,
                start_date=ics_event.begin.datetime.astimezone(self.timezone),
                summary=ics_event.name,
            )
        )

    def _process_recurring_event(self, ics_event: IcsEvent, event_description: str, important=False) -> None:
        event_duration = ics_event.end.datetime - ics_event.begin.datetime
        rules = "\n".join([rule for rule in event_description.split("\n") if rule.startswith(SUPPORTED_RRULE_PROPERTIES)])
        for next_event_start_datetime in rrule.rrulestr(rules):
            next_event_start_datetime = next_event_start_datetime.astimezone(self.timezone)
            if next_event_start_datetime > self.end_date:
                break
            next_event_end_datetime = next_event_start_datetime + event_duration
            if next_event_end_datetime < self.start_date:
                continue
            if self._starts_within_range(next_event_start_datetime) or self._end_within_range(next_event_end_datetime):
                self._add_event(
                    Event(
                        all_day=ics_event.all_day,
                        end_date=next_event_end_datetime,
                        important=important,
                        start_date=next_event_start_datetime,
                        summary=ics_event.name,
                    )
                )

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
        for key, events in self.days.items():
            self.days[key].events.sort(key=lambda e: e.start_date)
