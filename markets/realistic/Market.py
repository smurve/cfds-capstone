import abc
from typing import List

from markets.dynamic_market import Stock


class Market(abc.ABC):

    @abc.abstractmethod
    def get_stocks(self) -> List[Stock]:
        pass
