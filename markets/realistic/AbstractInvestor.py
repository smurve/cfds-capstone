import abc
from typing import List

from .AbstractMarketMaker import AbstractMarketMaker
from .Clock import Clock
from .Order import OrderType


class AbstractInvestor(abc.ABC):

    @abc.abstractmethod
    def tick(self, clock: Clock):
        pass

    @abc.abstractmethod
    def identify(self) -> str:
        pass

    @abc.abstractmethod
    def get_stock_symbols(self) -> List[str]:
        """
        :return: a list of the stocks traded by this investor
        """
        pass

    @abc.abstractmethod
    def register_with(self, market_maker: AbstractMarketMaker, symbol: str):
        pass

    @abc.abstractmethod
    def report_tx(self, order_type: OrderType, symbol: str, volume: float, price: float, amount: float):
        pass
