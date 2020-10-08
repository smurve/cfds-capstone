import abc
from typing import List

from markets.dynamic_market import Stock


class AbstractMarket(abc.ABC):

    @abc.abstractmethod
    def get_stocks(self) -> List[Stock]:
        pass

    @abc.abstractmethod
    def get_intrinsic_value(self, symbol: str, day: int) -> float:
        pass
