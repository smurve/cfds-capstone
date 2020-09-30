import abc
from typing import List

from markets.realistic import AbstractMarketMaker
from markets.realistic import Clock


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
