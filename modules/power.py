import functools
import logging
import subprocess

from pydantic import BaseModel


logger = logging.getLogger('power')


class BatteryStatus(BaseModel):
    level: float
    is_charging: bool


class Power:
    @property
    @functools.lru_cache()
    def battery_status(self) -> BatteryStatus:
        status = BatteryStatus(
            level=self._get_battery_level(),
            is_charging=self._is_charging(),
        )
        logger.info(f"Battery level {status.level}%, is{'' if status.is_charging else ' not'} charging")

        return status

    def sync_time(self) -> None:
        # To sync PiSugar RTC with current time
        try:
            ps = subprocess.Popen(('echo', 'rtc_pi2rtc'), stdout=subprocess.PIPE)
            subprocess.check_output(('nc', '-q', '0', '127.0.0.1', '8423'), stdin=ps.stdout)
            ps.wait()
        except subprocess.CalledProcessError:
            logger.warning('Invalid time sync command')

    def _get_battery_level(self) -> float:
        try:
            ps = subprocess.Popen(('echo', 'get battery'), stdout=subprocess.PIPE)
            result = subprocess.check_output(('nc', '-q', '0', '127.0.0.1', '8423'), stdin=ps.stdout)
            ps.wait()
            value = result.decode('utf-8').rstrip().split()[-1]
            return float(value)
        except (ValueError, subprocess.CalledProcessError):
            logger.warning('Invalid battery output')

        return 0.0

    def _is_charging(self) -> bool:
        try:
            ps = subprocess.Popen(('echo', 'get battery_charging'), stdout=subprocess.PIPE)
            result = subprocess.check_output(('nc', '-q', '0', '127.0.0.1', '8423'), stdin=ps.stdout)
            ps.wait()
            value = result.decode('utf-8').rstrip().split()[-1]
            return value == "true"
        except (ValueError, subprocess.CalledProcessError):
            logger.warning('Invalid battery output')

        return False
