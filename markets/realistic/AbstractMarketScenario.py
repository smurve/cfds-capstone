import abc
from typing import List

from .AbstractInvestor import AbstractInvestor
from .AbstractMarketMaker import AbstractMarketMaker
from .Clock import Clock


class AbstractMarketScenario(abc.ABC):

    def __init__(self, clock: Clock):
        self.clock = clock

    @abc.abstractmethod
    def register_investors(self, *investors: AbstractInvestor) -> List[AbstractInvestor]:
        """
        register the investors and return a list of references to those investors
        :param investors: A list of plain old python investors (POPIs)
        :return: a list of references, may be to remote instances of those
        """
        pass

    @abc.abstractmethod
    def register_market_makers(self, *market_makers: AbstractMarketMaker) -> List[AbstractMarketMaker]:
        """
        register the market makers and return a list of references to those investors
        :param market_makers: A list of plain old python MarketMakers
        :return: a list of references, may be to remote instances of those
        """
        pass

    @abc.abstractmethod
    def tick(self, seconds: int):
        pass

    @abc.abstractmethod
    def identify_investors(self):
        pass
