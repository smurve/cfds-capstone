from __future__ import annotations
from typing import Tuple


class Clock:

    def __init__(self, n_seconds=60, n_minutes=60, n_hours=24, n_days=256):
        """
        Creates a clock with special multiplicities
        :param n_seconds: number of settings per minute
        :param n_minutes: number of minutes per hour
        :param n_hours: number of hours per day
        :param n_days: number of days per year
        """
        self.seconds = 0
        self.n_seconds = n_seconds
        self.n_minutes = n_minutes
        self.n_hours = n_hours
        self.n_days = n_days

    def time(self) -> Tuple[int, int, int, int, int]:
        minutes, seconds = divmod(self.seconds, self.n_seconds)
        hours, minutes = divmod(minutes, self.n_minutes)
        days, hours = divmod(hours, self.n_hours)
        years, days = divmod(days, self.n_days)
        return years, days, hours, minutes, seconds

    def year(self):
        return self.time()[0]

    def day(self):
        return self.time()[1]

    def hour(self):
        return self.time()[2]

    def minute(self):
        return self.time()[3]

    def second(self):
        return self.time()[4]

    def tick(self, seconds: int = 1) -> Clock:
        self.seconds += seconds
        return self
