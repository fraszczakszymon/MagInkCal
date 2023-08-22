import logging
import subprocess
from datetime import datetime, timedelta
from pytz import timezone
from typing import Optional

from pydantic import BaseModel

from modules.config import Config

logger = logging.getLogger('schedule')


class BatteryStatus(BaseModel):
    level: Optional[float]
    is_charging: bool


class Scheduler:
    def __init__(self, config: Config):
        self.timezone = timezone(config.timezone)
        self.wakeup_hours = config.wakeup_hours

    def schedule_next_wakeup(self) -> None:
        command = ("echo", "rtc_alarm_disable")
        next_wakeup = self.get_next_wakeup_time()
        if next_wakeup:
            command = ("echo", f"rtc_alarm_set {next_wakeup.isoformat()} 127")

        try:
            ps = subprocess.Popen(command, stdout=subprocess.PIPE)
            subprocess.check_output(('nc', '-q', '0', '127.0.0.1', '8423'), stdin=ps.stdout)
            ps.wait()
            if next_wakeup:
                logger.info(f"Next wake up time set to {next_wakeup.isoformat()}")
            else:
                logger.info("No wake up time configured")
        except subprocess.CalledProcessError:
            logger.warning('Invalid alarm schedule command')

    def get_next_wakeup_time(self) -> Optional[datetime]:
        if not self.wakeup_hours:
            return None

        now = datetime.now().astimezone(self.timezone)
        next_wakeup = datetime.now().astimezone(self.timezone)
        for wakeup_hour in self.wakeup_hours:
            hour, minutes = wakeup_hour.split(":")
            next_wakeup = next_wakeup.replace(hour=int(hour), minute=int(minutes), second=0, microsecond=0)
            if now < next_wakeup:
                return next_wakeup

        hour, minutes = self.wakeup_hours[0].split(":")
        next_wakeup = next_wakeup + timedelta(days=1)

        return next_wakeup.replace(hour=int(hour), minute=int(minutes), second=0, microsecond=0)
