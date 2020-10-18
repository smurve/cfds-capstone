import logging
import datetime as dt
from collections import defaultdict
from copy import deepcopy
from typing import Dict, Any

import pandas as pd

from .Clock import Clock
from .abstract import AbstractStatistician, AbstractParticipant


class Statistician(AbstractStatistician):
    """
    Need to deal with out of order arrival
    Spec: For every minute:
        - record the first tx with the smallest second count as Open,
        - record the last tx with the highest second count as Close,
        - record the highest tx price as High
        - record the lowest tx price as Low
        - add the tx volume
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # data like {'symbol': {minute: {'Open':  (0, 123.13),
        #                                'Close': (59, 113.54),
        #                                'High', 123.98,
        #                                'Low', 110.22},
        #                       ...},
        #             ...}
        self.minute_data: Dict[str, Dict[int, Dict[str, Any]]] = defaultdict(
            lambda: defaultdict(lambda: {
                'Open': None,
                'High': None,
                'Low': None,
                'Close': None,
                'Volume': 0.}))

    def get_chart_data(self, symbol: str, date: dt.date) -> pd.DataFrame:
        data = deepcopy(self.minute_data[symbol])

        for minute in data:
            data[minute]['Open'] = data[minute]['Open'][1]
            data[minute]['Close'] = data[minute]['Close'][1]
            data[minute]['Date'] = date + dt.timedelta(minutes=minute)

        data = pd.DataFrame.from_dict(data, orient='index')

        data = data.set_index(pd.DatetimeIndex(data['Date']))
        data.drop('Date', axis='columns', inplace=True)

        self.logger.debug(f"{self.osid()}: get_chart_data not implemented yet.")

        return data

    def report_transaction(self, symbol: str, volume: float, price: float, clock: Clock):
        self.logger.debug(f"{self.osid()}: At {clock}: observing transaction for {symbol}")
        _, _, _, minute, second = clock.time()
        record = self.minute_data[symbol][minute]

        price = round(price, 2)

        volume = round(volume, 0)

        if not record['Open'] or (second < record['Open'][0]):
            record['Open'] = (second, price)

        if not record['Close'] or (second >= record['Close'][0]):
            record['Close'] = (second, price)

        if not record['High'] or price > record['High']:
            record['High'] = price

        if not record['Low'] or price < record['Low']:
            record['Low'] = price

        record['Volume'] += volume

    def register_participant(self, other_participant: AbstractParticipant, **kwargs):
        self.logger.error(f"{self.osid()}: Statisticians don't register other participants")
