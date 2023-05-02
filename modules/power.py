import functools
import logging
import subprocess

from pydantic import BaseModel


class BatteryStatus(BaseModel):
    level: float
    is_charging: bool


class Power:
    def __init__(self):
        self.logger = logging.getLogger('maginkcal')

    @property
    @functools.lru_cache()
    def battery_status(self) -> BatteryStatus:
        return BatteryStatus(
            level=self._get_battery_level(),
            is_charging=self._is_charging(),
        )

    def sync_time(self) -> None:
        # To sync PiSugar RTC with current time
        try:
            ps = subprocess.Popen(('echo', 'rtc_rtc2pi'), stdout=subprocess.PIPE)
            subprocess.check_output(('nc', '-q', '0', '127.0.0.1', '8423'), stdin=ps.stdout)
            ps.wait()
        except subprocess.CalledProcessError:
            self.logger.info('Invalid time sync command')

    def _get_battery_level(self) -> float:
        try:
            ps = subprocess.Popen(('echo', 'get battery'), stdout=subprocess.PIPE)
            result = subprocess.check_output(('nc', '-q', '0', '127.0.0.1', '8423'), stdin=ps.stdout)
            ps.wait()
            value = result.decode('utf-8').rstrip().split()[-1]
            return float(value)
        except (ValueError, subprocess.CalledProcessError):
            self.logger.info('Invalid battery output')

        return 0.0

    def _is_charging(self) -> bool:
        try:
            ps = subprocess.Popen(('echo', 'get battery_charging'), stdout=subprocess.PIPE)
            result = subprocess.check_output(('nc', '-q', '0', '127.0.0.1', '8423'), stdin=ps.stdout)
            ps.wait()
            value = result.decode('utf-8').rstrip().split()[-1]
            return value == "true"
        except (ValueError, subprocess.CalledProcessError):
            self.logger.info('Invalid battery output')

        return False
